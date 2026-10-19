#pragma once

#include <memory>
#include <stop_token>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace freeflight {
// Calls, including stop(), must be serialized by the owner. Cancellation is
// supported through the request's stop token, not a concurrent stop() call.
class Process {
  public:
    explicit Process(std::vector<std::string> argv);
    ~Process();
    Process(const Process &) = delete;
    Process &operator=(const Process &) = delete;
    nlohmann::json request(const nlohmann::json &message, std::stop_token token = {});
    void stop() noexcept;

  private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace freeflight
