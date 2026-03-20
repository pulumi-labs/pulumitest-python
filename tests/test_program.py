# Copyright 2026, Pulumi Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test PulumiProgram construction (no cloud credentials needed)."""

from unittest.mock import patch, MagicMock
from pulumitest import PulumiProgram, opttest


def test_imports():
    """Verify all public exports are importable."""
    from pulumitest import (
        PulumiProgram,
        opttest,
    )

    assert PulumiProgram is not None
    assert opttest is not None


@patch("pulumitest.program.auto")
def test_program_with_test_in_place_skip_install_skip_stack(mock_auto):
    """PulumiProgram initializes without copying or creating stack."""
    mock_workspace = MagicMock()
    mock_auto.LocalWorkspace.return_value = mock_workspace

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
    )

    assert program.working_dir == "test_stack"
    assert program.options.test_in_place is True
    assert program.options.skip_install is True
    assert program.options.skip_stack_create is True
    assert program.current_stack is None
    mock_workspace.install.assert_not_called()
    mock_auto.create_or_select_stack.assert_not_called()


@patch("pulumitest.program.auto")
def test_program_creates_stack(mock_auto):
    """PulumiProgram creates stack when not skipped."""
    mock_workspace = MagicMock()
    mock_auto.LocalWorkspace.return_value = mock_workspace
    mock_stack = MagicMock()
    mock_auto.create_or_select_stack.return_value = mock_stack

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
    )

    assert program.current_stack is mock_stack
    call_args = mock_auto.create_or_select_stack.call_args
    assert call_args[0] == ("test",)
    assert call_args[1]["work_dir"] == "test_stack"


@patch("pulumitest.program.auto")
def test_program_custom_stack_name(mock_auto):
    mock_auto.LocalWorkspace.return_value = MagicMock()
    mock_auto.create_or_select_stack.return_value = MagicMock()

    PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.stack_name("custom"),
    )

    call_args = mock_auto.create_or_select_stack.call_args
    assert call_args[0] == ("custom",)
    assert call_args[1]["work_dir"] == "test_stack"


@patch("pulumitest.program.auto")
def test_get_env_vars(mock_auto):
    mock_auto.LocalWorkspace.return_value = MagicMock()

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
    )

    env_vars = program.get_env_vars()
    assert "PULUMI_CONFIG_PASSPHRASE" in env_vars
    assert env_vars["PULUMI_CONFIG_PASSPHRASE"] == "correct horse battery staple"


@patch("pulumitest.program.auto")
def test_custom_env_vars_applied(mock_auto):
    """Custom env vars from env() option are merged into _env_vars and passed to workspace."""
    mock_auto.LocalWorkspace.return_value = MagicMock()
    mock_auto.create_or_select_stack.return_value = MagicMock()

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.env("PULUMI_BACKEND_URL", "file:///tmp/test-backend"),
        opttest.env("MY_CUSTOM_VAR", "hello"),
    )

    env_vars = program.get_env_vars()
    assert env_vars["PULUMI_BACKEND_URL"] == "file:///tmp/test-backend"
    assert env_vars["MY_CUSTOM_VAR"] == "hello"

    # Verify env vars were passed to LocalWorkspace
    ws_call = mock_auto.LocalWorkspace.call_args
    ws_env = ws_call[1]["env_vars"]
    assert ws_env["PULUMI_BACKEND_URL"] == "file:///tmp/test-backend"
    assert ws_env["MY_CUSTOM_VAR"] == "hello"

    # Verify opts were passed to create_or_select_stack
    stack_call = mock_auto.create_or_select_stack.call_args
    assert "opts" in stack_call[1]
    # Verify LocalWorkspaceOptions was constructed with env_vars
    opts_call = mock_auto.LocalWorkspaceOptions.call_args
    assert opts_call[1]["env_vars"]["PULUMI_BACKEND_URL"] == "file:///tmp/test-backend"


@patch("pulumitest.program.auto")
def test_cleanup_no_stack(mock_auto):
    """Cleanup is safe when no stack exists."""
    mock_auto.LocalWorkspace.return_value = MagicMock()

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
    )

    program.cleanup()  # Should not raise
