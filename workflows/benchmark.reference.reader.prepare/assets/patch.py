# SPDX-License-Identifier: Apache-2.0
"""Only generated snapshots change. Every replacement asserts its exact source."""
def replace(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def patch_reader(p):
 s=p.read_text();s=replace(s,"        for (;;) {\n            check(token, deadline);\n            const auto newline = impl_->buffered.find('\\n');", """        // Search only newly appended bytes until this response's delimiter arrives.
        // A buffered tail from a previous response is searched once at request entry.
        auto newline = impl_->buffered.find('\\n');
        for (;;) {
            check(token, deadline);""")
 s=replace(s,'impl_->buffered.substr(0, newline),','impl_->buffered.cbegin(),\n                    impl_->buffered.cbegin() + static_cast<std::ptrdiff_t>(newline),')
 s=replace(s,"            impl_->buffered.append(buffer.data(), count);\n            const auto end = impl_->buffered.find('\\n');\n            if ((end == std::string::npos && impl_->buffered.size() > max_line) ||\n                (end != std::string::npos && end > max_line))", """            const auto previousSize = impl_->buffered.size();
            impl_->buffered.append(buffer.data(), count);
            newline = impl_->buffered.find('\\n', previousSize);
            if ((newline == std::string::npos && impl_->buffered.size() > max_line) ||
                (newline != std::string::npos && newline > max_line))""")
 p.write_text(s)
def patch_tests(p):
 s=p.read_text();s=replace(s,'        if (mode == "oversize") {',r'''        if (mode == "coalesced") {
            if (message["id"] == 1)
                std::cout << "{\"id\":1,\"value\":\"first\"}\n{\"id\":2,\"value\":\"tail\"}\n" << std::flush;
            continue;
        }
        if (mode == "at-limit" || mode == "over-limit-newline") {
            std::string encoded = json{{"id", message["id"]}, {"pad", ""}}.dump();
            const auto target = 8 * 1024 * 1024 + (mode == "at-limit" ? 0 : 1);
            encoded.insert(encoded.size() - 2, target - encoded.size(), 'x');
            std::cout << encoded << '\n' << std::flush;
            continue;
        }
        if (mode == "fragmented-large") {
            const auto encoded = json{{"id", message["id"]}, {"pad", std::string(65536, 'x') + "日本語λ"}}.dump() + '\n';
            for (std::size_t i = 0; i < encoded.size(); i += 1023)
                std::cout << encoded.substr(i, 1023) << std::flush;
            continue;
        }
        if (mode == "oversize") {''')
 marker='        for (const auto &[mode, error] :'
 test=r'''        {
            Process process({executable, "--worker", "coalesced"});
            require(process.request({{"id", 1}})["value"] == "first", "first coalesced frame changed");
            require(process.request({{"id", 2}})["value"] == "tail", "buffered frame tail lost");
        }
        {
            Process process({executable, "--worker", "fragmented-large"});
            for (int i = 0; i < 3; ++i)
                require(process.request({{"id", i}})["pad"] == std::string(65536, 'x') + "日本語λ", "large fragmented frame changed");
        }
        {
            Process process({executable, "--worker", "at-limit"});
            const auto result = process.request({{"id", 42}});
            require(result.dump().size() == 8 * 1024 * 1024, "exact response limit changed");
        }
        {
            Process process({executable, "--worker", "over-limit-newline"});
            fails([&] { process.request({{"id", 42}}); }, "response exceeds limit");
            fails([&] { process.request({{"id", 43}}); }, "stopped");
        }
'''
 s=replace(s,marker,test+marker);p.write_text(s)