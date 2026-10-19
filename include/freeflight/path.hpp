#pragma once

#include <filesystem>
#include <string>
#include <string_view>

namespace freeflight {
// MCP/worker JSON and normalized CLI arguments use UTF-8, independent of the
// Windows ANSI codepage. Keep native filesystem paths until crossing that boundary.
inline std::filesystem::path pathFromUtf8(std::string_view value) {
    return std::filesystem::path(std::u8string(value.begin(), value.end()));
}
inline std::string pathToUtf8(const std::filesystem::path &value) {
    const auto encoded = value.u8string();
    return std::string(encoded.begin(), encoded.end());
}
} // namespace freeflight
