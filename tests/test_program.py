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

import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pulumi import automation as auto
from pulumitest import PulumiProgram, opttest
from pulumitest.program import (
    EXCLUDED_NAMES,
    _copy_directory,
    _is_excluded_name,
    _safe_copy_filter,
)


def test_imports():
    """Verify all public exports are importable."""
    from pulumitest import (
        PulumiProgram,
        opttest,
    )

    assert PulumiProgram is not None
    assert opttest is not None


def _mock_local_workspace(monkeypatch):
    mock_workspace = MagicMock()
    monkeypatch.setattr(
        "pulumitest.program.auto.LocalWorkspace", MagicMock(return_value=mock_workspace)
    )
    return mock_workspace


def test_program_with_test_in_place_skip_install_skip_stack(monkeypatch, tmp_path):
    """PulumiProgram initializes without copying or creating stack."""
    _mock_local_workspace(monkeypatch)
    mock_create_stack = MagicMock()
    monkeypatch.setattr("pulumitest.program.auto.create_stack", mock_create_stack)

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
        opttest.temp_dir(str(tmp_path)),
    )

    assert program.working_dir == "test_stack"
    assert program.options.test_in_place is True
    assert program.options.skip_install is True
    assert program.options.skip_stack_create is True
    assert program.current_stack is None
    mock_create_stack.assert_not_called()


def test_program_creates_stack_with_env_vars(monkeypatch, tmp_path):
    """PulumiProgram creates a stack when not skipped and passes env vars through."""
    mock_workspace = _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    mock_create_stack = MagicMock(return_value=mock_stack)
    monkeypatch.setattr("pulumitest.program.auto.create_stack", mock_create_stack)

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
    )

    assert program.current_stack is mock_stack
    mock_create_stack.assert_called_once()
    args, kwargs = mock_create_stack.call_args
    assert args == ("test",)
    assert kwargs["work_dir"] == "test_stack"
    opts = kwargs["opts"]
    assert isinstance(opts, auto.LocalWorkspaceOptions)
    assert (
        opts.env_vars["PULUMI_CONFIG_PASSPHRASE"] == opttest.DEFAULT_CONFIG_PASSPHRASE
    )
    assert "PULUMI_BACKEND_URL" in opts.env_vars
    assert program.local_workspace is mock_workspace


def test_local_workspace_receives_env_vars(monkeypatch, tmp_path):
    mock_local_workspace_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        "pulumitest.program.auto.LocalWorkspace", mock_local_workspace_cls
    )
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=MagicMock())
    )

    PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
        opttest.env("FOO", "bar"),
    )

    _, kwargs = mock_local_workspace_cls.call_args
    assert kwargs["work_dir"] == "test_stack"
    assert kwargs["env_vars"]["FOO"] == "bar"
    assert (
        kwargs["env_vars"]["PULUMI_CONFIG_PASSPHRASE"]
        == opttest.DEFAULT_CONFIG_PASSPHRASE
    )


def test_program_custom_stack_name(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_create_stack = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("pulumitest.program.auto.create_stack", mock_create_stack)

    PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.stack_name("custom"),
        opttest.temp_dir(str(tmp_path)),
    )

    args, kwargs = mock_create_stack.call_args
    assert args == ("custom",)
    assert kwargs["work_dir"] == "test_stack"


def test_get_env_vars(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=MagicMock())
    )

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
        opttest.temp_dir(str(tmp_path)),
    )

    env_vars = program.get_env_vars()
    assert "PULUMI_CONFIG_PASSPHRASE" in env_vars
    assert env_vars["PULUMI_CONFIG_PASSPHRASE"] == opttest.DEFAULT_CONFIG_PASSPHRASE


def test_cleanup_no_stack(monkeypatch, tmp_path):
    """Cleanup is safe when no stack exists."""
    _mock_local_workspace(monkeypatch)

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.skip_stack_create(),
        opttest.temp_dir(str(tmp_path)),
    )

    program.cleanup()  # Should not raise


# --- Stack guard: create vs. select ---------------------------------------


def test_preexisting_stack_selected_and_not_destroyed(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack",
        MagicMock(side_effect=auto.StackAlreadyExistsError("test")),
    )
    monkeypatch.setattr(
        "pulumitest.program.auto.select_stack", MagicMock(return_value=mock_stack)
    )

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
    )

    assert program.current_stack is mock_stack
    assert program.stack_preexisted is True

    program.cleanup()
    mock_stack.destroy.assert_not_called()


def test_destroy_existing_stack_opts_in(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack",
        MagicMock(side_effect=auto.StackAlreadyExistsError("test")),
    )
    monkeypatch.setattr(
        "pulumitest.program.auto.select_stack", MagicMock(return_value=mock_stack)
    )

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
        opttest.destroy_existing_stack(),
    )

    assert program.stack_preexisted is True
    program.cleanup()
    mock_stack.destroy.assert_called_once_with(remove=True)


def test_other_create_errors_reraised(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack",
        MagicMock(side_effect=RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.temp_dir(str(tmp_path)),
        )


# --- Backend isolation ------------------------------------------------------


def test_default_file_backend_set_with_private_dir(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=MagicMock())
    )

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
    )

    env_vars = program.get_env_vars()
    assert env_vars["PULUMI_BACKEND_URL"].startswith("file://")
    backend_dir = Path(program._backend_dir)
    assert backend_dir.exists()
    assert stat.S_IMODE(backend_dir.stat().st_mode) == 0o700


