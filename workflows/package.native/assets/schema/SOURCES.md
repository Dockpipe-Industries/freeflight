# Official MCPB manifest schema

Unmodified upstream files from `anthropics/mcpb` commit
`2a788100a60db19a6b1c018fb1cf84ae85de9537`, the npm `@anthropic-ai/mcpb@2.1.2`
source commit. Vendored under the included MIT license; no CLI code is vendored.

- [schema source](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/schemas/mcpb-manifest-v0.3.schema.json): SHA256 `3a0ac9d845711a1b9b17dfa5a52f8b60628239d6a86a9db417206a9efc78592d`
- [license](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/LICENSE): SHA256 `c8d40185f85962734fe6a50040cadafe0b3cdf91b4002364f4c96266b3a965d4`
- [valid fixture](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/test/valid-manifest.json): SHA256 `600244d6d85531cc9e1df35f6449b1fe85410d2c211e6c804643fad2ad3ecff9`
- [invalid fixture](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/test/invalid-manifest.json): SHA256 `e4273ade40725b79415f10a626e1ba5adc2efff9d7db32c6947ecd346490c95d`

The [official format documentation](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/README.md) defines MCPB as ZIP plus manifest and server files. Python standard-library ZIP creation is an implementation of that format, not a new package format. Draft-07 validation uses the project's existing jsonschema 4.25.1 tool dependency. No remote schemas are fetched at packaging time. Packaging checks the schema digest before use.
