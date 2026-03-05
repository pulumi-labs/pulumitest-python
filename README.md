# Pulumitest Python

Python testing utilities for Pulumi programs. Works with pytest, unittest, or standalone.

## Installation

```bash
pip install pulumitest
```

Or from source:

```bash
pip install 'pulumitest @ git+https://github.com/pulumi/pulumitest-python.git@main'
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
| `use_ambient_backend()` | Use existing `pulumi login` backend |
| `env(key, value)` | Set custom environment variable |

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

## Development

```bash
git clone https://github.com/pulumi/pulumitest-python.git
cd pulumitest-python
pip install -e ".[dev]"
pytest tests/
```

## License

Apache 2.0
