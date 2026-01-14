# Pulumitest Python

Python testing framework for Pulumi integration tests. This is the Python equivalent of the Go [pulumitest](https://github.com/pulumi/providertest) framework.

## Features

- **Full lifecycle testing** of Pulumi programs
- **Provider-agnostic drift creation** via state export/import
- **Automated stack management** with cleanup
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

```python
from pulumitest import PulumiTestProgram, opttest
import unittest

class TestS3Stack(unittest.TestCase):
    def test_deployment(self):
        test = PulumiTestProgram(self, "my-pulumi-project")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack
        result = test.up()

        # Verify no drift
        preview = test.preview()
        preview.has_no_changes()

        refresh = test.refresh()
        refresh.has_no_changes()
```

## Key Features

### Update Source

Swap program files while maintaining the same stack and state:

```python
test = PulumiTestProgram(self, "example").copy_to_temp_dir()

# Deploy original
test.update_source("path/to/original")
test.up()

# Switch to drifted code
test.update_source("path/to/drifted")
test.up()

# Switch back to original
test.update_source("path/to/original")
```

### Stack Export/Import

Create drift using native Automation API:

```python
# Export current state
saved_state = test.current_stack.export_stack()

# Deploy changes
test.update_source("path/to/drifted")
test.up()

# Import original state (creates drift!)
test.current_stack.import_stack(saved_state)
```

### Environment Variables

Get environment for coordination with external tools:

```python
env_vars = test.get_env_vars()
backend_url = env_vars["PULUMI_BACKEND_URL"]
passphrase = env_vars["PULUMI_CONFIG_PASSPHRASE"]
```

### Convenience Properties

Direct access to results:

```python
# Update results
result = test.up()
outputs = result.outputs
summary = result.summary
changes = result.change_summary

# Preview results
preview = test.preview()
changes = preview.change_summary
update_count = changes.get(OpType.UPDATE, 0)
```

## Testing Drift

See `test_drift_adoption.py` for comprehensive examples of drift testing workflows.

## License

Apache 2.0
