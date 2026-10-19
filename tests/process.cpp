#include "freeflight/process.hpp"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#ifdef _WIN32
#define NOMINMAX
#include <shellapi.h>
#include <windows.h>
#else
#include <cerrno>
#include <sys/wait.h>
#include <unistd.h>
#endif

using freeflight::Process;
using nlohmann::json;
namespace fs = std::filesystem;
using namespace std::chrono_literals;

namespace {
void require(bool condition, const std::string &message) {
    if (!condition)
        throw std::runtime_error(message);
}
template <typename Fn> void fails(Fn fn, const std::string &expected) {
    try {
        fn();
    } catch (const std::runtime_error &error) {
        require(std::string(error.what()).find(expected) != std::string::npos,
                "wrong error: " + std::string(error.what()) + "; expected " + expected);
        return;
    }
    throw std::runtime_error("expected failure: " + expected);
}
int worker(int argc, char **argv) {
    const std::string mode = argv[2];
    if (mode == "no-read") {
        std::this_thread::sleep_for(10s);
        return 0;
    }
    std::string line;
    while (std::getline(std::cin, line)) {
        const auto message = json::parse(line);
        if (mode == "crash") {
            std::ofstream marker(argv[3], std::ios::app);
            marker << "one invocation\n";
            marker.close();
            return 7;
        }
        if (mode == "hang") {
            std::this_thread::sleep_for(10s);
            return 0;
        }
        if (mode == "malformed") {
            std::cout << "not JSON\n" << std::flush;
            continue;
        }
        if (mode == "mismatch") {
            std::cout << "{\"id\":\"wrong\"}\n" << std::flush;
            continue;
        }
        if (mode == "oversize") {
            std::cout << std::string(8 * 1024 * 1024 + 1, 'x') << std::flush;
            continue;
        }
        json response = {
            {"id", message["id"]}, {"echo", message}, {"cwd", fs::current_path().string()}};
        response["args"] = json::array();
        response["secretInherited"] = std::getenv("FREEFLIGHT_TEST_SECRET") != nullptr;
        response["injectionInherited"] = std::getenv("NODE_OPTIONS") != nullptr;
        for (int i = 3; i < argc; ++i)
            response["args"].push_back(argv[i]);
#ifndef _WIN32
        response["pid"] = getpid();
        if (mode == "close-input")
            close(STDIN_FILENO);
#endif
        const auto encoded = response.dump() + '\n';
        if (mode == "partial") {
            for (char c : encoded) {
                std::cout.put(c);
                std::cout.flush();
            }
        } else {
            std::cout << encoded << std::flush;
        }
#ifndef _WIN32
        if (mode == "close-input") {
            std::this_thread::sleep_for(10s);
            return 0;
        }
#endif
    }
    return 0;
}
} // namespace

