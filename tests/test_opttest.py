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
