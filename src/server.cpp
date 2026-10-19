#include "freeflight/server.hpp"
#include <algorithm>
#include <fstream>
#include <stdexcept>

namespace freeflight {
namespace fs = std::filesystem;

static bool within(const fs::path &root, const fs::path &path) {
    const auto relative = path.lexically_relative(root);
    return !relative.empty() && !relative.is_absolute() && *relative.begin() != "..";
}

Server::Server(const Json &configuration) {
    for (const auto &root : configuration.at("roots")) {
        auto path = fs::canonical(root.get<std::string>());
        if (!fs::is_directory(path))
            throw std::runtime_error("Root is not a directory");
        roots_.push_back(path);
    }
    if (roots_.empty() || roots_.size() > 32)
        throw std::runtime_error("Require 1–32 roots");
    const auto engines = configuration.value("engines", Json::object());
    if (!engines.is_object())
        throw std::runtime_error("engines must be an object");
    for (const auto &[language, command] : engines.items()) {
        auto args = command.get<std::vector<std::string>>();
        if (args.empty() || !fs::path(args.front()).is_absolute())
            throw std::runtime_error("Engine executable must be an absolute path");
        commands_.emplace(language, std::move(args));
    }
}

fs::path Server::authorize(const std::string &value) const {
    auto path = fs::canonical(value);
    for (const auto &root : roots_) {
        if (within(root, path))
            return path;
    }
    throw std::runtime_error("Path is outside startup-authorized workspace roots");
}

Json Server::tools() const {
    const Json object = {
        {"type", "object"}, {"properties", Json::object()}, {"additionalProperties", false}};
    Json query = {{"type", "object"},
                  {"properties",
                   {{"root", {{"type", "string"}}},
                    {"language", {{"type", "string"}}},
                    {"operation", {{"type", "string"}}},
                    {"arguments", {{"type", "object"}}}}},
                  {"required", {"root", "language", "operation"}},
                  {"additionalProperties", false}};
    auto capability = query;
    capability["properties"].erase("operation");
    capability["properties"].erase("arguments");
    capability["required"] = {"root", "language"};
    const Json readOnly = {{"readOnlyHint", true},
                           {"destructiveHint", false},
                           {"idempotentHint", true},
                           {"openWorldHint", false}};
    return Json::array(
        {{{"name", "workspace.discover"},
          {"description", "List authorized roots and bounded project discovery."},
          {"inputSchema", object},
          {"annotations", readOnly}},
         {{"name", "engine.capabilities"},
          {"description", "Open an authorized root and discover actual worker operations."},
          {"inputSchema", capability},
          {"annotations", readOnly}},
         {{"name", "semantic.query"},
          {"description", "Invoke an operation reported by engine.capabilities. Rename returns a "
                          "preview; no files are written."},
          {"inputSchema", query},
          {"annotations", readOnly}}});
}

Server::Engine &Server::engine(const fs::path &root, const std::string &language,
                               std::stop_token stop) {
    const auto command = commands_.find(language);
    if (command == commands_.end())
        throw std::runtime_error("Language engine is not configured");
    const auto key = root.string() + "\n" + language;
    if (auto found = engines_.find(key); found != engines_.end())
        return found->second;
    if (engines_.size() >= 8)
        throw std::runtime_error("Worker limit reached; restart with fewer roots");
    auto process = std::make_unique<Process>(command->second);
    auto response = process->request(
        {{"id", ++sequence_}, {"method", "capabilities"}, {"params", Json::object()}}, stop);
    if (response.contains("error"))
        throw std::runtime_error(response["error"].dump());
    auto capabilities = response.at("result");
    auto opened = process->request(
        {{"id", ++sequence_}, {"method", "open"}, {"params", {{"root", root.string()}}}}, stop);
    if (opened.contains("error"))
        throw std::runtime_error(opened["error"].dump());
    return engines_.emplace(key, Engine{std::move(process), capabilities}).first->second;
}

Json Server::call(const std::string &name, const Json &arguments, std::stop_token stop) {
    if (!arguments.is_object())
        throw std::runtime_error("arguments must be an object");
    if (name == "workspace.discover") {
        if (!arguments.empty())
            throw std::runtime_error("workspace.discover accepts no arguments");
        Json workspaces = Json::array();
        for (const auto &root : roots_) {
            Json projects = Json::array();
            std::size_t scanned = 0;
            bool truncated = false;
            fs::recursive_directory_iterator it(root,
                                                fs::directory_options::skip_permission_denied);
            for (const auto &entry : it) {
                if (stop.stop_requested())
                    throw std::runtime_error("Cancelled");
                if (++scanned > 50000) {
                    truncated = true;
                    break;
                }
                const auto filename = entry.path().filename().string();
                if (entry.is_directory() &&
                    (filename == ".git" || filename == "node_modules" || filename == "bin" ||
                     filename == "obj" || filename == ".dockpipe")) {
                    it.disable_recursion_pending();
                    continue;
                }
                if (entry.is_symlink()) {
                    it.disable_recursion_pending();
                    continue;
                }
                const auto ext = entry.path().extension().string();
                if (ext == ".sln" || ext == ".slnx" || ext == ".csproj" ||
                    filename == "tsconfig.json" || filename == "jsconfig.json" ||
                    filename == "package.json")
                    projects.push_back(entry.path().string());
            }
            std::sort(projects.begin(), projects.end());
            workspaces.push_back(
                {{"root", root.string()}, {"projects", projects}, {"truncated", truncated}});
        }
        return {{"workspaces", workspaces}};
    }
    if (name != "semantic.query" && name != "engine.capabilities")
        throw std::runtime_error("Unknown tool");
    for (const auto &[key, value] : arguments.items()) {
        (void)value;
        if (key != "root" && key != "language" &&
            !(name == "semantic.query" && (key == "operation" || key == "arguments")))
            throw std::runtime_error("Unknown argument: " + key);
    }
    const auto root = authorize(arguments.at("root").get<std::string>());
    if (!fs::is_directory(root))
        throw std::runtime_error("Workspace root is not a directory");
    const auto language = arguments.at("language").get<std::string>();
    const auto key = root.string() + "\n" + language;
    try {
        auto &selected = engine(root, language, stop);
        if (name == "engine.capabilities")
            return selected.capabilities;
        const auto operation = arguments.at("operation").get<std::string>();
        const auto operations = selected.capabilities.at("operations");
        if (std::find(operations.begin(), operations.end(), operation) == operations.end())
            throw std::runtime_error("Operation is not supported by this engine");
        auto params = arguments.value("arguments", Json::object());
        if (!params.is_object())
            throw std::runtime_error("Operation arguments must be an object");
        if (params.contains("file")) {
            const auto path = authorize(params["file"].get<std::string>());
            if (!within(root, path))
                throw std::runtime_error("Document is outside selected workspace");
            params["file"] = path.string();
        }
        params["root"] = root.string();
        auto response = selected.process->request(
            {{"id", ++sequence_}, {"method", operation}, {"params", params}}, stop);
        if (response.contains("error"))
            throw std::runtime_error(response["error"].dump());
        return response.at("result");
    } catch (...) {
        engines_.erase(key); // A later explicit request lazily recovers; never replay mutations.
        throw;
    }
}
} // namespace freeflight
