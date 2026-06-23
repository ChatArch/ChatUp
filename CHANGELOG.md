# Changelog

## 0.2.0

### Added
- Migrate ChatTool setup commands into ChatUp, including workspace setup helpers and package assets.
- Add workspace fallback behavior so ChatBlog without `source/_posts` can temporarily link documentation through `public` instead of failing setup.

### Changed
- Require the published shared config runtime `chatenv>=0.2.0,<0.3.0` and bounded ChatArch CLI runtime `chatstyle>=0.1.0,<0.2.0`.
- Use ChatEnv `0.2.x` shared OpenAI/Feishu configs directly from setup modules; ChatUp no longer ships a `chatup.config` package, copied schema definitions, or another `chatenv.configs` provider.
- Remove the legacy hand-written OpenCode ChatLoop plugin/assets from ChatUp; `setup opencode --plugin` now keeps only supported presets such as `auto-loop`, because RuffleLoop covers the loop use case.

## 0.1.0

### Added
- Add the initial `chatup` CLI entrypoint with `--help`, `--version`, and `doctor` smoke command.
- Add tag-driven PyPI publish workflow using Trusted Publishing/OIDC.
- Document the ChatUp setup-split role and release requirements.

## 0.0.1

### Added
- Initial placeholder package release for the `chatup` name.
