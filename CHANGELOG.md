# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `util/version.py`: New utility module to retrieve the package version via `importlib.metadata` with a fallback to `pyproject.toml`
- First test suite, covering `tui/theme_loader.py`, together with the pytest, coverage and dev-dependency setup the project was missing

### Changed

- `CustomBindings`: Global bindings are no longer prefixed with `*`
- Updated colors of Textual themes `compact-gray` and `mnml-deepblack`
- `ThemeLoader`: A theme is now identified by the `name` in its `theme.py` plus its registration prefix. The directory name is no longer used as a key, so it may differ freely, and a standard and a custom theme may share a name
- `ThemeLoader`: Theme modules are imported by file path instead of through `sys.path`, so loading no longer alters the interpreter's import state
- `ThemeData`: Now frozen, and its redundant `name` field was removed

### Fixed

- `ThemeLoader`: The theme registry was held in class attributes shared by every instance, and registration re-prefixed the same `Theme` objects each time. A second application in one process saw `CUSTOM_CUSTOM_<name>`, a third `CUSTOM_CUSTOM_CUSTOM_<name>`. State is now per instance and the prefix is applied once, to a copy
- `ThemeLoader`: A theme folder whose name differed from the `name` in its `theme.py` registered but silently lost its stylesheet
- `ThemeLoader`: From the second loader in a process on, the bundled themes were not found at all, because a consumer's theme folder shadowed them under the shared package name `themes`. The bug was masked by the shared registry described above
- `ThemeLoader`: Switching themes never removed the stylesheet of a theme outside termz's own theme folder, so a consumer's CSS stayed applied on top of every theme it switched to
- `ThemeLoader`: A theme without a stylesheet, and any theme not registered by termz such as Textual's built-ins, logged a warning during entirely normal use. This is reported at debug level now
- `ThemeLoader`: Diagnostics went to the root logger and surfaced as `WARNING:root:` in every consumer; they now use a module logger and lazy formatting
- `ThemeLoader`: Two theme folders declaring the same name silently overwrote each other; the second is now refused with an error

## [0.1.1] – 2026-04-07

- Initial Release

## [0.1.0] – 2026-03-25

*PyPI name reservation – no functional code.*

[Unreleased]: https://github.com/cgroening/py-termz/compare/v0.1.1...HEAD [0.1.1]: https://github.com/cgroening/py-termz/compare/v0.1.0...v0.1.1 [0.1.0]: https://github.com/cgroening/py-termz/releases/tag/v0.1.0
