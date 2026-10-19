#ifndef _WIN32
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#endif
#include "freeflight/process.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <stdexcept>
#include <thread>
#include <utility>

#ifdef _WIN32
#define NOMINMAX
#include <atomic>
#include <windows.h>
#else
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace freeflight {
namespace {
constexpr std::size_t max_line = 8 * 1024 * 1024;
std::vector<std::string> worker_environment() {
    std::vector<std::string> values;
    // Language workers do not need unrelated cloud/provider credentials or
    // runtime injection controls such as NODE_OPTIONS and DOTNET_STARTUP_HOOKS.
    for (const auto *name : {"PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG",
                             "LC_ALL", "DOTNET_ROOT"}) {
        if (const char *value = std::getenv(name))
            values.push_back(std::string(name) + "=" + value);
    }
    values.emplace_back("DOTNET_CLI_TELEMETRY_OPTOUT=1");
    values.emplace_back("DOTNET_EnableDiagnostics=0");
    return values;
}
using Clock = std::chrono::steady_clock;
void check(std::stop_token token, Clock::time_point deadline) {
    if (token.stop_requested())
        throw std::runtime_error("worker request cancelled");
    if (Clock::now() >= deadline)
        throw std::runtime_error("worker request timed out");
}
#ifdef _WIN32
std::wstring wide(const std::string &value) {
    const int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                                      static_cast<int>(value.size()), nullptr, 0);
    if (!n && !value.empty())
        throw std::runtime_error("invalid UTF-8 process argument");
    std::wstring result(n, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                        result.data(), n);
    return result;
}
std::wstring quote(const std::wstring &value) {
    std::wstring result = L"\"";
    std::size_t slashes = 0;
    for (wchar_t c : value) {
        if (c == L'\\') {
            ++slashes;
            continue;
        }
        result.append(c == L'"' ? slashes * 2 + 1 : slashes, L'\\');
        slashes = 0;
        result += c;
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}
void close_handle(HANDLE &h) noexcept {
    if (h && h != INVALID_HANDLE_VALUE)
        CloseHandle(h);
    h = nullptr;
}
#else
void close_fd(int &fd) noexcept {
    if (fd >= 0)
        close(fd);
    fd = -1;
}
// Block SIGPIPE only on the calling thread and consume only a signal generated
// here. Do not change the application's process-wide signal disposition.
class PipeSignalGuard {
    sigset_t set_{}, old_{};
    bool pending_ = false;

  public:
    PipeSignalGuard() {
        sigemptyset(&set_);
        sigaddset(&set_, SIGPIPE);
        if (pthread_sigmask(SIG_BLOCK, &set_, &old_) != 0)
            throw std::runtime_error("cannot protect worker pipe write");
        sigset_t pending{};
        sigpending(&pending);
        pending_ = sigismember(&pending, SIGPIPE) == 1;
    }
    ~PipeSignalGuard() {
        sigset_t pending{};
        sigpending(&pending);
        if (!pending_ && sigismember(&pending, SIGPIPE) == 1) {
            int signal = 0;
            sigwait(&set_, &signal);
        }
        pthread_sigmask(SIG_SETMASK, &old_, nullptr);
    }
};
void ready(int fd, short events, std::stop_token token, Clock::time_point deadline) {
    for (;;) {
        check(token, deadline);
        pollfd item{fd, events, 0};
        const int result = poll(&item, 1, 25);
        if (result < 0 && errno != EINTR)
            throw std::runtime_error("worker pipe poll failed");
        if (result > 0) {
            if (item.revents & events)
                return;
            if (item.revents & (POLLERR | POLLHUP | POLLNVAL))
                throw std::runtime_error("worker pipe closed");
        }
    }
}
#endif
} // namespace

struct Process::Impl {
#ifdef _WIN32
    HANDLE process = nullptr, job = nullptr, input = nullptr, output = nullptr;
#else
    pid_t pid = -1;
    int input = -1, output = -1;
#endif
    std::string buffered;
    ~Impl() {
        stop();
    }
    void stop() noexcept {
#ifdef _WIN32
        if (process) {
            TerminateProcess(process, 1);
            WaitForSingleObject(process, 5000);
        }
        close_handle(job);
        close_handle(process);
        close_handle(input);
        close_handle(output);
#else
        close_fd(input);
        close_fd(output);
        if (pid > 0) {
            kill(-pid, SIGKILL); // Each worker owns a process group.
            kill(pid, SIGKILL);
            while (waitpid(pid, nullptr, 0) < 0 && errno == EINTR) {
            }
            pid = -1;
        }
#endif
        buffered.clear();
    }
};

Process::Process(std::vector<std::string> argv) : impl_(std::make_unique<Impl>()) {
    if (argv.empty() || !std::filesystem::path(argv.front()).is_absolute())
        throw std::runtime_error("worker executable must be an absolute path");
    for (const auto &arg : argv)
        if (arg.find('\0') != std::string::npos || arg.size() > max_line)
            throw std::runtime_error("invalid worker argument");
#ifdef _WIN32
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE child_input = nullptr, child_output = nullptr, child_error = nullptr;
    LPPROC_THREAD_ATTRIBUTE_LIST attributes = nullptr;
    auto cleanup = [&] {
        close_handle(child_input);
        close_handle(child_output);
        close_handle(child_error);
        if (attributes) {
            DeleteProcThreadAttributeList(attributes);
            HeapFree(GetProcessHeap(), 0, attributes);
            attributes = nullptr;
        }
    };
    if (!CreatePipe(&child_input, &impl_->input, &security, 0) ||
        !CreatePipe(&impl_->output, &child_output, &security, 0)) {
        cleanup();
        throw std::runtime_error("cannot create worker pipes");
    }
    if (!SetHandleInformation(impl_->input, HANDLE_FLAG_INHERIT, 0) ||
        !SetHandleInformation(impl_->output, HANDLE_FLAG_INHERIT, 0)) {
        cleanup();
        throw std::runtime_error("cannot secure worker pipes");
    }
    try {
        std::wstring command;
        for (const auto &arg : argv) {
            if (!command.empty())
                command += L' ';
            command += quote(wide(arg));
        }
        const auto executable = wide(argv.front());
        const auto directory = std::filesystem::path(executable).parent_path().wstring();
        if (!DuplicateHandle(GetCurrentProcess(), GetStdHandle(STD_ERROR_HANDLE),
                             GetCurrentProcess(), &child_error, 0, TRUE, DUPLICATE_SAME_ACCESS))
            child_error = CreateFileW(L"NUL", GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
                                      &security, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (child_error == INVALID_HANDLE_VALUE)
            throw std::runtime_error("cannot configure worker stderr");
        SIZE_T attribute_size = 0;
        InitializeProcThreadAttributeList(nullptr, 1, 0, &attribute_size);
        attributes = static_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(
            HeapAlloc(GetProcessHeap(), 0, attribute_size));
        if (!attributes)
            throw std::runtime_error("cannot allocate worker attributes");
        if (!InitializeProcThreadAttributeList(attributes, 1, 0, &attribute_size)) {
            HeapFree(GetProcessHeap(), 0, attributes);
            attributes = nullptr;
            throw std::runtime_error("cannot initialize worker attributes");
        }
        HANDLE inherited[] = {child_input, child_output, child_error};
        if (!UpdateProcThreadAttribute(attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, inherited,
                                       sizeof(inherited), nullptr, nullptr))
            throw std::runtime_error("cannot isolate worker handles");
        STARTUPINFOEXW startup{};
        startup.StartupInfo.cb = sizeof(startup);
        startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
        startup.StartupInfo.hStdInput = child_input;
        startup.StartupInfo.hStdOutput = child_output;
        startup.StartupInfo.hStdError = child_error;
        startup.lpAttributeList = attributes;
        impl_->job = CreateJobObjectW(nullptr, nullptr);
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if (!impl_->job || !SetInformationJobObject(impl_->job, JobObjectExtendedLimitInformation,
                                                    &limits, sizeof(limits)))
            throw std::runtime_error("cannot create worker job");
        PROCESS_INFORMATION info{};
        std::vector<std::wstring> entries;
        for (const auto &item : worker_environment())
            entries.push_back(wide(item));
        // CreateProcess requires a case-insensitive ordinally sorted environment block.
        std::sort(entries.begin(), entries.end(), [](const auto &left, const auto &right) {
            return CompareStringOrdinal(left.c_str(), -1, right.c_str(), -1, TRUE) ==
                   CSTR_LESS_THAN;
        });
        std::wstring environment;
        for (const auto &item : entries) {
            environment += item;
            environment.push_back(L'\0');
        }
        environment.push_back(L'\0');
        if (!CreateProcessW(executable.c_str(), command.data(), nullptr, nullptr, TRUE,
                            CREATE_NO_WINDOW | CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT |
                                CREATE_UNICODE_ENVIRONMENT,
                            environment.data(), directory.c_str(), &startup.StartupInfo, &info))
            throw std::runtime_error("cannot launch worker");
        impl_->process = info.hProcess;
        if (!AssignProcessToJobObject(impl_->job, info.hProcess) ||
            ResumeThread(info.hThread) == DWORD(-1)) {
            CloseHandle(info.hThread);
            throw std::runtime_error("cannot supervise worker job");
        }
        CloseHandle(info.hThread);
        cleanup();
    } catch (...) {
        cleanup();
        throw;
    }
#else
    // Finish allocation-bearing preparation before acquiring raw launch resources.
    const auto directory = std::filesystem::path(argv.front()).parent_path().string();
    std::vector<char *> args;
    for (auto &arg : argv)
        args.push_back(arg.data());
    args.push_back(nullptr);
    auto environment = worker_environment();
    std::vector<char *> env;
    for (auto &value : environment)
        env.push_back(value.data());
    env.push_back(nullptr);
    std::array<int, 2> input{-1, -1}, output{-1, -1};
    auto cleanup = [&] {
        for (auto &fd : input)
            close_fd(fd);
        for (auto &fd : output)
            close_fd(fd);
    };
    if (pipe(input.data()) != 0 || pipe(output.data()) != 0) {
        cleanup();
        throw std::runtime_error("cannot create worker pipes");
    }
    for (int *fd : {&input[0], &input[1], &output[0], &output[1]}) {
        if (*fd <= STDERR_FILENO) {
            const int replacement = fcntl(*fd, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
            if (replacement < 0) {
                cleanup();
                throw std::runtime_error("cannot isolate worker pipe");
            }
            close(*fd);
            *fd = replacement;
        }
        if (fcntl(*fd, F_SETFD, FD_CLOEXEC) == -1) {
            cleanup();
            throw std::runtime_error("cannot secure worker pipes");
        }
    }
    posix_spawn_file_actions_t actions;
    posix_spawnattr_t attrs;
    if (posix_spawn_file_actions_init(&actions) != 0) {
        cleanup();
        throw std::runtime_error("cannot initialize worker launch");
    }
    if (posix_spawnattr_init(&attrs) != 0) {
        posix_spawn_file_actions_destroy(&actions);
        cleanup();
        throw std::runtime_error("cannot initialize worker attributes");
    }
    int error = posix_spawn_file_actions_adddup2(&actions, input[0], STDIN_FILENO);
    error |= posix_spawn_file_actions_adddup2(&actions, output[1], STDOUT_FILENO);
    for (int fd : {input[0], input[1], output[0], output[1]})
        if (fd != STDIN_FILENO && fd != STDOUT_FILENO)
            error |= posix_spawn_file_actions_addclose(&actions, fd);
#if defined(__APPLE__) && __MAC_OS_X_VERSION_MIN_REQUIRED >= 260000
    error |= posix_spawn_file_actions_addchdir(&actions, directory.c_str());
#else
    error |= posix_spawn_file_actions_addchdir_np(&actions, directory.c_str());
#endif
#ifdef __APPLE__
    error |= posix_spawnattr_setflags(&attrs, POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_CLOEXEC_DEFAULT);
#else
    error |= posix_spawn_file_actions_addclosefrom_np(&actions, STDERR_FILENO + 1);
    error |= posix_spawnattr_setflags(&attrs, POSIX_SPAWN_SETPGROUP);
#endif
    error |= posix_spawnattr_setpgroup(&attrs, 0);
    if (!error)
        error =
            posix_spawn(&impl_->pid, argv[0].c_str(), &actions, &attrs, args.data(), env.data());
    posix_spawn_file_actions_destroy(&actions);
    posix_spawnattr_destroy(&attrs);
    if (error) {
        impl_->pid = -1;
        cleanup();
        throw std::runtime_error("cannot launch worker");
    }
    impl_->input = std::exchange(input[1], -1);
    impl_->output = std::exchange(output[0], -1);
    cleanup();
    for (int fd : {impl_->input, impl_->output}) {
        const int flags = fcntl(fd, F_GETFL);
        if (flags == -1 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
            throw std::runtime_error("cannot configure worker pipe");
    }
#endif
}

Process::~Process() = default;
void Process::stop() noexcept {
    impl_->stop();
}

nlohmann::json Process::request(const nlohmann::json &message, std::stop_token token) {
    if (!message.is_object() || !message.contains("id"))
        throw std::runtime_error("worker request requires an id");
    const auto deadline = Clock::now() + std::chrono::seconds(30);
    std::string line;
    try {
        line = message.dump();
    } catch (const nlohmann::json::exception &) {
        throw std::runtime_error("cannot serialize worker request");
    }
    if (line.size() > max_line)
        throw std::runtime_error("worker request exceeds limit");
    line += '\n';
    try {
        check(token, deadline);
#ifdef _WIN32
        if (!impl_->process)
            throw std::runtime_error("worker is stopped");
        std::atomic<bool> finished{false}, success{true};
        std::thread writer([&] {
            std::size_t offset = 0;
            while (offset < line.size()) {
                DWORD written = 0;
                if (!WriteFile(impl_->input, line.data() + offset,
                               static_cast<DWORD>(line.size() - offset), &written, nullptr) ||
                    !written) {
                    success = false;
                    break;
                }
                offset += written;
            }
            finished = true;
        });
        try {
            while (!finished) {
                check(token, deadline);
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        } catch (...) {
            close_handle(impl_->job);
            TerminateProcess(impl_->process, 1);
            CancelSynchronousIo(writer.native_handle());
            writer.join();
            throw;
        }
        writer.join();
        if (!success)
            throw std::runtime_error("worker pipe write failed");
#else
        if (impl_->pid <= 0)
            throw std::runtime_error("worker is stopped");
        PipeSignalGuard guard;
        std::size_t offset = 0;
        while (offset < line.size()) {
            ready(impl_->input, POLLOUT, token, deadline);
            const auto n = write(impl_->input, line.data() + offset, line.size() - offset);
            if (n > 0)
                offset += static_cast<std::size_t>(n);
            else if (n < 0 && errno != EAGAIN && errno != EINTR)
                throw std::runtime_error("worker pipe write failed");
        }
#endif
        for (;;) {
            check(token, deadline);
            const auto newline = impl_->buffered.find('\n');
            if (newline != std::string::npos) {
                auto result = nlohmann::json::parse(impl_->buffered.substr(0, newline));
                impl_->buffered.erase(0, newline + 1);
                if (!result.is_object() || !result.contains("id") || result["id"] != message["id"])
                    throw std::runtime_error("worker response id mismatch");
                return result;
            }
            std::array<char, 8192> buffer{};
            std::size_t count = 0;
#ifdef _WIN32
            DWORD available = 0, received = 0;
            if (!PeekNamedPipe(impl_->output, nullptr, 0, nullptr, &available, nullptr))
                throw std::runtime_error("worker pipe closed");
            if (!available) {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                continue;
            }
            if (!ReadFile(impl_->output, buffer.data(), static_cast<DWORD>(buffer.size()),
                          &received, nullptr) ||
                !received)
                throw std::runtime_error("worker pipe read failed");
            count = received;
#else
            ready(impl_->output, POLLIN, token, deadline);
            const auto n = read(impl_->output, buffer.data(), buffer.size());
            if (n < 0 && (errno == EAGAIN || errno == EINTR))
                continue;
            if (n <= 0)
                throw std::runtime_error("worker pipe closed");
            count = static_cast<std::size_t>(n);
#endif
            impl_->buffered.append(buffer.data(), count);
            const auto end = impl_->buffered.find('\n');
            if ((end == std::string::npos && impl_->buffered.size() > max_line) ||
                (end != std::string::npos && end > max_line))
                throw std::runtime_error("worker response exceeds limit");
        }
    } catch (const nlohmann::json::exception &) {
        stop();
        throw std::runtime_error("invalid worker JSON response");
    } catch (...) {
        stop();
        throw;
    }
}
} // namespace freeflight
