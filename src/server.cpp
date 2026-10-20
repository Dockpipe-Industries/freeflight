#include "freeflight/server.hpp"
#include "freeflight/path.hpp"
#include <algorithm>
#include <fstream>
#include <set>
#include <stdexcept>

namespace freeflight {
namespace fs = std::filesystem;

static bool within(const fs::path &root, const fs::path &path) {
    const auto relative = path.lexically_relative(root);
    return !relative.empty() && !relative.is_absolute() && *relative.begin() != "..";
}

Server::Server(const Json &configuration) {
    resources_ = {{"maxFileBytes", 32 * 1024 * 1024},
                  {"maxWorkspaceBytes", 512 * 1024 * 1024},
                  {"maxFiles", 50000},
                  {"maxDirectoryEntries", 500000}};
    const Json ceilings = {{"maxFileBytes", 256 * 1024 * 1024},
                           {"maxWorkspaceBytes", 2147483648LL},
                           {"maxFiles", 200000},
                           {"maxDirectoryEntries", 2000000}};
    const auto resources = configuration.value("resources", Json::object());
    if (!resources.is_object())
        throw std::runtime_error("resources must be an object in operator startup configuration");
    for (const auto &[name, value] : resources.items()) {
        if (!ceilings.contains(name) || !value.is_number_integer() || value <= 0 ||
            value > ceilings.at(name))
            throw std::runtime_error("Invalid startup resource limit: " + name);
        resources_[name] = value;
    }
    if (resources_["maxFileBytes"] > resources_["maxWorkspaceBytes"])
        throw std::runtime_error("maxFileBytes must not exceed maxWorkspaceBytes");
    sourceRoots_ = !configuration.contains("roots") && configuration.contains("trustedRoots");
    const auto accessRoots =
        configuration.value("roots", configuration.value("trustedRoots", Json::array()));
    if (!accessRoots.is_array() || accessRoots.size() > 32)
        throw std::runtime_error("Require 0–32 startup roots");
    for (const auto &root : accessRoots) {
        if (!pathFromUtf8(root.get<std::string>()).is_absolute())
            throw std::runtime_error("Startup roots must be absolute");
        auto path = fs::canonical(pathFromUtf8(root.get<std::string>()));
        if (!fs::is_directory(path))
            throw std::runtime_error("Root is not a directory");
        roots_.push_back(path);
    }
    active_ = roots_;
    const auto engines = configuration.value("engines", Json::object());
    if (!engines.is_object())
        throw std::runtime_error("engines must be an object");
    for (const auto &[language, command] : engines.items()) {
        auto args = command.get<std::vector<std::string>>();
        if (args.empty() || !pathFromUtf8(args.front()).is_absolute())
            throw std::runtime_error("Engine executable must be an absolute path");
        commands_.emplace(language, std::move(args));
    }
    const auto csharp = configuration.value("csharp", Json::object());
    if (!csharp.is_object())
        throw std::runtime_error("csharp must be an operator startup configuration object");
    for (const auto &[key, value] : csharp.items()) {
        if ((key != "mode" && key != "project") || !value.is_string())
            throw std::runtime_error("Invalid csharp startup setting: " + key);
    }
    auto command = commands_.find("csharp");
    const bool legacyTrust =
        command != commands_.end() && std::find(command->second.begin(), command->second.end(),
                                                "--trusted-msbuild") != command->second.end();
    const auto mode = csharp.value("mode", legacyTrust ? "trusted-msbuild" : "safe-source");
    if (mode != "trusted-msbuild" && mode != "safe-source")
        throw std::runtime_error("csharp.mode must be safe-source or trusted-msbuild");
    trustedCsharp_ = mode == "trusted-msbuild";
    if (legacyTrust && !trustedCsharp_)
        throw std::runtime_error(
            "csharp.mode conflicts with explicitly configured trusted worker arguments");
    const auto trusted = configuration.value("trustedRoots", Json::array());
    if (!trusted.is_array() || trusted.size() > 32)
        throw std::runtime_error(
            "trustedRoots must contain at most 32 explicitly authorized directories");
    if (!trusted.empty() && trustedCsharp_)
        throw std::runtime_error("Use per-root trustedRoots or legacy global C# trust, not both");
    for (const auto &entry : trusted) {
        const auto root = authorize(entry.get<std::string>());
        if (!fs::is_directory(root))
            throw std::runtime_error("Each trustedRoots entry must be a directory within roots");
        trustedRoots_.push_back(root);
    }
    if (csharp.contains("project")) {
        defaultProject_ = csharp.at("project").get<std::string>();
        const auto project = pathFromUtf8(defaultProject_);
        if ((!trustedCsharp_ && trustedRoots_.empty()) || project.empty() ||
            project.has_root_path() ||
            (project.extension() != ".sln" && project.extension() != ".csproj") ||
            std::any_of(project.begin(), project.end(),
                        [](const auto &part) { return part == ".."; }))
            throw std::runtime_error("csharp.project requires trusted-msbuild and an in-root "
                                     "relative .sln/.csproj path");
    }
}

bool Server::trusts(const fs::path &root) const {
    return trustedCsharp_ ||
           std::any_of(trustedRoots_.begin(), trustedRoots_.end(),
                       [&](const auto &trusted) { return within(trusted, root); });
}

// Inspect only ancestors of the requested document. Never recursively load a source
// folder containing unrelated repositories. The worker still resolves ambiguity
// within the selected repository using its structured project-selection contract.
fs::path Server::route(const fs::path &root, const fs::path &file, const std::string &language,
                       std::stop_token stop) const {
    fs::path project, solution, package;
    std::size_t entries = 0;
    for (auto cursor = file.parent_path(); within(root, cursor); cursor = cursor.parent_path()) {
        if (stop.stop_requested())
            throw std::runtime_error("Request cancelled");
        if (fs::exists(cursor / ".git") || fs::exists(cursor / ".hg"))
            return cursor;
        for (const auto &entry : fs::directory_iterator(cursor)) {
            if (stop.stop_requested())
                throw std::runtime_error("Request cancelled");
            if (++entries > resources_.at("maxDirectoryEntries").get<std::size_t>())
                throw std::runtime_error("Project routing directory entry limit exceeded");
            if (entry.is_symlink() || !entry.is_regular_file())
                continue;
            const auto extension = entry.path().extension();
            if (language == "csharp") {
                if (extension == ".sln" && solution.empty())
                    solution = cursor;
                if (extension == ".csproj" && project.empty())
                    project = cursor;
            } else if ((language == "typescript" || language == "javascript") && package.empty() &&
                       (entry.path().filename() == "tsconfig.json" ||
                        entry.path().filename() == "jsconfig.json" ||
                        entry.path().filename() == "package.json")) {
                package = cursor;
            }
        }
        if (cursor == root)
            break;
    }
    if (!solution.empty())
        return solution;
    if (!project.empty())
        return project;
    if (!package.empty())
        return package;
    // Loose files get a bounded containing workspace, not the whole source tree.
    return file.parent_path();
}

fs::path Server::authorize(const std::string &value) const {
    const auto supplied = pathFromUtf8(value);
    if (roots_.empty() || !supplied.is_absolute())
        throw std::runtime_error("Path is outside startup-authorized workspace roots; restart "
                                 "with --workspace or an explicit --config policy");
    // Native filesystem_error::what() can contain Windows ANSI path bytes.
    // Keep errors crossing the JSON boundary in controlled UTF-8 instead.
    std::error_code resolutionError;
    auto path = fs::canonical(supplied, resolutionError);
    if (resolutionError)
        throw std::runtime_error("Workspace path does not exist or cannot be resolved: " + value);
    for (const auto &root : roots_) {
        if (within(root, path))
            return path;
    }
    throw std::runtime_error("Path is outside startup-authorized workspace roots");
}

void Server::close(const fs::path &root) {
    std::erase_if(explicitWorkspaces_, [&](const auto &path) { return within(root, path); });
    std::erase_if(engines_, [&](const auto &entry) { return within(root, entry.second.root); });
    std::erase_if(projects_, [&](const auto &entry) { return within(root, entry.first); });
    std::erase_if(active_, [&](const auto &path) { return within(root, path); });
    std::erase_if(associations_, [&](const auto &entry) { return within(root, entry.first); });
}

void Server::clientRoots(const Json &roots) {
    if (!roots.is_array() || roots.size() > 32)
        throw std::runtime_error("Client roots must be an array of at most 32 candidates");
    Json candidates = Json::array();
    std::set<std::string> seen;
    for (const auto &root : roots) {
        if (!root.is_object() || !root.contains("uri") || !root["uri"].is_string())
            throw std::runtime_error("Client root requires a file URI");
        const auto uri = root["uri"].get<std::string>();
        if (!uri.starts_with("file://") || uri.size() > 8192 || !seen.insert(uri).second ||
            (root.contains("name") &&
             (!root["name"].is_string() || root["name"].get<std::string>().size() > 1024)))
            throw std::runtime_error("Invalid or duplicate client root candidate");
        Json item = {{"uri", uri}};
        if (root.contains("name"))
            item["name"] = root["name"];
        candidates.push_back(std::move(item));
    }
    std::vector<fs::path> removed;
    for (const auto &[root, uri] : associations_)
        if (!seen.contains(uri))
            removed.push_back(root);
    for (const auto &root : removed)
        close(root);
    candidates_ = std::move(candidates);
}

static fs::path candidatePath(const std::string &uri) {
    std::string value;
    if (uri.starts_with("file:///"))
        value = uri.substr(7);
    else if (uri.starts_with("file://localhost/"))
        value = uri.substr(16);
    else
        throw std::runtime_error("Only local absolute file URI candidates can be associated");
    std::string decoded;
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (value[i] == '?' || value[i] == '#' || value[i] == '\\')
            throw std::runtime_error("Candidate URI must not contain query or fragment");
        if (value[i] == '%') {
            auto hex = [](char c) -> int {
                if (c >= '0' && c <= '9')
                    return c - '0';
                if (c >= 'a' && c <= 'f')
                    return c - 'a' + 10;
                if (c >= 'A' && c <= 'F')
                    return c - 'A' + 10;
                return -1;
            };
            if (i + 2 >= value.size() || hex(value[i + 1]) < 0 || hex(value[i + 2]) < 0)
                throw std::runtime_error("Invalid candidate URI escape");
            const auto byte = static_cast<char>((hex(value[i + 1]) << 4) | hex(value[i + 2]));
            if (!byte || byte == '/' || byte == '\\')
                throw std::runtime_error("NUL or encoded separator in candidate URI");
            decoded += byte;
            i += 2;
        } else {
            if (!value[i])
                throw std::runtime_error("NUL in candidate URI");
            decoded += value[i];
        }
    }
#ifdef _WIN32
    if (decoded.size() >= 3 && decoded[0] == '/' && decoded[2] == ':')
        decoded.erase(0, 1);
#endif
    return pathFromUtf8(decoded).lexically_normal();
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
    const Json lifecycle = {{"readOnlyHint", false},
                            {"destructiveHint", false},
                            {"idempotentHint", true},
                            {"openWorldHint", false}};
    auto closeLifecycle = lifecycle;
    closeLifecycle["idempotentHint"] = false;
    const Json rootSchema = {{"type", "object"},
                             {"properties", {{"root", {{"type", "string"}}}}},
                             {"required", {"root"}},
                             {"additionalProperties", false}};
    auto openSchema = rootSchema;
    openSchema["properties"]["candidateUri"] = {{"type", "string"}};
    openSchema["properties"]["project"] = {{"type", "string"}};
    openSchema["properties"]["reload"] = {{"type", "boolean"}};
    return Json::array(
        {{{"name", "workspace.discover"},
          {"description", "List authorized roots and bounded project discovery."},
          {"inputSchema", object},
          {"annotations", readOnly}},
         {{"name", "workspace.list"},
          {"description", "List immutable allowed roots, active workspaces and informational "
                          "client candidates without scanning files."},
          {"inputSchema", object},
          {"annotations", readOnly}},
         {{"name", "workspace.open"},
          {"description", "Activate a directory within startup policy. Optional candidateUri "
                          "associates its lifecycle with a client candidate; never grants access. "
                          "Trusted C# may select a relative project; reload=true stops this root's "
                          "workers so the next query reloads the graph. Trust is startup-only."},
          {"inputSchema", openSchema},
          {"annotations", lifecycle}},
         {{"name", "workspace.close"},
          {"description", "Close an active workspace and descendants, stopping workers. Startup "
                          "authority is retained for explicit reopening."},
          {"inputSchema", rootSchema},
          {"annotations", closeLifecycle}},
         {{"name", "workspace.clientRoots"},
          {"description",
           "Optional client-roots compatibility discovery. Candidates are informational, never "
           "authorization. Removed associated workspaces close."},
          {"inputSchema", object},
          {"annotations", lifecycle}},
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
    const auto key = pathToUtf8(root) + "\n" + language;
    if (auto found = engines_.find(key); found != engines_.end())
        return found->second;
    if (engines_.size() >= 8)
        throw std::runtime_error("Worker limit reached; restart with fewer roots");
    auto argv = command->second;
    if (language == "csharp" && trusts(root) &&
        std::find(argv.begin(), argv.end(), "--trusted-msbuild") == argv.end())
        argv.push_back("--trusted-msbuild");
    auto process = std::make_unique<Process>(argv);
    auto response = process->request(
        {{"id", ++sequence_}, {"method", "capabilities"}, {"params", Json::object()}}, stop);
    if (response.contains("error"))
        throw EngineError(response["error"]);
    auto capabilities = response.at("result");
    Json openParams = {{"root", pathToUtf8(root)}, {"resources", resources_}};
    if (language == "csharp" && trusts(root)) {
        const auto selected = projects_.contains(root) ? projects_.at(root) : defaultProject_;
        if (!selected.empty())
            openParams["project"] = selected;
    }
    auto opened =
        process->request({{"id", ++sequence_}, {"method", "open"}, {"params", openParams}}, stop);
    if (opened.contains("error"))
        throw EngineError(opened["error"]);
    capabilities["analysis"] = opened.at("result");
    for (const auto *field :
         {"mode", "fidelity", "selectedProject", "loadWarnings", "degradedFidelity", "limitations"})
        if (opened.at("result").contains(field))
            capabilities[field] = opened.at("result").at(field);
    return engines_.emplace(key, Engine{std::move(process), capabilities, root}).first->second;
}

Json Server::call(const std::string &name, const Json &arguments, std::stop_token stop) {
    if (!arguments.is_object())
        throw std::runtime_error("arguments must be an object");
    if (name == "workspace.list" || name == "workspace.clientRoots") {
        if (!arguments.empty())
            throw std::runtime_error(name + " accepts no arguments");
        Json allowed = Json::array(), active = Json::array(), trusted = Json::array();
        for (const auto &root : trustedRoots_)
            trusted.push_back(pathToUtf8(root));
        for (const auto &root : roots_)
            allowed.push_back(pathToUtf8(root));
        for (const auto &root : active_) {
            Json item = {{"root", pathToUtf8(root)},
                         {"csharp",
                          {{"mode", trusts(root) ? "trusted-msbuild" : "safe-source"},
                           {"project", trusts(root) ? (projects_.contains(root) ? projects_.at(root)
                                                                                : defaultProject_)
                                                    : ""}}},
                         {"engines", Json::object()}};
            for (const auto &[key, engine] : engines_) {
                if (engine.root == root)
                    item["engines"][key.substr(key.find('\n') + 1)] = engine.capabilities;
            }
            if (const auto association = associations_.find(root);
                association != associations_.end())
                item["candidateUri"] = association->second;
            active.push_back(std::move(item));
        }
        return {{"allowedRoots", allowed},
                {"trustedRoots", trusted},
                {"workspaces", active},
                {"candidates", candidates_},
                {"authorization", "startup-only"},
                {"dormant", active_.empty()}};
    }
    if (name == "workspace.open" || name == "workspace.close") {
        for (const auto &[key, value] : arguments.items()) {
            (void)value;
            if (key != "root" && !(name == "workspace.open" &&
                                   (key == "candidateUri" || key == "project" || key == "reload")))
                throw std::runtime_error("Unknown argument: " + key);
        }
        const auto supplied = arguments.at("root").get<std::string>();
        if (name == "workspace.close") {
            // Closing an existing path must work even after it disappears on disk.
            const auto root = pathFromUtf8(supplied).lexically_normal();
            if (std::find(active_.begin(), active_.end(), root) == active_.end())
                throw std::runtime_error("Workspace is not active");
            close(root);
            return {{"root", pathToUtf8(root)}, {"active", false}};
        }
        const auto root = authorize(supplied);
        if (!fs::is_directory(root))
            throw std::runtime_error("Workspace root is not a directory");
        std::string candidate;
        if (arguments.contains("candidateUri")) {
            candidate = arguments.at("candidateUri").get<std::string>();
            if (std::none_of(candidates_.begin(), candidates_.end(),
                             [&](const auto &item) { return item.at("uri") == candidate; }) ||
                (candidatePath(candidate) != root &&
                 candidatePath(candidate) != pathFromUtf8(supplied).lexically_normal()))
                throw std::runtime_error("Candidate URI does not match this authorized workspace");
            if (std::find(roots_.begin(), roots_.end(), root) != roots_.end())
                throw std::runtime_error(
                    "Pinned startup roots cannot be associated with client candidates");
        }
        const bool reload = arguments.value("reload", false);
        std::string selectedProject =
            projects_.contains(root) ? projects_.at(root) : defaultProject_;
        if (arguments.contains("project")) {
            if (!trusts(root))
                throw std::runtime_error(
                    "Project selection requires operator startup trustedRoots authorization; "
                    "requests cannot grant trust");
            const auto suppliedProject = arguments.at("project").get<std::string>();
            const auto relative = pathFromUtf8(suppliedProject);
            if (relative.empty() || relative.has_root_path() ||
                std::any_of(relative.begin(), relative.end(),
                            [](const auto &part) { return part == ".."; }) ||
                (relative.extension() != ".sln" && relative.extension() != ".csproj"))
                throw std::runtime_error("project must be an in-root relative .sln/.csproj path");
            const auto selected = authorize(pathToUtf8(root / relative));
            if (!within(root, selected) || !fs::is_regular_file(selected))
                throw std::runtime_error("Selected project is outside workspace or not a file");
            // Reject symlink components, even when their destination remains in-root.
            auto cursor = root;
            for (const auto &part : relative) {
                cursor /= part;
                if (fs::is_symlink(cursor))
                    throw std::runtime_error("Selected project cannot traverse symlinks");
            }
            const auto normalized = pathToUtf8(selected.lexically_relative(root));
            if (normalized != selectedProject && !reload &&
                engines_.contains(pathToUtf8(root) + "\ncsharp"))
                throw std::runtime_error(
                    "Project selection changed; invoke workspace.open with reload=true");
            selectedProject = normalized;
        }
        if (std::find(active_.begin(), active_.end(), root) == active_.end()) {
            if (active_.size() >= 32)
                throw std::runtime_error("Active workspace limit reached");
            active_.push_back(root);
            std::sort(active_.begin(), active_.end());
        }
        if (reload)
            std::erase_if(engines_, [&](const auto &entry) { return entry.second.root == root; });
        if (!selectedProject.empty())
            projects_[root] = selectedProject;
        if (!candidate.empty())
            associations_[root] = candidate;
        else
            associations_.erase(root);
        explicitWorkspaces_.insert(root);
        return {{"root", pathToUtf8(root)}, {"active", true}};
    }
    if (name == "workspace.discover") {
        if (!arguments.empty())
            throw std::runtime_error("workspace.discover accepts no arguments");
        Json workspaces = Json::array();
        for (const auto &root : active_) {
            Json projects = Json::array();
            std::set<std::string> languages;
            std::size_t scanned = 0;
            bool truncated = false;
            fs::recursive_directory_iterator it(root,
                                                fs::directory_options::skip_permission_denied);
            for (const fs::recursive_directory_iterator end; it != end; ++it) {
                const auto &entry = *it;
                if (stop.stop_requested())
                    throw std::runtime_error("Cancelled");
                if (++scanned > 50000) {
                    truncated = true;
                    break;
                }
                const auto filename = pathToUtf8(entry.path().filename());
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
                const auto ext = pathToUtf8(entry.path().extension());
                if (ext == ".cs")
                    languages.insert("csharp");
                else if (ext == ".ts" || ext == ".tsx" || ext == ".mts" || ext == ".cts")
                    languages.insert("typescript");
                else if (ext == ".js" || ext == ".jsx" || ext == ".mjs" || ext == ".cjs")
                    languages.insert("javascript");
                if (ext == ".sln" || ext == ".slnx" || ext == ".csproj" ||
                    filename == "tsconfig.json" || filename == "jsconfig.json" ||
                    filename == "package.json")
                    projects.push_back(pathToUtf8(entry.path()));
            }
            std::sort(projects.begin(), projects.end());
            workspaces.push_back({{"root", pathToUtf8(root)},
                                  {"projects", projects},
                                  {"languages", languages},
                                  {"truncated", truncated}});
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
    auto root = authorize(arguments.at("root").get<std::string>());
    if (std::find(active_.begin(), active_.end(), root) == active_.end())
        throw std::runtime_error("Workspace is not active; invoke workspace.open first");
    if (!fs::is_directory(root))
        throw std::runtime_error("Workspace root is not a directory");
    const auto language = arguments.at("language").get<std::string>();
    auto params = arguments.value("arguments", Json::object());
    if (!params.is_object())
        throw std::runtime_error("Operation arguments must be an object");
    if (params.contains("mode") || params.contains("trustedMsbuild") ||
        params.contains("trusted-msbuild") || params.contains("project") ||
        params.contains("csharp"))
        throw std::runtime_error("Trust is startup-only; select projects using workspace.open, not "
                                 "semantic query arguments");
    if (params.contains("resources"))
        throw std::runtime_error("Resource limits are owned by operator startup configuration");
    if (params.contains("file")) {
        const auto path = authorize(params["file"].get<std::string>());
        if (!within(root, path))
            throw std::runtime_error("Document is outside selected workspace");
        params["file"] = pathToUtf8(path);
        if (sourceRoots_ && !projects_.contains(root) &&
            std::find(roots_.begin(), roots_.end(), root) != roots_.end()) {
            root = route(root, path, language, stop);
            if (std::find(active_.begin(), active_.end(), root) == active_.end()) {
                if (active_.size() >= 32)
                    throw std::runtime_error("Active workspace limit reached");
                active_.push_back(root);
                std::sort(active_.begin(), active_.end());
            }
        }
    }
    if (sourceRoots_ && !params.contains("file") && !explicitWorkspaces_.contains(root) &&
        std::find(roots_.begin(), roots_.end(), root) != roots_.end())
        throw EngineError(
            {{"code", "workspace_selection_required"},
             {"root", pathToUtf8(root)},
             {"message", "Select a repository workspace or supply a document file"},
             {"remediation",
              "Invoke workspace.open with a repository directory within trustedRoots, then query "
              "that root. No configuration change is required."}});
    const auto key = pathToUtf8(root) + "\n" + language;
    params["root"] = pathToUtf8(root);
    try {
        auto &selected = engine(root, language, stop);
        if (name == "engine.capabilities")
            return selected.capabilities;
        const auto operation = arguments.at("operation").get<std::string>();
        const auto operations = selected.capabilities.at("operations");
        if (std::find(operations.begin(), operations.end(), operation) == operations.end())
            throw std::runtime_error("Operation is not supported by this engine");
        auto response = selected.process->request(
            {{"id", ++sequence_}, {"method", operation}, {"params", params}}, stop);
        if (response.contains("error"))
            throw EngineError(response["error"]);
        return response.at("result");
    } catch (const EngineError &error) {
        engines_.erase(key);
        auto detail = error.detail;
        detail["workspaceRoot"] = pathToUtf8(root);
        throw EngineError(std::move(detail));
    } catch (...) {
        engines_.erase(key); // A later explicit request lazily recovers; never replay mutations.
        throw;
    }
}
} // namespace freeflight
