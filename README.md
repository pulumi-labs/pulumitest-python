# Pulumitest Python

Python testing framework for Pulumi integration tests. This is the Python equivalent of the Go [pulumitest](https://github.com/pulumi/providertest) framework.

## Features

- **Framework-independent API** - Use with pytest, unittest, or standalone
- **Full lifecycle testing** of Pulumi programs
- **Provider-agnostic drift creation** via state export/import
- **Automated stack management** with cleanup callbacks
- **Assertion helpers** for validating operation results
- **Flexible test configuration** through options
- **Temporary directory management** to avoid polluting source directories

## Installation

```bash
pip install pulumitest
```

Or for development:

```bash
uv add 'pulumitest @ git+https://github.com/pulumi/pulumitest-python.git@main'
```

## Quick Start

### Framework-Independent API (Recommended)

The most flexible approach - works with any test framework or standalone:

#### With Pytest

```python
from pulumitest import PulumiProgram, opttest

def test_deployment(request):
    """Test with pytest - no framework coupling."""
    # Create program
    program = PulumiProgram("my-pulumi-project")

    # Register cleanup with pytest
    request.addfinalizer(program.cleanup)

    # Add cloud credentials
    program.add_environments("aws/pulumi-ce")

    # Deploy and test
    result = program.up()
    assert "bucket_name" in result.outputs

    # Verify no drift
    preview = program.preview()
    preview.has_no_changes()
```

#### With Unittest

```python
from pulumitest import PulumiProgram
import unittest

class TestStack(unittest.TestCase):
    def test_deployment(self):
        # Create program
        program = PulumiProgram("my-pulumi-project")

        # Register cleanup with unittest
        self.addCleanup(program.cleanup)

        # Deploy and test
        program.add_environments("aws/pulumi-ce")
        program.up()
```

#### Standalone Usage

```python
from pulumitest import PulumiProgram

program = PulumiProgram("my-pulumi-project")
try:
    program.add_environments("aws/pulumi-ce")
    result = program.up()
    print(f"Deployed! Outputs: {result.outputs}")
finally:
    program.cleanup()
```

### Pytest Fixtures API

For pytest-native integration with automatic cleanup:

```python
import pytest
from pulumitest import opttest

@pytest.mark.pulumi_program_dir("my-pulumi-project")
def test_deployment(pulumi_stack):
    """Test with automatic deployment and cleanup."""
    # Stack already deployed
    outputs = pulumi_stack.current_stack.outputs()
    assert "bucket_name" in outputs

    # Verify no drift
    preview = pulumi_stack.preview()
    preview.has_no_changes()

    # Stack automatically destroyed after test
```

### Unittest Compatibility API

For existing unittest-based tests (backward compatible):

```python
from pulumitest import PulumiTestProgram
import unittest

class TestStack(unittest.TestCase):
    def test_deployment(self):
        test = PulumiTestProgram(self, "my-pulumi-project")
        test.add_environments("aws/pulumi-ce")
        test.up()
```

## API Comparison

| Feature | PulumiProgram | Pytest Fixtures | PulumiTestProgram |
|---------|---------------|-----------------|-------------------|
| Framework coupling | None | Pytest only | Unittest only |
| Cleanup control | Manual registration | Automatic | Automatic |
| Use in pytest | ✅ `request.addfinalizer` | ✅ Native fixtures | ❌ |
| Use in unittest | ✅ `self.addCleanup` | ❌ | ✅ Native |
| Use standalone | ✅ Try/finally | ❌ | ❌ |
| Best for | Flexibility, integration | New pytest tests | Legacy unittest |

**Recommendation:** Use `PulumiProgram` for maximum flexibility and to integrate with existing test suites.

## Configuration Options

All APIs support the same configuration options:

```python
from pulumitest import PulumiProgram, opttest

program = PulumiProgram(
    "my-pulumi-project",
    opttest.test_in_place(),        # Don't copy to temp directory
    opttest.skip_install(),         # Skip pulumi install
    opttest.stack_name("dev"),      # Custom stack name
)
request.addfinalizer(program.cleanup)
```

### Available Options

- `test_in_place()` - Run from source directory (no copy)
- `skip_install()` - Skip `pulumi install` command
- `skip_stack_create()` - Skip stack creation (must exist)
- `stack_name(name)` - Set custom stack name
- `config_passphrase(pass)` - Set config passphrase
- `temp_dir(path)` - Set custom temp directory location

## Key Features

### Update Source

Swap program files while maintaining the same stack and state:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

# Copy to temp directory
temp_program = program.copy_to_temp_dir()

# Deploy original
temp_program.update_source("path/to/original")
temp_program.up()

# Switch to drifted code
temp_program.update_source("path/to/drifted")
temp_program.up()

# Switch back to original (drift now visible!)
temp_program.update_source("path/to/original")
preview = temp_program.preview()
# preview.has_changes() == True
```

### Stack Export/Import for Drift Testing

Create drift using native Automation API:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

# Deploy initial state
program.up()

# Export current state
saved_state = program.current_stack.export_stack()

# Deploy changes
program.update_source("path/to/drifted")
program.up()

# Import original state (creates drift!)
program.current_stack.import_stack(saved_state)

# Now verify drift detection
program.update_source("path/to/original")
refresh = program.refresh()
assert refresh.has_changes()
```

### Environment Variables

Get environment for coordination with external tools:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

# Get environment variables
env_vars = program.get_env_vars()
backend_url = env_vars["PULUMI_BACKEND_URL"]
passphrase = env_vars["PULUMI_CONFIG_PASSPHRASE"]

# Use with external Pulumi CLI
import subprocess
subprocess.run(
    ["pulumi", "stack", "output"],
    cwd=program.working_dir,
    env={**os.environ, **env_vars}
)
```

### Result Properties

Direct access to operation results:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

# Update results
result = program.up()
outputs = result.outputs
summary = result.summary
changes = result.change_summary

# Preview results
preview = program.preview()
changes = preview.change_summary
update_count = changes.get(OpType.UPDATE, 0)

# Assertions
preview.has_no_changes()
preview.has_changes()
```

### Access Pulumi Automation API

Direct access to underlying Pulumi objects:

```python
program = PulumiProgram("example")
request.addfinalizer(program.cleanup)

# Access stack
stack = program.current_stack
stack_name = stack.name
outputs = stack.outputs()

# Access workspace
workspace = program.local_workspace
work_dir = workspace.work_dir
```

## Advanced Examples

### Multiple Stacks

```python
def test_multi_stack(request):
    # Create backend stack
    backend = PulumiProgram("backend")
    request.addfinalizer(backend.cleanup)

    # Create frontend stack
    frontend = PulumiProgram("frontend")
    request.addfinalizer(frontend.cleanup)

    # Deploy both
    backend_result = backend.up()
    frontend_result = frontend.up()

    # Test integration
    api_url = backend_result.outputs["api_url"]
    frontend_api = frontend_result.outputs["api_endpoint"]
    assert frontend_api.startswith(api_url)
```

### Custom Logger

```python
import logging

def test_with_custom_logger(request):
    logger = logging.getLogger("my_test")
    logger.setLevel(logging.INFO)

    program = PulumiProgram("example", logger=logger)
    request.addfinalizer(program.cleanup)

    program.up()  # Logs go to custom logger
```

### Pytest Factory Pattern

```python
@pytest.fixture
def pulumi_factory(request):
    """Factory fixture for creating multiple programs."""
    programs = []

    def create(working_dir, *opts):
        program = PulumiProgram(working_dir, *opts)
        programs.append(program)
        return program

    yield create

    # Cleanup all programs
    for program in programs:
        program.cleanup()

def test_with_factory(pulumi_factory):
    program1 = pulumi_factory("stack1")
    program2 = pulumi_factory("stack2")

    program1.up()
    program2.up()
```

## Testing Drift

The framework provides powerful tools for drift testing:

1. **Update Source** - Swap code while maintaining stack
2. **Export/Import** - Manipulate state directly
3. **Refresh Detection** - Verify drift is detected
4. **Preview Validation** - Check expected changes

See `examples/using_pulumi_program.py` and `test_drift_adoption.py` for comprehensive drift testing workflows.

## Integration with Existing Test Suites

`PulumiProgram` is designed to integrate seamlessly into existing test suites:

```python
# In your existing pytest test file
from pulumitest import PulumiProgram

def test_your_feature(request):
    # Your existing test setup
    setup_test_environment()

    # Add Pulumi infrastructure
    program = PulumiProgram("test_stack")
    request.addfinalizer(program.cleanup)

    program.add_environments("aws/pulumi-ce")
    program.up()

    # Your existing test code
    run_your_tests()

    # Cleanup automatic via finalizer
```

## Examples

Comprehensive examples are available in the `examples/` directory:

- `examples/using_pulumi_program.py` - Framework-independent API examples
  - Pytest integration
  - Unittest integration
  - Standalone usage
  - Multiple stacks
  - Drift detection
  - Custom logger
  - Factory patterns

## Documentation

- **API Reference**: See docstrings in source code
- **Type Hints**: Full mypy --strict compliance
- **Examples**: Extensive examples in `examples/` directory

## Development

```bash
# Clone repository
git clone https://github.com/pulumi/pulumitest-python.git
cd pulumitest-python

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Run tests
pytest tests/

# Type checking
mypy pulumitest/ --strict
```

## License

Apache 2.0