def test_ambient_backend_leaves_backend_url_unset(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=MagicMock())
    )
    monkeypatch.delenv("PULUMI_BACKEND_URL", raising=False)

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
        opttest.use_ambient_backend(),
    )

    assert "PULUMI_BACKEND_URL" not in program.get_env_vars()
    assert program._backend_dir is None


def test_custom_backend_url_overrides_default(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=MagicMock())
    )

    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install(),
        opttest.temp_dir(str(tmp_path)),
        opttest.env("PULUMI_BACKEND_URL", "file:///tmp/custom-backend"),
    )

    assert program.get_env_vars()["PULUMI_BACKEND_URL"] == "file:///tmp/custom-backend"
    assert program._backend_dir is None


# --- Copy filtering ----------------------------------------------------------


def test_excluded_names():
    for name in EXCLUDED_NAMES:
        assert _is_excluded_name(name)
    assert _is_excluded_name(".env.local")
    assert _is_excluded_name(".env.production")
    assert not _is_excluded_name("main.py")


def test_exclusion_list_not_copied(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("keep me")
    (src / ".git").mkdir()
    (src / ".git" / "config").write_text("secret")
    (src / "node_modules").mkdir()
    (src / ".env").write_text("SECRET=1")
    (src / ".env.local").write_text("SECRET=2")
    (src / "__pycache__").mkdir()

    dest = tmp_path / "dest"
    _copy_directory(str(src), str(dest), _safe_copy_filter(str(src), [str(dest)]))

    assert (dest / "main.py").exists()
    assert not (dest / ".git").exists()
    assert not (dest / "node_modules").exists()
    assert not (dest / ".env").exists()
    assert not (dest / ".env.local").exists()
    assert not (dest / "__pycache__").exists()


def test_symlink_escape_skipped_and_inside_kept(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "real.txt").write_text("hello")
    (src / "inside_link").symlink_to(src / "real.txt")

    outside = tmp_path / "outside.txt"
    outside.write_text("nope")
    (src / "escape_link").symlink_to(outside)

    dest = tmp_path / "dest"
    _copy_directory(str(src), str(dest), _safe_copy_filter(str(src), [str(dest)]))

    assert (dest / "inside_link").is_symlink()
    assert (dest / "inside_link").read_text() == "hello"
    assert not (dest / "escape_link").exists()


def test_self_containing_temp_dir(tmp_path):
    """A program whose temp base lives inside the source directory must not
    recurse into (or copy) that temp base."""
    src = tmp_path / "program"
    src.mkdir()
    (src / "main.py").write_text("code")
    temp_base = src / "tmp"
    temp_base.mkdir()
    (temp_base / "leftover.txt").write_text("from a previous run")

    dest = tmp_path / "dest"
    _copy_directory(
        str(src), str(dest), _safe_copy_filter(str(src), [str(dest), str(temp_base)])
    )

    assert (dest / "main.py").exists()
    assert not (dest / "tmp").exists()


def test_directories_created_private(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "sub").mkdir()
    (src / "sub" / "file.txt").write_text("x")

    dest = tmp_path / "dest"
    _copy_directory(str(src), str(dest), _safe_copy_filter(str(src), [str(dest)]))

    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    assert stat.S_IMODE((dest / "sub").stat().st_mode) == 0o700


# --- Temp directory hygiene ---------------------------------------------------


def test_temp_dir_created_private_and_removed_on_cleanup(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=mock_stack)
    )

    monkeypatch.chdir(tmp_path)
    src = tmp_path / "program"
    src.mkdir()
    (src / "main.py").write_text("code")
    base = tmp_path / "tempbase"

    program = PulumiProgram("program", opttest.temp_dir(str(base)))

    owned = Path(program._owned_temp_dir)
    assert owned.exists()
    assert stat.S_IMODE(owned.stat().st_mode) == 0o700

    program.cleanup()
    assert not owned.exists()


def test_temp_dir_kept_on_failed_destroy(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    mock_stack.destroy.side_effect = RuntimeError("destroy failed")
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=mock_stack)
    )

    monkeypatch.chdir(tmp_path)
    src = tmp_path / "program"
    src.mkdir()
    (src / "main.py").write_text("code")

    program = PulumiProgram("program", opttest.temp_dir(str(tmp_path / "tempbase")))
    owned = Path(program._owned_temp_dir)

    program.cleanup()
    assert owned.exists()


def test_temp_dir_kept_when_keep_temp_dir_option(monkeypatch, tmp_path):
    _mock_local_workspace(monkeypatch)
    mock_stack = MagicMock()
    monkeypatch.setattr(
        "pulumitest.program.auto.create_stack", MagicMock(return_value=mock_stack)
    )

    monkeypatch.chdir(tmp_path)
    src = tmp_path / "program"
    src.mkdir()
    (src / "main.py").write_text("code")

    program = PulumiProgram(
        "program",
        opttest.temp_dir(str(tmp_path / "tempbase")),
        opttest.keep_temp_dir(),
    )
    owned = Path(program._owned_temp_dir)

    program.cleanup()
    assert owned.exists()
