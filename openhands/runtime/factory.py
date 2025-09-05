"""Runtime factory for creating runtime instances based on configuration."""

import os
from pathlib import Path
from typing import Callable

from openhands.core.config import OpenHandsConfig
from openhands.core.logger import openhands_logger as logger
from openhands.events import EventStream
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.llm.llm_registry import LLMRegistry
from openhands.runtime import get_runtime_cls
from openhands.runtime.base import Runtime
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.runtime_status import RuntimeStatus


class RuntimeFactory:
    """Factory for creating runtime instances based on configuration.

    This factory provides a centralized way to create runtime instances
    with proper validation and configuration. It ensures that runtime
    instances are created consistently across the application.
    """

    _instance: 'RuntimeFactory | None' = None
    _current_runtime: Runtime | None = None
    _current_config_hash: str | None = None

    def __new__(cls) -> 'RuntimeFactory':
        """Singleton pattern to ensure only one factory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'RuntimeFactory':
        """Get the singleton factory instance."""
        return cls()

    def create_runtime(
        self,
        config: OpenHandsConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = False,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> Runtime:
        """Create a runtime instance based on configuration.

        Args:
            config: OpenHands configuration
            event_stream: Event stream for communication
            llm_registry: LLM registry instance
            sid: Session ID
            plugins: List of plugin requirements
            env_vars: Environment variables
            status_callback: Status callback function
            attach_to_existing: Whether to attach to existing runtime
            headless_mode: Whether to run in headless mode
            user_id: User ID
            git_provider_tokens: Git provider tokens

        Returns:
            Runtime instance

        Raises:
            ValueError: If runtime configuration is invalid
            RuntimeError: If runtime creation fails
        """
        # Validate runtime configuration
        self._validate_runtime_config(config)

        # Get runtime class based on configuration
        runtime_name = self._get_runtime_name(config)

        # Use enhanced LocalRuntime for local runtime
        if runtime_name == 'local':
            from openhands.runtime.impl.local.enhanced_local_runtime import (
                EnhancedLocalRuntime,
            )

            runtime_cls = EnhancedLocalRuntime  # type: ignore[assignment]
        else:
            runtime_cls = get_runtime_cls(runtime_name)  # type: ignore[assignment]

        logger.info(f'Creating {runtime_name} runtime for session {sid}')

        try:
            # Create runtime instance
            runtime = runtime_cls(
                config=config,
                event_stream=event_stream,
                llm_registry=llm_registry,
                sid=sid,
                plugins=plugins,
                env_vars=env_vars,
                status_callback=status_callback,
                attach_to_existing=attach_to_existing,
                headless_mode=headless_mode,
                user_id=user_id,
                git_provider_tokens=git_provider_tokens,
            )

            logger.debug(
                f'Successfully created {runtime_name} runtime for session {sid}'
            )
            return runtime

        except Exception as e:
            logger.error(
                f'Failed to create {runtime_name} runtime for session {sid}: {e}'
            )
            raise RuntimeError(f'Failed to create {runtime_name} runtime: {e}') from e

    def get_or_create_runtime(
        self,
        config: OpenHandsConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = False,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> Runtime:
        """Get existing runtime or create a new one if configuration changed.

        This method implements caching to avoid recreating runtimes when
        the configuration hasn't changed. If cold configuration keys have
        changed, a new runtime will be created.

        Args:
            config: OpenHands configuration
            event_stream: Event stream for communication
            llm_registry: LLM registry instance
            sid: Session ID
            plugins: List of plugin requirements
            env_vars: Environment variables
            status_callback: Status callback function
            attach_to_existing: Whether to attach to existing runtime
            headless_mode: Whether to run in headless mode
            user_id: User ID
            git_provider_tokens: Git provider tokens

        Returns:
            Runtime instance (cached or new)
        """
        # Calculate configuration hash for cold keys
        config_hash = self._calculate_cold_config_hash(config)

        # Check if we can reuse existing runtime
        if (
            self._current_runtime is not None
            and self._current_config_hash == config_hash
            and self._current_runtime.sid == sid
        ):
            logger.debug(f'Reusing existing runtime for session {sid}')
            return self._current_runtime

        # Create new runtime
        logger.debug(f'Creating new runtime for session {sid} (config changed)')
        runtime = self.create_runtime(
            config=config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=sid,
            plugins=plugins,
            env_vars=env_vars,
            status_callback=status_callback,
            attach_to_existing=attach_to_existing,
            headless_mode=headless_mode,
            user_id=user_id,
            git_provider_tokens=git_provider_tokens,
        )

        # Cache the new runtime
        self._current_runtime = runtime
        self._current_config_hash = config_hash

        return runtime

    def _validate_runtime_config(self, config: OpenHandsConfig) -> None:
        """Validate runtime configuration.

        Args:
            config: OpenHands configuration

        Raises:
            ValueError: If configuration is invalid
        """
        runtime_name = self._get_runtime_name(config)

        # Validate runtime name
        try:
            get_runtime_cls(runtime_name)
        except ValueError as e:
            raise ValueError(f'Invalid runtime configuration: {e}') from e

        # Validate local runtime specific configuration
        if runtime_name == 'local':
            self._validate_local_runtime_config(config)

    def _validate_local_runtime_config(self, config: OpenHandsConfig) -> None:
        """Validate local runtime specific configuration.

        Args:
            config: OpenHands configuration

        Raises:
            ValueError: If local runtime configuration is invalid
        """
        # Get local runtime configuration
        if hasattr(config, 'runtime_config') and config.runtime_config:
            local_config = config.runtime_config.local
            project_root = local_config.project_root or config.workspace_base
        else:
            # Legacy configuration
            project_root = config.workspace_base

        if project_root:
            project_root_path = Path(project_root).expanduser().resolve()

            # Validate project root exists
            if not project_root_path.exists():
                raise ValueError(
                    f'Local runtime project_root does not exist: {project_root_path}. '
                    f'Please create the directory or update the configuration.'
                )

            # Validate project root is a directory
            if not project_root_path.is_dir():
                raise ValueError(
                    f'Local runtime project_root is not a directory: {project_root_path}. '
                    f'Please specify a valid directory path.'
                )

            # Validate read/write permissions
            if not os.access(project_root_path, os.R_OK):
                raise ValueError(
                    f'Local runtime project_root is not readable: {project_root_path}. '
                    f'Please check directory permissions.'
                )

            if not os.access(project_root_path, os.W_OK):
                raise ValueError(
                    f'Local runtime project_root is not writable: {project_root_path}. '
                    f'Please check directory permissions.'
                )

        # Validate path mapping configuration if provided
        if hasattr(config, 'runtime_config') and config.runtime_config:
            local_config = config.runtime_config.local
            mount_host_prefix = local_config.mount_host_prefix
            mount_container_prefix = local_config.mount_container_prefix

            if mount_host_prefix and not mount_container_prefix:
                raise ValueError(
                    'Local runtime mount_host_prefix specified without mount_container_prefix. '
                    'Both must be provided for path mapping.'
                )

            if mount_container_prefix and not mount_host_prefix:
                raise ValueError(
                    'Local runtime mount_container_prefix specified without mount_host_prefix. '
                    'Both must be provided for path mapping.'
                )

            if mount_host_prefix and mount_container_prefix:
                # Validate that mount paths are absolute
                if not os.path.isabs(mount_host_prefix):
                    raise ValueError(
                        f'Local runtime mount_host_prefix must be absolute path: {mount_host_prefix}'
                    )

                if not os.path.isabs(mount_container_prefix):
                    raise ValueError(
                        f'Local runtime mount_container_prefix must be absolute path: {mount_container_prefix}'
                    )

    def _get_runtime_name(self, config: OpenHandsConfig) -> str:
        """Get runtime name from configuration.

        Args:
            config: OpenHands configuration

        Returns:
            Runtime name
        """
        # Check if runtime_config.environment is specified (new format)
        if hasattr(config, 'runtime_config') and config.runtime_config:
            return config.runtime_config.environment

        # Fall back to legacy runtime field
        return config.runtime

    def _calculate_cold_config_hash(self, config: OpenHandsConfig) -> str:
        """Calculate hash of cold configuration keys.

        Cold keys are configuration values that require runtime restart
        when changed. This hash is used to determine if a runtime needs
        to be recreated.

        Args:
            config: OpenHands configuration

        Returns:
            Hash string of cold configuration
        """
        import hashlib
        import json

        # Cold configuration keys that require runtime restart
        cold_config = {
            'runtime': self._get_runtime_name(config),
            'runtime_config': config.runtime_config.to_dict()
            if hasattr(config, 'runtime_config') and config.runtime_config
            else {},
            'sandbox_base_container_image': config.sandbox.base_container_image,
            'sandbox_runtime_container_image': config.sandbox.runtime_container_image,
            'sandbox_platform': config.sandbox.platform,
            'security_confirmation_mode': config.security.confirmation_mode,
            'workspace_base': config.workspace_base,
        }

        # Create deterministic hash
        config_str = json.dumps(cold_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear cached runtime instance.

        This forces creation of a new runtime on next request.
        Useful when configuration has been updated externally.
        """
        if self._current_runtime:
            logger.debug('Clearing cached runtime instance')
            self._current_runtime = None
            self._current_config_hash = None


