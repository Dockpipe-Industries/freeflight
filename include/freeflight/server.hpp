#pragma once
#include "freeflight/process.hpp"
#include <filesystem>
#include <map>
#include <memory>
#include <stop_token>
#include <string>

namespace freeflight {
using Json = nlohmann::json;

class Server {
  public:
    explicit Server(const Json &configuration);
    Json tools() const;
    Json call(const std::string &name, const Json &arguments, std::stop_token stop);

  private:
    struct Engine {
        std::unique_ptr<Process> process;
        Json capabilities;
    };
    std::vector<std::filesystem::path> roots_;
    std::map<std::string, std::vector<std::string>> commands_;
    std::map<std::string, Engine> engines_;
    std::filesystem::path authorize(const std::string &path) const;
    Engine &engine(const std::filesystem::path &root, const std::string &language,
                   std::stop_token stop);
    unsigned long sequence_ = 0;
};
} // namespace freeflight
