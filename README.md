# Pulumitest Python

A Python port of [pulumitest](https://github.com/pulumi/pulumitest) (Go) for testing Pulumi programs using the Automation API. Framework-agnostic: works with pytest, unittest, or standalone.

## Installation

```bash
uv add pulumitest
```

Or from source:

```bash
uv add 'pulumitest @ git+https://github.com/pulumi-labs/pulumitest-python.git@main'
```

## Quick Start

### Pytest

```python
from pulumitest import PulumiProgram, opttest

def test_deployment(request):
    program = PulumiProgram("my-pulumi-project")
    request.addfinalizer(program.cleanup)

    program.add_environments("aws/pulumi-ce")
    result = program.up()
    assert "bucket_name" in result.outputs

    preview = program.preview()
    preview.has_no_changes()
```

### Unittest

```python
from pulumitest import PulumiProgram
import unittest

class TestStack(unittest.TestCase):
    def test_deployment(self):
        program = PulumiProgram("my-pulumi-project")
        self.addCleanup(program.cleanup)

        program.add_environments("aws/pulumi-ce")
        program.up()
```

### Standalone

```python
from pulumitest import PulumiProgram

program = PulumiProgram("my-pulumi-project")
try:
    result = program.up()
    print(f"Outputs: {result.outputs}")
finally:
    program.cleanup()
```

## Configuration Options

```python
program = PulumiProgram(
    "my-pulumi-project",
    opttest.test_in_place(),        # Don't copy to temp directory
    opttest.skip_install(),         # Skip pulumi install
    opttest.stack_name("dev"),      # Custom stack name
    opttest.config_passphrase("x"), # Set config passphrase
)
```

| Option | Description |
|--------|-------------|
| `test_in_place()` | Run from source directory (no copy) |
| `skip_install()` | Skip `pulumi install` |
| `skip_stack_create()` | Skip stack creation (must exist) |
| `stack_name(name)` | Set custom stack name |
| `config_passphrase(p)` | Set config passphrase |
| `temp_dir(path)` | Set custom temp directory |
| `use_ambient_backend()` | Use existing `pulumi login` backend instead of a private one |
| `env(key, value)` | Set custom environment variable |
| `destroy_existing_stack()` | Let `cleanup()` destroy a stack that existed before the run |
| `keep_temp_dir()` | Leave the temporary copy on disk after `cleanup()` |

The temp directory defaults to `./tmp` under the current working directory, or `$PULUMITEST_TEMP_DIR` when set. Temp directories are created readable only by the current user and are deleted by `cleanup()`.

### Isolation defaults

- **Backend.** Each program gets a private local file backend under its temp directory, so test stacks never reach the backend `pulumi login` points at. Pass `use_ambient_backend()` when a test needs Pulumi Cloud, for example to attach ESC environments, or set `env("PULUMI_BACKEND_URL", ...)` explicitly.
- **Pre-existing stacks.** If the stack name already exists, it is selected rather than created and `program.stack_preexisted` is `True`. `cleanup()` will not destroy it unless `destroy_existing_stack()` was given. This matters with `test_in_place()`, where the default stack name `test` may collide with a real stack in the project directory.
- **Copied files.** `.git`, `.env` and `.env.*`, `node_modules`, `bin`, `obj`, `__pycache__`, `.venv`, `venv`, and `.terraform` are never copied, and symlinks that point outside the program directory are skipped.
- **Passphrase.** The default config passphrase is the fixed, publicly known string `correct horse battery staple` (`opttest.DEFAULT_CONFIG_PASSPHRASE`). Secrets in a test stack's config are not protected by it. Pass `config_passphrase()` with a real value if that matters.
- **`get_env_vars()`** returns the passphrase and anything passed via `env()`. Do not log it.

Environment variables from `env()` are passed to the Automation API workspace and take precedence over the defaults, so `env("PULUMI_BACKEND_URL", "file:///tmp/backend")` runs the stack against a local file backend instead of the private per-run one.

## Result Assertions

```python
result = program.up()
result.has_no_changes()
result.has_no_deletes()
result.has_no_replacements()

preview = program.preview()
preview.has_no_changes()

refresh = program.refresh()
refresh.has_no_changes()
```

All assertion methods raise `AssertionError` on failure, which works with both pytest and unittest.

## Result Properties

```python
# UpdateResult
result = program.up()
result.outputs          # Stack outputs
result.summary          # UpdateSummary
result.change_summary   # OpType -> count mapping

# PreviewResult
preview = program.preview()
preview.change_summary  # OpType -> count mapping

# RefreshResult
refresh = program.refresh()
refresh.summary         # UpdateSummary
refresh.change_summary  # OpType -> count mapping
```

## Advanced Usage

### Update Source (Drift Testing)

Swap program files while maintaining the same stack:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

program.up()
program.update_source("path/to/modified")
preview = program.preview()
# preview will show changes
```

### Copy to Temp Directory

```python
program = PulumiProgram("example", opttest.test_in_place())
copy = program.copy_to_temp_dir()
request.addfinalizer(copy.cleanup)
copy.up()
```

### Access Pulumi Automation API

```python
program = PulumiProgram("example")
stack = program.current_stack       # auto.Stack
workspace = program.local_workspace # auto.LocalWorkspace
```

## Cleanup

`cleanup()` destroys the stack, removes it, and deletes the temporary copy of the program. A stack that existed before the run is left in place unless `destroy_existing_stack()` was given. The temporary directory is kept when the destroy fails so state can be inspected, or when `keep_temp_dir()` was given. A failed destroy is logged but does not raise, so teardown never masks the test result:

```python
request.addfinalizer(program.cleanup)
```

## Development

```bash
git clone https://github.com/pulumi-labs/pulumitest-python.git
cd pulumitest-python
uv sync --dev
just test    # run tests
just lint    # run linter
```

## License

Apache 2.0
