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

"""Framework-independent Pulumi program wrapper.

PulumiProgram wraps the Pulumi Automation API with ZERO test framework
dependencies. It can be used with pytest, unittest, or standalone.

Example usage in pytest:
    def test_my_stack(request):
        program = PulumiProgram("test_stack")
        request.addfinalizer(program.cleanup)
        result = program.up()
        assert "bucket_name" in result.outputs

Example usage in unittest:
    class TestStack(unittest.TestCase):
        def test_deployment(self):
            program = PulumiProgram("test_stack")
            self.addCleanup(program.cleanup)
            program.up()

Example usage standalone:
    program = PulumiProgram("test_stack")
    try:
        program.up()
    finally:
        program.cleanup()
"""

import os
import sys
import shutil
import logging
import uuid
from pathlib import Path
from typing import Callable, Optional

from pulumi import automation as auto

from . import opttest
from .results import UpdateResult, PreviewResult, RefreshResult

#: Directory and file names never copied from the program under test.
#:
#: These hold credentials (``.env*``), history that may contain old secrets
#: (``.git``), or build output that is large and reproducible.
EXCLUDED_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".env",
        "node_modules",
        "bin",
        "obj",
        "__pycache__",
        ".venv",
        "venv",
        ".terraform",
    }
)


def _is_excluded_name(name: str) -> bool:
    return name in EXCLUDED_NAMES or name.startswith(".env.")


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _copy_file(src: str, dst: str) -> None:
    src_path, dst_path = Path(src), Path(dst)
    dst_path.write_bytes(src_path.read_bytes())
    dst_path.chmod(src_path.stat().st_mode)


def _copy_symlink(src: Path, dst: Path) -> None:
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.symlink_to(os.readlink(src))


def _safe_copy_filter(
    source_root: str,
    avoid: list[str],
    extra: Optional[Callable[[str], bool]] = None,
) -> Callable[[Path], bool]:
    """Build a copy filter that skips excluded names, refuses symlinks whose
    target lies outside ``source_root``, and never descends into anything in
    ``avoid`` (typically the destination, so copying a directory into its own
    subtree cannot recurse).

    Paths are compared lexically (``os.path.abspath``) rather than resolved,
    so a symlink's own path is never itself followed while deciding whether
    it is in scope.
    """
    root = os.path.abspath(str(source_root))
    avoid_resolved = [os.path.abspath(str(a)) for a in avoid]

    def filt(src: Path) -> bool:
        resolved = os.path.abspath(str(src))
        if resolved == root:
            return True
        for a in avoid_resolved:
            if resolved == a or resolved.startswith(a + os.sep):
                return False
        if _is_excluded_name(os.path.basename(resolved)):
            return False
        if src.is_symlink():
            target = os.path.abspath(
                os.path.join(os.path.dirname(resolved), os.readlink(src))
            )
            if target != root and not target.startswith(root + os.sep):
                return False
        return extra(resolved) if extra else True

    return filt


