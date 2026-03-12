# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
