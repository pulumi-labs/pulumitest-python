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

import pytest

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
    mock_auto.create_or_select_stack.assert_called_once_with(
        "test",
        work_dir="test_stack",
    )


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

    mock_auto.create_or_select_stack.assert_called_once_with(
        "custom",
        work_dir="test_stack",
    )


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


def _program_with_failing_destroy(mock_auto):
    """A program whose stack raises on destroy."""
    mock_auto.LocalWorkspace.return_value = MagicMock()

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
    )

    stack = MagicMock()
    stack.name = "some-stack"
    stack.destroy.side_effect = RuntimeError("destroy failed: resource still in use")
    program.current_stack = stack
    return program, stack


@patch("pulumitest.program.auto")
def test_cleanup_swallows_destroy_error_by_default(mock_auto):
    """A failed destroy is logged, not raised, preserving existing behaviour."""
    program, stack = _program_with_failing_destroy(mock_auto)

    program.cleanup()  # Should not raise

    stack.destroy.assert_called_once_with(remove=True)


@patch("pulumitest.program.auto")
def test_cleanup_raises_destroy_error_when_requested(mock_auto):
    """raise_on_error surfaces the failure so leaked resources aren't silent."""
    program, stack = _program_with_failing_destroy(mock_auto)

    with pytest.raises(RuntimeError, match="destroy failed"):
        program.cleanup(raise_on_error=True)

    stack.destroy.assert_called_once_with(remove=True)


@patch("pulumitest.program.auto")
def test_cleanup_no_stack_does_not_raise_even_when_strict(mock_auto):
    """Nothing to destroy is not an error, regardless of raise_on_error."""
    mock_auto.LocalWorkspace.return_value = MagicMock()

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
    )

    program.cleanup(raise_on_error=True)  # Should not raise