def _copy_directory(src_dir: str, dest: str, filt: Callable[[Path], bool]) -> None:
    """Recursive copy that consults ``filt`` for every entry before touching it.

    Symlinks are recreated verbatim, files overwrite, directories are created
    private to the current user (mode ``0700``). Each entry's ``is_symlink()``
    is checked before ``is_dir()`` so a symlink to a directory is never
    followed and recursed into.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    os.chmod(dest_path, 0o700)
    for entry in Path(src_dir).iterdir():
        if not filt(entry):
            continue
        dest_entry = dest_path / entry.name
        if entry.is_symlink():
            _copy_symlink(entry, dest_entry)
        elif entry.is_dir():
            _copy_directory(str(entry), str(dest_entry), filt)
        else:
            _copy_file(str(entry), str(dest_entry))


# Names preserved in the working directory when the source is swapped out.
PRESERVED_PATHS = {".pulumi", "Pulumi.yaml", "Pulumi.test.yaml"}


class PulumiProgram:
    """Framework-independent Pulumi program wrapper.

    Wraps Pulumi Automation API operations without any test framework
    dependencies. Provides a cleanup callback for registration with
    any test framework or manual invocation.
    """

    working_dir: str
    options: opttest.Options
    logger: logging.Logger
    current_stack: auto.Stack | None
    local_workspace: auto.LocalWorkspace | None
    #: True when the stack already existed and was selected rather than
    #: created. ``cleanup()`` refuses to destroy such a stack unless
    #: ``opttest.destroy_existing_stack()`` was given.
    stack_preexisted: bool
    #: Directory this program created and will remove in ``cleanup()``, if any.
    _owned_temp_dir: Optional[str]
    #: Local file backend directory created for this program, if any.
    _backend_dir: Optional[str]
    _env_vars: dict[str, str]

    defaultStackName = "test"

    def __init__(
        self,
        working_dir: str,
        *opts: opttest.Option,
        options: Optional[opttest.Options] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.working_dir = working_dir

        if options:
            self.options = options
        else:
            self.options = opttest.default_options()
        for opt in opts:
            opt.apply(self.options)

        if logger:
            self.logger = logger
        else:
            self.logger = self._create_default_logger()

        self.current_stack = None
        self.local_workspace = None
        self.stack_preexisted = False
        self._owned_temp_dir = None
        self._backend_dir = None

        self._env_vars = {
            "PULUMI_CONFIG_PASSPHRASE": self.options.config_passphrase
            or opttest.DEFAULT_CONFIG_PASSPHRASE,
        }

        if not self.options.test_in_place:
            program_dir, destination = self._create_temp_dir()
            self._owned_temp_dir = program_dir
            self._copy_to_internal(destination)
            self.working_dir = destination

        self._configure_backend()
        self._init_stack()

    def _create_default_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"PulumiProgram-{id(self)}")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(levelname)s - %(name)s - %(message)s")
        )
        if not logger.handlers:
            logger.addHandler(handler)
        return logger

    def _temp_base(self) -> Path:
        if self.options.temp_dir:
            return Path(self.options.temp_dir)
        return Path.cwd() / "tmp"

    def _create_temp_dir(self) -> tuple[str, str]:
        """Create ``<temp base>/programDir_<id>/<program name>``.

        Directories are private to the current user (``0700``) because the
        copy may include stack config and state.
        """
        base_dir = self._temp_base()
        base_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(base_dir, 0o700)

        program_dir = base_dir / f"programDir_{_short_id()}"
        self.logger.info(f"Creating temp directory {program_dir.name}")
        program_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(program_dir, 0o700)

        source_base = os.path.basename(os.path.abspath(self.working_dir))
        destination = program_dir / source_base
        destination.mkdir(parents=True, exist_ok=True)
        os.chmod(destination, 0o700)
        return str(program_dir), str(destination)

    def _configure_backend(self) -> None:
        """Pick the backend.

        Precedence: an explicit ``env("PULUMI_BACKEND_URL", ...)``, then the
        ambient backend if ``use_ambient_backend()`` was given, otherwise a
        private local file backend so test stacks never reach a shared
        backend.
        """
        if (
            "PULUMI_BACKEND_URL" not in self.options.custom_env
            and not self.options.use_ambient_backend
        ):
            if self._owned_temp_dir:
                backend_dir = Path(self._owned_temp_dir) / "backend"
            else:
                backend_dir = self._temp_base() / f"backend_{_short_id()}"
            backend_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(backend_dir, 0o700)
            self._backend_dir = str(backend_dir)
            self._env_vars["PULUMI_BACKEND_URL"] = backend_dir.absolute().as_uri()
        # Custom env vars from the env() option take precedence over defaults.
        self._env_vars.update(self.options.custom_env)

    def _active_env_vars(self) -> dict[str, str]:
        """Env vars to hand to the Automation API, with empty values dropped."""
        return {k: v for k, v in self._env_vars.items() if v}

    def _copy_to_internal(self, directory: str) -> None:
        try:
            _copy_directory(
                self.working_dir,
                directory,
                _safe_copy_filter(
                    self.working_dir, [directory, str(self._temp_base())]
                ),
            )
        except OSError as e:
            raise RuntimeError(f"Error copying program to {directory}: {e}") from e

    def _init_stack(self) -> None:
        self.logger.info("Creating local workspace...")
        active_env = self._active_env_vars()
        self.local_workspace = auto.LocalWorkspace(
            work_dir=self.working_dir, env_vars=active_env
        )

        if not self.options.skip_install:
            self.logger.info("Running pulumi install...")
            self.local_workspace.install()

        if self.options.skip_stack_create:
            self.logger.info("Skipping stack creation (skip_stack_create=True)")
            return

        stack_name = self.options.stack_name or self.defaultStackName
        opts = auto.LocalWorkspaceOptions(env_vars=active_env)
        self.logger.info(f"Running pulumi stack init... (stack: {stack_name})")
        try:
            self.current_stack = auto.create_stack(
                stack_name, work_dir=self.working_dir, opts=opts
            )
        except auto.StackAlreadyExistsError:
            self.current_stack = auto.select_stack(
                stack_name, work_dir=self.working_dir, opts=opts
            )
            self.stack_preexisted = True
            self.logger.info(
                f"Stack '{stack_name}' already existed and was selected, not created. "
                + (
                    "cleanup() will destroy it because destroy_existing_stack() was given."
                    if self.options.destroy_existing_stack
                    else "cleanup() will leave it in place; pass opttest.destroy_existing_stack() to destroy it."
                )
            )

    def cleanup(self) -> None:
        """Destroy and remove the stack, then delete the temporary copy of the
        program. Register with your test framework's cleanup.

        A stack that existed before this run is left untouched unless
        ``opttest.destroy_existing_stack()`` was given. The temporary
        directory is kept when the destroy fails, so the state is available
        for inspection, or when ``opttest.keep_temp_dir()`` was given.
        """
        if self.current_stack is not None:
            if self.stack_preexisted and not self.options.destroy_existing_stack:
                self.logger.info(
                    f"Stack '{self.current_stack.name}' existed before this run; "
                    "leaving it in place. Pass opttest.destroy_existing_stack() to destroy it."
                )
                return

            self.logger.info("Running pulumi destroy and removing stack...")
            try:
                self.current_stack.destroy(remove=True)
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
                return
        else:
            self.logger.info("No current stack, skipping destroy...")

        self._remove_temp_dirs()

    def _remove_temp_dirs(self) -> None:
        if self.options.keep_temp_dir:
            return
        for directory in (self._owned_temp_dir, self._backend_dir):
            if directory is not None and Path(directory).exists():
                shutil.rmtree(directory)

    def up(self) -> UpdateResult:
        """Run pulumi up."""
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")
        self.logger.info(f"Running pulumi up on stack: {self.current_stack.name}")
        return UpdateResult(self.current_stack.up())

    def preview(self) -> PreviewResult:
        """Run pulumi preview."""
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")
        self.logger.info(f"Running pulumi preview on stack: {self.current_stack.name}")
        return PreviewResult(self.current_stack.preview())

    def refresh(self) -> RefreshResult:
        """Run pulumi refresh."""
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")
        self.logger.info(f"Running pulumi refresh on stack: {self.current_stack.name}")
        return RefreshResult(self.current_stack.refresh())

    def destroy(self) -> auto.DestroyResult:
        """Run pulumi destroy."""
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")
        self.logger.info(f"Running pulumi destroy on stack: {self.current_stack.name}")
        return self.current_stack.destroy()

    def update_source(self, source_dir: str) -> None:
        """Update working directory from source, preserving stack state."""
        self.logger.info(f"Updating source from {source_dir} to {self.working_dir}")
        source_root = os.path.abspath(source_dir)

        def extra(resolved: str) -> bool:
            is_top_level = os.path.dirname(resolved) == source_root
            return not (is_top_level and os.path.basename(resolved) in PRESERVED_PATHS)

        try:
            _copy_directory(
                source_root,
                self.working_dir,
                _safe_copy_filter(source_root, [self.working_dir], extra),
            )
        except OSError as e:
            raise RuntimeError(f"Error updating source from {source_dir}: {e}") from e

    def add_environments(self, *environment_names: str) -> None:
        """Add ESC environments to stack."""
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")
        self.current_stack.add_environments(*environment_names)

    def get_env_vars(self) -> dict[str, str]:
        """Get the environment variables for this workspace.

        Includes the config passphrase and anything passed via
        ``opttest.env()``, which may be credentials. Do not log the returned
        object.
        """
        return self._env_vars.copy()

    def copy_to_temp_dir(self, *opts: opttest.Option) -> "PulumiProgram":
        """Copy program to a new temporary directory.

        The returned program owns that directory and removes it in ``cleanup()``.
        """
        program_dir, destination = self._create_temp_dir()
        copy = self.copy_to(destination, *opts)
        copy._owned_temp_dir = program_dir
        return copy

    def copy_to(self, directory: str, *opts: opttest.Option) -> "PulumiProgram":
        """Copy program to specified directory.

        The caller chose ``directory``, so the returned program does not remove
        it in ``cleanup()``. Use :meth:`copy_to_temp_dir` for a self-cleaning copy.
        """
        self._copy_to_internal(directory)
        options = self.options.copy()
        for opt in opts:
            opt.apply(options)
        opttest.test_in_place().apply(options)
        return PulumiProgram(directory, options=options, logger=self.logger)
