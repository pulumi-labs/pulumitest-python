"""Integration tests for pytest fixtures.

Tests the pytest-native fixture API to ensure fixtures work correctly
with real Pulumi programs.
"""

import pytest
from pulumitest import opttest
from pulumitest.core import PulumiTest


# Test pulumi_test fixture (manual deployment)
@pytest.mark.pulumi_program_dir("test_stack")
def test_pulumi_test_fixture_manual_deployment(pulumi_test):
    """Test pulumi_test fixture with manual deployment control."""
    assert pulumi_test is not None
    assert isinstance(pulumi_test, PulumiTest)
    assert pulumi_test.working_dir.endswith("test_stack") or "programDir_" in pulumi_test.working_dir

    # Verify we can access environment variables
    env_vars = pulumi_test.get_env_vars()
    assert "PULUMI_CONFIG_PASSPHRASE" in env_vars
    assert "PULUMI_BACKEND_URL" in env_vars


@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_opts(opttest.test_in_place(), opttest.skip_install(), opttest.skip_stack_create())
def test_pulumi_test_with_options(pulumi_test):
    """Test pulumi_test fixture with custom options."""
    assert pulumi_test.working_dir == "test_stack"
    assert pulumi_test.options.test_in_place is True
    assert pulumi_test.options.skip_install is True


# Test pulumi_stack fixture (auto deployment)
@pytest.mark.pulumi_program_dir("test_stack")
def test_pulumi_stack_auto_deploy(pulumi_stack):
    """Test pulumi_stack fixture with automatic deployment."""
    # Stack should already be deployed
    outputs = pulumi_stack.current_stack.outputs()
    assert outputs is not None

    # Preview should show no changes (already deployed)
    preview = pulumi_stack.preview()
    preview.has_no_changes()

    # Stack will be automatically destroyed after test


@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_skip_deploy
def test_pulumi_stack_skip_deploy(pulumi_stack):
    """Test pulumi_stack fixture with skip_deploy marker."""
    # Stack created but not deployed
    # We can still manually deploy
    result = pulumi_stack.up()
    assert result is not None


# Test pulumi_program fixture (semantic alias)
@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_opts(opttest.test_in_place(), opttest.skip_install(), opttest.skip_stack_create())
def test_pulumi_program_fixture(pulumi_program):
    """Test pulumi_program fixture."""
    assert pulumi_program is not None
    assert pulumi_program.working_dir == "test_stack"


# Test pulumi_test_factory fixture
def test_pulumi_test_factory_creates_instances(pulumi_test_factory):
    """Test pulumi_test_factory creates multiple instances."""
    # Create first test instance
    test1 = pulumi_test_factory(
        "test_stack",
        [opttest.test_in_place(), opttest.skip_install(), opttest.skip_stack_create()]
    )
    assert test1 is not None
    assert test1.working_dir == "test_stack"

    # Create second test instance with different options
    test2 = pulumi_test_factory(
        "test_stack",
        [opttest.skip_install(), opttest.skip_stack_create()]
    )
    assert test2 is not None
    # test2 should be in a temp directory (not test_in_place)
    assert "programDir_" in test2.working_dir or test2.working_dir.endswith("test_stack")


# Test fixture with add_environments
@pytest.mark.pulumi_program_dir("test_stack")
def test_fixture_with_environments(pulumi_stack):
    """Test adding environments to stack via fixture."""
    pulumi_stack.add_environments("aws/pulumi-ce")

    # Stack should be deployed with environment
    outputs = pulumi_stack.current_stack.outputs()
    assert outputs is not None


# Test fixture with copy operations
@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_opts(opttest.test_in_place(), opttest.skip_install(), opttest.skip_stack_create())
def test_fixture_copy_operations(pulumi_test):
    """Test copy operations with fixture."""
    # Original test in place
    assert pulumi_test.working_dir == "test_stack"

    # Copy to temp dir
    copied = pulumi_test.copy_to_temp_dir()
    assert copied is not None
    assert copied.working_dir != pulumi_test.working_dir
    assert "programDir_" in copied.working_dir


# Test fixture error handling
def test_fixture_without_marker_fails(request):
    """Test that using fixture without marker fails properly."""
    # This test doesn't have @pytest.mark.pulumi_program_dir
    # We're testing that the error handling works
    from pulumitest.pytest_plugin import _get_program_dir

    with pytest.raises(pytest.fail.Exception):
        _get_program_dir(request)


# Test pulumi_options fixture
def test_pulumi_options_fixture(pulumi_options):
    """Test pulumi_options fixture provides default options."""
    assert pulumi_options is not None
    assert pulumi_options.stack_name == "test"
    assert pulumi_options.config_passphrase == "correct horse battery staple"

    # Options should be mutable
    pulumi_options.config_passphrase = "custom-passphrase"
    assert pulumi_options.config_passphrase == "custom-passphrase"


# Test pulumi_backend fixture
def test_pulumi_backend_fixture(pulumi_backend):
    """Test pulumi_backend fixture provides backend config."""
    assert pulumi_backend is not None
    assert isinstance(pulumi_backend, dict)
    assert "PULUMI_BACKEND_URL" in pulumi_backend
    assert "PULUMI_CONFIG_PASSPHRASE" in pulumi_backend


# Test workspace and stack access via fixture
@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_opts(opttest.skip_install())
def test_fixture_workspace_access(pulumi_test):
    """Test accessing workspace and stack via fixture."""
    # Test workspace property
    workspace = pulumi_test.local_workspace
    assert workspace is not None

    # Test stack property
    stack = pulumi_test.current_stack
    assert stack is not None
    assert stack.name == "test"


# Test fixture with update_source
@pytest.mark.pulumi_program_dir("test_stack")
def test_fixture_update_source(pulumi_stack):
    """Test update_source operation via fixture."""
    # Stack already deployed via fixture
    outputs_before = pulumi_stack.current_stack.outputs()

    # Update source (same directory for test)
    pulumi_stack.update_source("test_stack")

    # Stack should still exist
    outputs_after = pulumi_stack.current_stack.outputs()
    assert outputs_after is not None


# Parameterized test with fixture
@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.parametrize("test_option", [
    opttest.test_in_place(),
    opttest.skip_install(),
])
def test_fixture_with_parametrize(pulumi_test, test_option):
    """Test that fixtures work with pytest.mark.parametrize."""
    # Note: test_option is from parametrize, not applied to fixture
    # This test verifies fixtures work in parametrized tests
    assert pulumi_test is not None
    assert isinstance(pulumi_test, PulumiTest)


# Test multiple operations with pulumi_stack
@pytest.mark.pulumi_program_dir("test_stack")
def test_multiple_operations_with_fixture(pulumi_stack):
    """Test multiple Pulumi operations with fixture."""
    # Stack already deployed

    # Preview should show no changes
    preview = pulumi_stack.preview()
    preview.has_no_changes()

    # Refresh should show no changes
    refresh = pulumi_stack.refresh()
    refresh.has_no_changes()

    # Verify outputs
    outputs = pulumi_stack.current_stack.outputs()
    assert outputs is not None


# Test fixture cleanup behavior
@pytest.mark.pulumi_program_dir("test_stack")
@pytest.mark.pulumi_opts(opttest.skip_install())
def test_fixture_cleanup_registered(pulumi_test):
    """Test that cleanup is properly registered via fixture."""
    # Cleanup registration is automatic via PyTestContext
    # This test verifies the fixture works without errors
    assert pulumi_test is not None
    # Cleanup will happen automatically after test completes
