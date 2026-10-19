#include "freeflight/path.hpp"
#include "freeflight/server.hpp"
#include <condition_variable>
#include <deque>
#include <fstream>
#include <iostream>
#include <mutex>
#include <set>
#include <thread>
#ifdef _WIN32
#include <windows.h>
#elif defined(__APPLE__)
#include <mach-o/dyld.h>
#endif

using freeflight::Json;
namespace {
constexpr auto version = "2026-07-28";
constexpr auto versionKey = "io.modelcontextprotocol/protocolVersion";
constexpr auto capabilitiesKey = "io.modelcontextprotocol/clientCapabilities";
const Json identity = {{"name", "freeflight"}, {"version", "0.1.0"}};
// Limit container nesting before constructing deeply recursive JSON values.
// Throwing aborts parsing; returning false would still consume the nested input.
bool boundedJsonDepth(int depth, Json::parse_event_t event, Json &) {
    if (depth >= 128 &&
        (event == Json::parse_event_t::object_start || event == Json::parse_event_t::array_start))
        throw std::runtime_error("JSON nesting exceeds 128 containers");
    return true;
}
std::filesystem::path executablePath() {
#ifdef _WIN32
    std::wstring buffer(32768, L'\0');
    const auto length =
        GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!length || length == buffer.size())
        throw std::runtime_error("Cannot locate executable");
    buffer.resize(length);
    return std::filesystem::canonical(buffer);
#elif defined(__APPLE__)
    uint32_t size = 0;
    _NSGetExecutablePath(nullptr, &size);
    std::string buffer(size, '\0');
    if (_NSGetExecutablePath(buffer.data(), &size))
        throw std::runtime_error("Cannot locate executable");
    return std::filesystem::canonical(buffer.c_str());
#else
    return std::filesystem::canonical("/proc/self/exe");
#endif
}
struct Job {
    Json id;
    Json params;
    bool modern;
    std::stop_source stop;
    Json clientRoots = nullptr;
};
} // namespace

