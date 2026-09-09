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

"""Test options for Pulumi testing framework.

Matches the Go providertest/opttest naming convention. Options control
how PulumiProgram initializes and runs Pulumi programs.
"""

import os
import copy
from dataclasses import dataclass, field
from typing import Callable, Protocol
from abc import abstractmethod

#: The fixed, publicly known passphrase used when none is supplied.
DEFAULT_CONFIG_PASSPHRASE = "correct horse battery staple"


@dataclass
class Options:
    """Configuration options for Pulumi testing."""

    stack_name: str = "test"
    skip_install: bool = False
    skip_stack_create: bool = False
    test_in_place: bool = False
    temp_dir: str = field(default_factory=lambda: os.getenv("PULUMITEST_TEMP_DIR", ""))
    config_passphrase: str = DEFAULT_CONFIG_PASSPHRASE
    use_ambient_backend: bool = False
    custom_env: dict[str, str] = field(default_factory=dict)
    #: Allow `cleanup()` to destroy a stack that existed before this run.
    destroy_existing_stack: bool = False
    #: Leave the temporary copy of the program on disk after `cleanup()`.
    keep_temp_dir: bool = False

    def copy(self) -> "Options":
        """Create a deep copy of the current options."""
        return copy.deepcopy(self)


class Option(Protocol):
    """Protocol for option functions."""

    @abstractmethod
    def apply(self, options: Options) -> None:
        """Apply this option to the given Options instance."""
        ...


class OptionFunc:
    """Function-based option implementation."""

    def __init__(self, func: Callable[[Options], None]):
        self.func = func

    def apply(self, options: Options) -> None:
        self.func(options)


def stack_name(name: str) -> Option:
    """Set the stack name to use when running the program under test."""

    def apply_option(o: Options) -> None:
        o.stack_name = name

    return OptionFunc(apply_option)


def skip_install() -> Option:
    """Skip running `pulumi install` before running the program under test."""

    def apply_option(o: Options) -> None:
        o.skip_install = True

    return OptionFunc(apply_option)


def skip_stack_create() -> Option:
    """Skip creating the stack before running the program under test."""

    def apply_option(o: Options) -> None:
        o.skip_stack_create = True

    return OptionFunc(apply_option)


def test_in_place() -> Option:
    """Run the program from its current location, rather than copying to a temporary directory.

    The program's real directory is used, so `up`, `destroy`, and `cleanup()`
    act on whatever stack the name resolves to there. A stack that already
    existed before the run is never destroyed by `cleanup()` unless
    `destroy_existing_stack()` is also given.
    """

    def apply_option(o: Options) -> None:
        o.test_in_place = True

    return OptionFunc(apply_option)


def temp_dir(directory: str) -> Option:
    """Set the temporary directory for copying the program under test."""

    def apply_option(o: Options) -> None:
        o.temp_dir = directory

    return OptionFunc(apply_option)


def config_passphrase(passphrase: str) -> Option:
    """Set the config passphrase to use when running the program under test.

    The default is the fixed, publicly known string
    `DEFAULT_CONFIG_PASSPHRASE`. Stack config secrets encrypted with it are
    not protected. Pass a real value if the test stack's config will hold
    anything sensitive.
    """

    def apply_option(o: Options) -> None:
        o.config_passphrase = passphrase

    return OptionFunc(apply_option)


def use_ambient_backend() -> Option:
    """Use whatever backend `pulumi login` or `PULUMI_BACKEND_URL` points at.

    By default each program gets its own local file backend under the temp
    directory, so test stacks never touch a shared backend. Pass this option
    when the test needs a real backend, for example to attach ESC
    environments or use Pulumi Cloud secrets providers.
    """

    def apply_option(o: Options) -> None:
        o.use_ambient_backend = True

    return OptionFunc(apply_option)


def env(key: str, value: str) -> Option:
    """Set a custom environment variable to use when running the program under test.

    Values are handed to the Pulumi CLI as-is and returned by
    `PulumiProgram.get_env_vars()`. Treat anything passed here as a secret
    that must not be logged.
    """

    def apply_option(o: Options) -> None:
        o.custom_env[key] = value

    return OptionFunc(apply_option)


def destroy_existing_stack() -> Option:
    """Allow `cleanup()` to destroy and remove a stack that already existed.

    Without this option a pre-existing stack that was selected instead of
    created is left untouched, because destroying it would remove
    infrastructure the test did not create.
    """

    def apply_option(o: Options) -> None:
        o.destroy_existing_stack = True

    return OptionFunc(apply_option)


def keep_temp_dir() -> Option:
    """Keep the temporary copy of the program on disk after `cleanup()`, for inspection."""

    def apply_option(o: Options) -> None:
        o.keep_temp_dir = True

    return OptionFunc(apply_option)


def default_options() -> Options:
    """Create a new Options instance with default values."""
    return Options()