# Global factory instance
_runtime_factory = RuntimeFactory()


def get_runtime_factory() -> RuntimeFactory:
    """Get the global runtime factory instance.

    Returns:
        RuntimeFactory instance
    """
    return _runtime_factory


def create_runtime(
    config: OpenHandsConfig,
    event_stream: EventStream,
    llm_registry: LLMRegistry,
    sid: str = 'default',
    plugins: list[PluginRequirement] | None = None,
    env_vars: dict[str, str] | None = None,
    status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
    attach_to_existing: bool = False,
    headless_mode: bool = False,
    user_id: str | None = None,
    git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
) -> Runtime:
    """Create a runtime instance using the global factory.

    This is a convenience function that uses the global runtime factory
    to create runtime instances.

    Args:
        config: OpenHands configuration
        event_stream: Event stream for communication
        llm_registry: LLM registry instance
        sid: Session ID
        plugins: List of plugin requirements
        env_vars: Environment variables
        status_callback: Status callback function
        attach_to_existing: Whether to attach to existing runtime
        headless_mode: Whether to run in headless mode
        user_id: User ID
        git_provider_tokens: Git provider tokens

    Returns:
        Runtime instance
    """
    factory = get_runtime_factory()
    return factory.create_runtime(
        config=config,
        event_stream=event_stream,
        llm_registry=llm_registry,
        sid=sid,
        plugins=plugins,
        env_vars=env_vars,
        status_callback=status_callback,
        attach_to_existing=attach_to_existing,
        headless_mode=headless_mode,
        user_id=user_id,
        git_provider_tokens=git_provider_tokens,
    )