int runMain(const std::vector<std::string> &argv) {
    const auto argc = argv.size();
    try {
        if (argc == 2 && std::string(argv[1]) == "--version") {
            std::cout << "FreeFlight 0.1.0\n";
            return 0;
        }
        if (argc != 1 && (argc != 3 || (std::string(argv[1]) != "--config" &&
                                        std::string(argv[1]) != "--workspace"))) {
            std::cerr << "Usage: freeflight [--workspace /absolute/root | --config "
                         "/absolute/freeflight.json]\n";
            return 2;
        }
        if (argc > 1 && !freeflight::pathFromUtf8(argv[2]).is_absolute())
            throw std::runtime_error("Configuration or workspace path must be absolute");
        Json config;
        if (argc > 1 && std::string(argv[1]) == "--config") {
            std::ifstream input(freeflight::pathFromUtf8(argv[2]));
            config = Json::parse(input, boundedJsonDepth);
        } else {
            const auto library =
                executablePath().parent_path().parent_path() / "lib" / "freeflight";
#ifdef _WIN32
            const auto node = library / "node" / "node.exe";
            const auto roslyn = library / "roslyn" / "FreeFlight.Roslyn.exe";
#else
            const auto node = library / "node" / "bin" / "node";
            const auto roslyn = library / "roslyn" / "FreeFlight.Roslyn";
#endif
            const auto worker = library / "typescript" / "worker.mjs";
            if (argc > 1 && (!std::filesystem::exists(node) || !std::filesystem::exists(worker) ||
                             !std::filesystem::exists(roslyn)))
                throw std::runtime_error(
                    "Incomplete runtime bundle; use --config for development builds");
            config = {
                {"roots", argc == 1 ? Json::array() : Json::array({argv[2]})},
                {"engines",
                 {{"typescript", {freeflight::pathToUtf8(node), freeflight::pathToUtf8(worker)}},
                  {"javascript", {freeflight::pathToUtf8(node), freeflight::pathToUtf8(worker)}},
                  {"csharp", {freeflight::pathToUtf8(roslyn)}}}}};
        }
        freeflight::Server server(config);
        std::mutex outputMutex;
        auto send = [&](Json response) {
            std::lock_guard guard(outputMutex);
            std::cout << response.dump() << '\n' << std::flush;
        };
        auto error = [&](const Json &id, int code, const std::string &message,
                         Json data = nullptr) {
            Json detail = {{"code", code}, {"message", message}};
            if (!data.is_null())
                detail["data"] = std::move(data);
            send({{"jsonrpc", "2.0"}, {"id", id}, {"error", detail}});
        };
        auto result = [&](const Json &id, Json value, bool modern) {
            if (modern) {
                value["resultType"] = "complete";
                value["_meta"] = {{"io.modelcontextprotocol/serverInfo", identity}};
            }
            send({{"jsonrpc", "2.0"}, {"id", id}, {"result", value}});
        };
        std::mutex queueMutex;
        std::condition_variable ready;
        std::deque<std::shared_ptr<Job>> queue;
        std::map<std::string, std::shared_ptr<Job>> pending;
        bool closing = false;
        bool initialized = false;
        bool initializationSent = false;
        Json deferredRoots = nullptr;
        bool deferredInvalidation = false;
        bool legacyRoots = false;
        bool legacyRootChanges = false;
        std::string rootsRequest;
        unsigned long rootsSequence = 0;
        auto requestRoots = [&] {
            rootsRequest = "freeflight-roots-" + std::to_string(++rootsSequence);
            send({{"jsonrpc", "2.0"}, {"id", rootsRequest}, {"method", "roots/list"}});
        };
        auto validRoots = [](const Json &value) {
            if (!value.is_object() || !value.contains("roots") || !value["roots"].is_array() ||
                value["roots"].size() > 32)
                return false;
            std::set<std::string> seen;
            for (const auto &root : value["roots"]) {
                if (!root.is_object() || !root.contains("uri") || !root["uri"].is_string())
                    return false;
                const auto uri = root["uri"].get<std::string>();
                if (!uri.starts_with("file://") || uri.size() > 8192 || !seen.insert(uri).second ||
                    (root.contains("name") &&
                     (!root["name"].is_string() || root["name"].get<std::string>().size() > 1024)))
                    return false;
            }
            return true;
        };
        std::jthread executor([&] {
            while (true) {
                std::shared_ptr<Job> job;
                bool invalidateRoots = false;
                {
                    std::unique_lock lock(queueMutex);
                    ready.wait(lock, [&] {
                        return closing || !queue.empty() || !deferredRoots.is_null();
                    });
                    if (closing && queue.empty() && deferredRoots.is_null())
                        return;
                    if (!deferredRoots.is_null()) {
                        invalidateRoots = deferredInvalidation;
                        deferredInvalidation = false;
                        job = std::make_shared<Job>(Job{nullptr,
                                                        {{"name", "workspace.clientRoots"}},
                                                        false,
                                                        {},
                                                        std::move(deferredRoots)});
                        deferredRoots = nullptr;
                    } else {
                        job = queue.front();
                        queue.pop_front();
                    }
                }
                Json response;
                try {
                    if (invalidateRoots)
                        server.clientRoots(Json::array());
                    if (!job->clientRoots.is_null())
                        server.clientRoots(job->clientRoots);
                    auto value = server.call(job->params.at("name").get<std::string>(),
                                             job->params.value("arguments", Json::object()),
                                             job->stop.get_token());
                    response = {
                        {"content", Json::array({{{"type", "text"}, {"text", value.dump()}}})},
                        {"structuredContent", value.is_object() ? value : Json{{"items", value}}},
                        {"isError", false}};
                } catch (const std::exception &exception) {
                    response = {
                        {"content", Json::array({{{"type", "text"}, {"text", exception.what()}}})},
                        {"isError", true}};
                }
                // Cancellation and delivery share a lock, preventing a post-cancel reply.
                std::lock_guard guard(queueMutex);
                if (!job->id.is_null() && !job->stop.stop_requested())
                    result(job->id, response, job->modern);
                pending.erase(job->id.dump());
            }
        });
        std::string line;
        while (true) {
            line.clear();
            bool oversized = false;
            char character;
            while (std::cin.get(character) && character != '\n') {
                if (line.size() < 1024 * 1024)
                    line.push_back(character);
                else
                    oversized = true;
            }
            if (line.empty() && !std::cin)
                break;
            if (oversized) {
                error(nullptr, -32600, "Message exceeds 1 MiB");
                continue;
            }
            Json request;
            try {
                request = Json::parse(line, boundedJsonDepth);
            } catch (...) {
                error(nullptr, -32700, "Parse error");
                continue;
            }
            // Legacy server-request replies use the opposite JSON-RPC direction.
            // Only the latest outstanding ID can update candidates; never treat
            // arbitrary client-supplied result objects as filesystem authority.
            if (request.is_object() && request.value("jsonrpc", Json()) == "2.0" &&
                !request.contains("method") && request.contains("id") &&
                (request.contains("result") || request.contains("error"))) {
                if (!rootsRequest.empty() && request["id"] == rootsRequest) {
                    rootsRequest.clear();
                    std::lock_guard guard(queueMutex);
                    deferredRoots = request.contains("result") && !request.contains("error") &&
                                            validRoots(request["result"])
                                        ? request["result"]["roots"]
                                        : Json::array();
                    ready.notify_one();
                }
                continue;
            }
            if (!request.is_object() || request.value("jsonrpc", Json()) != "2.0" ||
                !request.contains("method") || !request["method"].is_string()) {
                error(nullptr, -32600, "Invalid request");
                continue;
            }
            const auto id = request.value("id", Json());
            if (request.contains("id") && !(id.is_string() || id.is_number_integer())) {
                error(nullptr, -32600, "Invalid request id");
                continue;
            }
            const auto method = request["method"].get<std::string>();
            const auto params = request.value("params", Json::object());
            if (!params.is_object()) {
                if (request.contains("id"))
                    error(id, -32602, "params must be an object");
                continue;
            }
            if (!request.contains("id")) {
                if (method == "notifications/initialized" && initializationSent && !initialized) {
                    initialized = true;
                    if (legacyRoots)
                        requestRoots();
                }
                if (method == "notifications/roots/list_changed" && initialized &&
                    legacyRootChanges) {
                    // Revoke associations before awaiting refresh; an unresponsive
                    // client must not leave stale candidate sessions active.
                    {
                        std::lock_guard guard(queueMutex);
                        deferredRoots = Json::array();
                        deferredInvalidation = true;
                        ready.notify_one();
                    }
                    requestRoots();
                }
                if (method == "notifications/cancelled" && params.contains("requestId")) {
                    std::lock_guard guard(queueMutex);
                    if (auto found = pending.find(params["requestId"].dump());
                        found != pending.end())
                        found->second->stop.request_stop();
                }
                continue;
            }
            const auto meta = params.value("_meta", Json::object());
            const bool modern = meta.is_object() && meta.contains(versionKey);
            if (modern) {
                if (!meta[versionKey].is_string() || !meta.contains(capabilitiesKey) ||
                    !meta[capabilitiesKey].is_object()) {
                    error(id, -32602, "Invalid protocol metadata");
                    continue;
                }
                if (meta[versionKey] != version) {
                    error(id, -32022, "Unsupported protocol version",
                          {{"supported", {version}}, {"requested", meta[versionKey]}});
                    continue;
                }
            }
            if (method == "server/discover") {
                if (!modern) {
                    error(id, -32602, "Protocol metadata required");
                    continue;
                }
                result(id,
                       {{"supportedVersions", {version}},
                        {"capabilities", {{"tools", Json::object()}}}},
                       true);
            } else if (method == "initialize") {
                if (modern || !params.contains("protocolVersion") ||
                    !params["protocolVersion"].is_string() || !params.contains("capabilities") ||
                    !params["capabilities"].is_object() || !params.contains("clientInfo") ||
                    !params["clientInfo"].is_object()) {
                    error(id, -32602, "Invalid initialization");
                    continue;
                }
                initializationSent = true;
                initialized = false;
                legacyRoots = params["capabilities"].contains("roots") &&
                              params["capabilities"]["roots"].is_object();
                legacyRootChanges = legacyRoots && params["capabilities"]["roots"].value(
                                                       "listChanged", Json()) == true;
                rootsRequest.clear();
                const auto requested = params["protocolVersion"].get<std::string>();
                const auto negotiated =
                    requested == "2025-06-18" ? requested : std::string("2025-11-25");
                result(id,
                       {{"protocolVersion", negotiated},
                        {"serverInfo", identity},
                        {"capabilities", {{"tools", Json::object()}}}},
                       false);
            } else if (method == "ping") {
                result(id, Json::object(), modern);
            } else if (!modern && !initialized) {
                error(id, -32600, "Initialize before making legacy requests");
            } else if (method == "tools/list") {
                result(id, {{"tools", server.tools()}}, modern);
            } else if (method == "tools/call") {
                if (!params.contains("name") || !params["name"].is_string() ||
                    (params.contains("arguments") && !params["arguments"].is_object())) {
                    error(id, -32602, "Invalid tool call");
                    continue;
                }
                const auto name = params["name"].get<std::string>();
                if (name != "workspace.discover" && name != "workspace.list" &&
                    name != "workspace.open" && name != "workspace.close" &&
                    name != "workspace.clientRoots" && name != "engine.capabilities" &&
                    name != "semantic.query") {
                    error(id, -32602, "Unknown tool");
                    continue;
                }
                Json roots = nullptr;
                if (name == "workspace.clientRoots") {
                    if (!params.value("arguments", Json::object()).empty()) {
                        error(id, -32602, "workspace.clientRoots accepts no arguments");
                        continue;
                    }
                    const bool supportsRoots = modern && meta[capabilitiesKey].contains("roots") &&
                                               meta[capabilitiesKey]["roots"].is_object();
                    if (modern && params.contains("inputResponses")) {
                        if (!supportsRoots || !params["inputResponses"].is_object() ||
                            !params["inputResponses"].contains("roots") ||
                            !validRoots(params["inputResponses"]["roots"])) {
                            error(id, -32602, "Invalid roots inputResponses");
                            continue;
                        }
                        roots = params["inputResponses"]["roots"]["roots"];
                    } else if (supportsRoots) {
                        send({{"jsonrpc", "2.0"},
                              {"id", id},
                              {"result",
                               {{"resultType", "input_required"},
                                {"inputRequests", {{"roots", {{"method", "roots/list"}}}}},
                                {"_meta", {{"io.modelcontextprotocol/serverInfo", identity}}}}}});
                        continue;
                    } else if (!modern && legacyRoots && rootsRequest.empty()) {
                        requestRoots();
                    }
                }
                std::lock_guard guard(queueMutex);
                if (pending.contains(id.dump())) {
                    error(id, -32600, "Duplicate in-flight id");
                    continue;
                }
                if (pending.size() >= 16) {
                    error(id, -32603, "Request capacity exceeded");
                    continue;
                }
                auto job = std::make_shared<Job>(Job{id, params, modern, {}, roots});
                pending[id.dump()] = job;
                queue.push_back(job);
                ready.notify_one();
            } else {
                error(id, -32601, "Method not found");
            }
        }
        {
            std::lock_guard guard(queueMutex);
            closing = true;
            for (auto &[id, job] : pending) {
                (void)id;
                job->stop.request_stop();
            }
        }
        ready.notify_one();
        executor.join();
        return 0;
    } catch (const std::exception &exception) {
        std::cerr << Json{{"level", "error"}, {"message", exception.what()}}.dump() << '\n';
        return 1;
    }
}

#ifdef _WIN32
int wmain(int argc, wchar_t **argv) {
    try {
        std::vector<std::string> arguments;
        for (int i = 0; i < argc; ++i)
            arguments.push_back(freeflight::pathToUtf8(std::filesystem::path(argv[i])));
        return runMain(arguments);
    } catch (const std::exception &) {
        std::cerr << "Cannot decode command-line arguments as Unicode\n";
        return 1;
    }
}
#else
int main(int argc, char **argv) {
    return runMain(std::vector<std::string>(argv, argv + argc));
}
#endif
