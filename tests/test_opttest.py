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

from pulumitest import opttest


def test_default_options():
    opts = opttest.default_options()
    assert opts.stack_name == "test"
    assert opts.skip_install is False
    assert opts.skip_stack_create is False
    assert opts.test_in_place is False
    assert opts.config_passphrase == "correct horse battery staple"
    assert opts.use_ambient_backend is False
    assert opts.custom_env == {}
    assert opts.destroy_existing_stack is False
    assert opts.keep_temp_dir is False


def test_stack_name():
    opts = opttest.default_options()
    opttest.stack_name("dev").apply(opts)
    assert opts.stack_name == "dev"


def test_skip_install():
    opts = opttest.default_options()
    opttest.skip_install().apply(opts)
    assert opts.skip_install is True


def test_skip_stack_create():
    opts = opttest.default_options()
    opttest.skip_stack_create().apply(opts)
    assert opts.skip_stack_create is True


def test_test_in_place():
    opts = opttest.default_options()
    opttest.test_in_place().apply(opts)
    assert opts.test_in_place is True


def test_temp_dir():
    opts = opttest.default_options()
    opttest.temp_dir("/tmp/test").apply(opts)
    assert opts.temp_dir == "/tmp/test"


def test_config_passphrase():
    opts = opttest.default_options()
    opttest.config_passphrase("secret").apply(opts)
    assert opts.config_passphrase == "secret"


def test_use_ambient_backend():
    opts = opttest.default_options()
    opttest.use_ambient_backend().apply(opts)
    assert opts.use_ambient_backend is True


def test_env():
    opts = opttest.default_options()
    opttest.env("FOO", "bar").apply(opts)
    assert opts.custom_env == {"FOO": "bar"}


def test_destroy_existing_stack():
    opts = opttest.default_options()
    opttest.destroy_existing_stack().apply(opts)
    assert opts.destroy_existing_stack is True


def test_keep_temp_dir():
    opts = opttest.default_options()
    opttest.keep_temp_dir().apply(opts)
    assert opts.keep_temp_dir is True


def test_default_config_passphrase_constant():
    assert opttest.DEFAULT_CONFIG_PASSPHRASE == "correct horse battery staple"
    assert (
        opttest.default_options().config_passphrase == opttest.DEFAULT_CONFIG_PASSPHRASE
    )


def test_options_copy():
    opts = opttest.default_options()
    opts.custom_env["KEY"] = "val"
    copied = opts.copy()
    copied.custom_env["KEY2"] = "val2"
    assert "KEY2" not in opts.custom_env


def test_multiple_options():
    opts = opttest.default_options()
    opttest.stack_name("prod").apply(opts)
    opttest.skip_install().apply(opts)
    opttest.test_in_place().apply(opts)
    assert opts.stack_name == "prod"
    assert opts.skip_install is True
    assert opts.test_in_place is True
