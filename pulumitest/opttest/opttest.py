"""Python conversion of opttest.go - Test options for Pulumi testing framework."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol
from abc import abstractmethod
import copy


class ProviderFactory(Protocol):
    """Protocol for provider factory functions."""
    def __call__(self) -> Any:
        ...


class ResourceProviderServerFactory(Protocol):
    """Protocol for resource provider server factory functions."""
    def __call__(self) -> Any:
        ...


class LocalWorkspaceOption(Protocol):
    """Protocol for local workspace options."""
    pass


class NewStackOpt(Protocol):
    """Protocol for new stack options."""
    pass


@dataclass
class ProviderConfigUnion:
    """Union type for specifying a provider configuration.
    Only one of factory or path should be set.
    """
    factory: Optional[ProviderFactory] = None
    path: Optional[str] = None


@dataclass
class Options:
    """Configuration options for Pulumi testing."""
    stack_name: str = "test"
    skip_install: bool = False
    skip_stack_create: bool = False
    new_stack_opts: List[NewStackOpt] = field(default_factory=list)
    test_in_place: bool = False
    temp_dir: str = field(default_factory=lambda: os.getenv("PULUMITEST_TEMP_DIR", ""))
    config_passphrase: str = "correct horse battery staple"
    providers: Dict[str, ProviderConfigUnion] = field(default_factory=dict)
    use_ambient_backend: bool = False
    yarn_links: List[str] = field(default_factory=list)
    go_mod_replacements: Dict[str, str] = field(default_factory=dict)
    custom_env: Dict[str, str] = field(default_factory=dict)
    extra_workspace_options: List[LocalWorkspaceOption] = field(default_factory=list)
    disable_grpc_log: bool = False

    def copy(self) -> 'Options':
        """Create a deep copy of the current options."""
        return copy.deepcopy(self)

    def provider_factories(self) -> Dict[str, ProviderFactory]:
        """Get provider factories from provider configurations."""
        provider_factories = {}
        for provider_name, provider_config in self.providers.items():
            if provider_config.factory is not None:
                provider_factories[provider_name] = provider_config.factory
        return provider_factories

    def provider_plugin_paths(self) -> Dict[str, str]:
        """Get provider plugin paths from provider configurations."""
        provider_plugin_paths = {}
        for provider_name, provider_config in self.providers.items():
            if provider_config.path:
                provider_plugin_paths[provider_name] = provider_config.path
        return provider_plugin_paths


class Option(Protocol):
    """Protocol for option functions."""
    
    @abstractmethod
    def apply(self, options: Options) -> None:
        """Apply this option to the given Options instance."""
        pass


class OptionFunc:
    """Function-based option implementation."""
    
    def __init__(self, func: Callable[[Options], None]):
        self.func = func
    
    def apply(self, options: Options) -> None:
        """Apply the function to the options."""
        self.func(options)


def stack_name(name: str) -> Option:
    """Set the default stack name to use when running the program under test."""
    def apply_option(o: Options) -> None:
        o.stack_name = name
    return OptionFunc(apply_option)


def skip_install() -> Option:
    """Skip running `pulumi install` before running the program under test."""
    def apply_option(o: Options) -> None:
        o.skip_install = True
    return OptionFunc(apply_option)


def skip_stack_create() -> Option:
    """Skip creating the stack before running the program under test.
    A stack will have to be created manually before running the program under test.
    """
    def apply_option(o: Options) -> None:
        o.skip_stack_create = True
    return OptionFunc(apply_option)


def test_in_place() -> Option:
    """Run the program under test from its current location, rather than firstly copying to a temporary directory."""
    def apply_option(o: Options) -> None:
        o.test_in_place = True
    return OptionFunc(apply_option)


def temp_dir(directory: str) -> Option:
    """Set the temporary directory to use when copying the program under test during a test.
    This directory will be created if missing and will not be cleaned up after the test.
    If not set (or set to an empty string), an OS-specific temporary directory will be used.
    It's recommended to ignore this directory in your version control system.
    """
    def apply_option(o: Options) -> None:
        o.temp_dir = directory
    return OptionFunc(apply_option)


def attach_provider(name: str, start_provider: ProviderFactory) -> Option:
    """Start the provider via the specified factory and attach it when running the program under test."""
    def apply_option(o: Options) -> None:
        o.providers[name] = ProviderConfigUnion(factory=start_provider)
    return OptionFunc(apply_option)


def attach_provider_binary(name: str, path: str) -> Option:
    """Add a provider to be started and attached for the test run.
    Path can be a directory or a binary. If it is a directory, the binary will be assumed to be
    pulumi-resource-<name> in that directory.
    """
    def apply_option(o: Options) -> None:
        # Note: In the Go version, this creates a LocalBinary provider factory
        # For now, we'll store the path directly - actual implementation would need
        # the equivalent of providers.LocalBinary()
        o.providers[name] = ProviderConfigUnion(path=path)
    return OptionFunc(apply_option)


def attach_provider_server(name: str, start_provider: ResourceProviderServerFactory) -> Option:
    """Start the specified provider server and attach for the test run."""
    def apply_option(o: Options) -> None:
        # Note: In Go this wraps with providers.ResourceProviderFactory
        # For now treating as a regular factory - actual implementation would need wrapping
        o.providers[name] = ProviderConfigUnion(factory=start_provider)
    return OptionFunc(apply_option)


def attach_downloaded_plugin(name: str, version: str) -> Option:
    """Install the plugin via `pulumi plugin install` then will start the provider and attach it for the test run."""
    def apply_option(o: Options) -> None:
        # Note: In Go this creates a DownloadPluginBinaryFactory
        # Actual implementation would need the equivalent factory
        def download_factory():
            # Placeholder - would need actual download logic
            return f"downloaded-{name}-{version}"
        o.providers[name] = ProviderConfigUnion(factory=download_factory)
    return OptionFunc(apply_option)


def local_provider_path(name: str, *path_parts: str) -> Option:
    """Set the path to the local provider binary to use when running the program under test.
    This sets the `plugins.providers` property in the project settings (Pulumi.yaml).
    """
    def apply_option(o: Options) -> None:
        path = str(Path(*path_parts)) if path_parts else ""
        o.providers[name] = ProviderConfigUnion(path=path)
    return OptionFunc(apply_option)


def download_provider_version(name: str, version: str) -> Option:
    """Download a specific provider version and configure its path."""
    def apply_option(o: Options) -> None:
        # Note: In Go this calls providers.DownloadPluginBinary and can panic
        # Python version should handle errors more gracefully
        try:
            # Placeholder - would need actual download logic
            binary_path = f"/tmp/pulumi-resource-{name}-{version}"
            o.providers[name] = ProviderConfigUnion(path=binary_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download provider {name}:{version}") from e
    return OptionFunc(apply_option)


def yarn_link(*packages: str) -> Option:
    """Specify packages which are linked via `yarn link` and should be used when running the program under test.
    Each package is called with `yarn link <package>` on stack creation.
    """
    def apply_option(o: Options) -> None:
        o.yarn_links.extend(packages)
    return OptionFunc(apply_option)


def go_mod_replacement(package_specifier: str, *replacement_path_parts: str) -> Option:
    """Specify replacements to be added to the go.mod file when running the program under test.
    Each replacement is added to the go.mod file with `go mod edit -replace <replacement>` on stack creation.
    """
    def apply_option(o: Options) -> None:
        replacement_path = str(Path(*replacement_path_parts)) if replacement_path_parts else ""
        o.go_mod_replacements[package_specifier] = replacement_path
    return OptionFunc(apply_option)


def use_ambient_backend() -> Option:
    """Skip setting `PULUMI_BACKEND_URL` to a local temporary directory which overrides any backend configuration 
    which might have been done on the local environment via `pulumi login`.
    Using this option will cause the program under test to use whatever backend configuration has been set via 
    `pulumi login` or an existing `PULUMI_BACKEND_URL` value.
    """
    def apply_option(o: Options) -> None:
        o.use_ambient_backend = True
    return OptionFunc(apply_option)


def disable_grpc_log() -> Option:
    """Disable the gRPC log which is written to grpc.log in the current working directory."""
    def apply_option(o: Options) -> None:
        o.disable_grpc_log = True
    return OptionFunc(apply_option)


def env(key: str, value: str) -> Option:
    """Set a custom environment variable to use when running the program under test."""
    def apply_option(o: Options) -> None:
        o.custom_env[key] = value
    return OptionFunc(apply_option)


def config_passphrase(passphrase: str) -> Option:
    """Set the config passphrase to use when running the program under test."""
    def apply_option(o: Options) -> None:
        o.config_passphrase = passphrase
    return OptionFunc(apply_option)


def workspace_options(*opts: LocalWorkspaceOption) -> Option:
    """Set additional options to pass to the workspace when running the program under test."""
    def apply_option(o: Options) -> None:
        o.extra_workspace_options.extend(opts)
    return OptionFunc(apply_option)


def new_stack_options(*opts: NewStackOpt) -> Option:
    """Set new stack options."""
    def apply_option(o: Options) -> None:
        o.new_stack_opts.extend(opts)
    return OptionFunc(apply_option)


def defaults() -> Option:
    """Set all options back to their defaults.
    This can be useful when using copy_to_temp_dir or convert but not wanting to inherit any options 
    from the previous PulumiTest.
    """
    def apply_option(o: Options) -> None:
        o.stack_name = "test"
        o.test_in_place = False
        o.skip_install = False
        o.skip_stack_create = False
        o.config_passphrase = "correct horse battery staple"
        o.providers = {}
        o.use_ambient_backend = False
        o.yarn_links = []
        o.go_mod_replacements = {}
        o.custom_env = {}
        o.extra_workspace_options = []
        o.disable_grpc_log = False
        o.temp_dir = os.getenv("PULUMITEST_TEMP_DIR", "")
    return OptionFunc(apply_option)


def default_options() -> Options:
    """Create a new Options instance with default values."""
    options = Options()
    defaults().apply(options)
    return options