int run_tests(int argc, char **argv) {
    if (argc >= 3 && std::string(argv[1]) == "--worker")
        return worker(argc, argv);
    try {
        const auto executable = fs::canonical(argv[0]).string();
        const auto cwd = fs::current_path();
#ifdef _WIN32
        _putenv_s("FREEFLIGHT_TEST_SECRET", "test-only-value");
        _putenv_s("NODE_OPTIONS", "test-only-value");
#else
        setenv("FREEFLIGHT_TEST_SECRET", "test-only-value", 1);
        setenv("NODE_OPTIONS", "test-only-value", 1);
#endif
        {
            Process process({executable, "--worker", "echo"});
            const auto response = process.request({{"id", "environment"}});
            require(!response["secretInherited"].get<bool>(), "worker inherited unrelated secret");
            require(!response["injectionInherited"].get<bool>(),
                    "worker inherited runtime injection");
        }
        const json message = {{"id", 42}, {"method", "test"}, {"value", "Unicode: λ and 日本語"}};
        fails([] { Process process({"relative-worker"}); }, "absolute path");
        fails([] { Process process({}); }, "absolute path");
        fails([&] { Process process({executable, std::string("a\0b", 3)}); },
              "invalid worker argument");
        fails(
            [&] {
                Process process(
                    {(fs::path(executable).parent_path() / "missing-worker-executable").string()});
            },
            "launch worker");
        {
            const std::vector<std::string> arguments = {
                "", "with spaces", "quote\"embedded", "trailing\\", "$HOME;not-a-shell", "日本語"};
            std::vector<std::string> command = {executable, "--worker", "echo"};
            command.insert(command.end(), arguments.begin(), arguments.end());
            Process process(command);
            for (int i = 0; i < 10; ++i) {
                auto request = message;
                request["id"] = i % 2 ? json("string-id") : json(i);
                const auto response = process.request(request);
                require(response["echo"] == request, "JSON round-trip differs");
                require(response["args"] == arguments, "process argument corruption");
                require(fs::equivalent(response["cwd"].get<std::string>(),
                                       fs::path(executable).parent_path()),
                        "unsafe child cwd");
            }
            require(fs::current_path() == cwd, "parent cwd changed");
            fails([&] { process.request(json::array()); }, "requires an id");
            fails([&] { process.request({{"method", "missing-id"}}); }, "requires an id");
            // Local validation failures do not poison the live connection.
            require(process.request(message)["id"] == 42, "validation killed worker");
            process.stop();
            process.stop();
            fails([&] { process.request(message); }, "stopped");
        }
        {
            Process process({executable, "--worker", "partial"});
            require(process.request(message)["echo"] == message, "fragmented response corrupted");
        }
        for (const auto &[mode, error] :
             std::vector<std::pair<std::string, std::string>>{{"malformed", "invalid worker JSON"},
                                                              {"mismatch", "id mismatch"},
                                                              {"oversize", "exceeds limit"}}) {
            Process process({executable, "--worker", mode});
            fails([&] { process.request(message); }, error);
            fails([&] { process.request(message); }, "stopped");
        }
        {
            Process process({executable, "--worker", "echo"});
            fails(
                [&] { process.request({{"id", 1}, {"text", std::string(8 * 1024 * 1024, 'x')}}); },
                "request exceeds limit");
            require(process.request(message)["id"] == 42, "large input validation killed worker");
        }
        const auto marker =
            fs::temp_directory_path() /
            ("freeflight-process-" +
             std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        {
            Process process({executable, "--worker", "crash", marker.string()});
            fails([&] { process.request(message); }, "pipe closed");
            fails([&] { process.request(message); }, "stopped");
            std::ifstream file(marker);
            std::string first, second;
            std::getline(file, first);
            std::getline(file, second);
            require(first == "one invocation" && second.empty(), "crashed request was retried");
        }
        fs::remove(marker);
        for (const auto &mode : {"hang", "no-read"}) {
            Process process({executable, "--worker", mode});
            std::stop_source cancel;
            const auto start = std::chrono::steady_clock::now();
            std::jthread trigger([&] {
                std::this_thread::sleep_for(100ms);
                cancel.request_stop();
            });
            auto request = message;
            if (std::string(mode) == "no-read")
                request["data"] = std::string(1024 * 1024, 'x');
            fails([&] { process.request(request, cancel.get_token()); }, "cancelled");
            require(std::chrono::steady_clock::now() - start < 3s,
                    "cancellation failed to interrupt pipe IO");
            fails([&] { process.request(message); }, "stopped");
        }
        {
            Process process({executable, "--worker", "echo"});
            std::stop_source cancel;
            cancel.request_stop();
            fails([&] { process.request(message, cancel.get_token()); }, "cancelled");
        }
#ifndef _WIN32
        {
            Process process({executable, "--worker", "close-input"});
            const auto pid = process.request(message)["pid"].get<pid_t>();
            fails([&] { process.request(message); }, "pipe");
            errno = 0;
            require(waitpid(pid, nullptr, WNOHANG) == -1 && errno == ECHILD,
                    "failed worker was not reaped");
        }
        {
            pid_t pid;
            {
                Process process({executable, "--worker", "echo"});
                pid = process.request(message)["pid"].get<pid_t>();
            }
            errno = 0;
            require(waitpid(pid, nullptr, WNOHANG) == -1 && errno == ECHILD,
                    "destructor did not reap worker");
        }
#endif
        std::cout
            << "Process IPC, launch, validation, cancellation, crash, and cleanup tests passed\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "Process test failed: " << error.what() << '\n';
        return 1;
    }
}

#ifdef _WIN32
int main() {
    // The CRT's narrow argv uses the active codepage, while Process uses UTF-8.
    int count = 0;
    wchar_t **wide_args = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!wide_args)
        return 1;
    std::vector<std::string> strings;
    for (int i = 0; i < count; ++i) {
        const int size =
            WideCharToMultiByte(CP_UTF8, 0, wide_args[i], -1, nullptr, 0, nullptr, nullptr);
        std::string value(static_cast<std::size_t>(size), '\0');
        WideCharToMultiByte(CP_UTF8, 0, wide_args[i], -1, value.data(), size, nullptr, nullptr);
        value.pop_back();
        strings.push_back(std::move(value));
    }
    LocalFree(wide_args);
    std::vector<char *> args;
    for (auto &value : strings)
        args.push_back(value.data());
    return run_tests(count, args.data());
}
#else
int main(int argc, char **argv) {
    return run_tests(argc, argv);
}
#endif
