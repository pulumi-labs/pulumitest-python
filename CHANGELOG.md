# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- `cleanup()` no longer destroys a stack that existed before the run. Such a stack is selected, `stack_preexisted` is set, and destroy is skipped unless `opttest.destroy_existing_stack()` is given
- Each program now uses a private local file backend by default; `opttest.use_ambient_backend()` opts into the `pulumi login` backend as the option always documented
- The temporary copy of the program excludes `.git`, `.env*`, `node_modules`, `bin`, `obj`, `__pycache__`, `.venv`, `venv`, and `.terraform`, skips symlinks that escape the program directory, is created with mode `0700`, and is deleted by `cleanup()` (`opttest.keep_temp_dir()` keeps it)
- Environment variables built for the Automation API workspace (config passphrase, backend URL, `env()` overrides) are now actually passed to `LocalWorkspace` and stack creation/selection; previously they were computed and discarded
- Documented that the default config passphrase is public and that `get_env_vars()` returns secrets
- Added `SECURITY.md` and Dependabot configuration
- Removed `poetry.lock` files (superseded by `uv.lock`); `pulumitest/poetry.lock` previously shipped inside the wheel

## [0.1.0] - 2026-03-12

### Added

- `PulumiProgram` API for testing Pulumi programs using the Automation API
- Framework-agnostic design: works with pytest, unittest, or standalone scripts
- Configuration options via `opttest` module (`test_in_place`, `skip_install`, `stack_name`, `config_passphrase`, etc.)
- Result assertion methods: `has_no_changes`, `has_no_deletes`, `has_no_replacements`
- Result types: `UpdateResult`, `PreviewResult`, `RefreshResult` with access to outputs, summaries, and change summaries
- `update_source` for drift testing (swap program files while maintaining the same stack)
- `copy_to_temp_dir` for isolated test copies
- Direct access to Pulumi Automation API via `current_stack` and `local_workspace` properties
- CI pipeline with lint and test matrix (Python 3.10-3.12)
- Tag-triggered release pipeline with PyPI trusted publishing
