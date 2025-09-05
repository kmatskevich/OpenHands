"""Enhanced LocalRuntime with improved configuration and path mapping support."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from openhands.core.config import OpenHandsConfig
from openhands.core.config.runtime_config import LocalRuntimeConfig
from openhands.core.logger import openhands_logger as logger
from openhands.events import EventStream
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.llm.llm_registry import LLMRegistry
from openhands.runtime.impl.local.local_runtime import LocalRuntime as BaseLocalRuntime
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.runtime_status import RuntimeStatus


class EnhancedLocalRuntime(BaseLocalRuntime):
    """Enhanced LocalRuntime with improved configuration and path mapping support.

    This runtime extends the base LocalRuntime with:
    - Support for new runtime_config structure
    - Path mapping for Docker-in-Docker scenarios
    - Better validation and error handling
    - Improved workspace management
    """

    def __init__(
        self,
        config: OpenHandsConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> None:
        # Extract local runtime configuration
        self.local_config = self._get_local_config(config)

        # Validate configuration before initialization
        self._validate_configuration(config)

        # Set up workspace based on configuration
        self._setup_workspace(config)

        # Initialize base runtime
        super().__init__(
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

        logger.info(
            f'Enhanced LocalRuntime initialized with project_root: {self.get_project_root()}'
        )

    def _get_local_config(self, config: OpenHandsConfig) -> LocalRuntimeConfig:
        """Extract local runtime configuration from main config.

        Args:
            config: Main OpenHands configuration

        Returns:
            Local runtime configuration
        """
        # Check if new runtime_config structure is used
        if hasattr(config, 'runtime_config') and config.runtime_config:
            return config.runtime_config.local

        # Fall back to creating default local config
        return LocalRuntimeConfig()

    def _validate_configuration(self, config: OpenHandsConfig) -> None:
        """Validate local runtime configuration.

        Args:
            config: Main OpenHands configuration

        Raises:
            ValueError: If configuration is invalid
        """
        is_valid, errors = self.local_config.validate_project_root(
            config.workspace_base
        )
        if not is_valid:
            error_msg = 'Local runtime configuration validation failed:\n' + '\n'.join(
                f'  - {error}' for error in errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _setup_workspace(self, config: OpenHandsConfig) -> None:
        """Set up workspace directory based on configuration.

        Args:
            config: Main OpenHands configuration
        """
        project_root = self.local_config.get_project_root(config.workspace_base)

        if project_root:
            # Use configured project root
            config.workspace_mount_path_in_sandbox = str(project_root)
            logger.info(f'Using configured project root: {project_root}')
        else:
            # Create temporary workspace
            temp_workspace = tempfile.mkdtemp(prefix=f'openhands_workspace_{self.sid}_')
            config.workspace_mount_path_in_sandbox = temp_workspace
            logger.warning(
                f'No project root configured, using temporary workspace: {temp_workspace}'
            )

    def get_project_root(self) -> Path | None:
        """Get the current project root path.

        Returns:
            Project root path or None if not configured
        """
        return self.local_config.get_project_root(self.config.workspace_base)

    def resolve_path(self, path: str) -> str:
        """Resolve a path, applying path mapping if configured.

        Args:
            path: Path to resolve

        Returns:
            Resolved path

        Raises:
            ValueError: If path mapping fails
        """
        try:
            # Apply path mapping if configured
            mapped_path = self.local_config.map_path(path)

            # Resolve to absolute path
            resolved_path = Path(mapped_path).expanduser().resolve()

            return str(resolved_path)
        except Exception as e:
            logger.error(f'Failed to resolve path {path}: {e}')
            raise ValueError(f'Path resolution failed: {e}') from e

    def read_file(self, path: str) -> str:
        """Read file content with path mapping support.

        Args:
            path: File path to read

        Returns:
            File content

        Raises:
            ValueError: If path resolution fails
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not readable
        """
        resolved_path = self.resolve_path(path)

        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f'File not found: {resolved_path}')
        except PermissionError:
            raise PermissionError(f'Permission denied reading file: {resolved_path}')
        except Exception as e:
            raise ValueError(f'Error reading file {resolved_path}: {e}') from e

    def write_file(self, path: str, content: str) -> None:
        """Write file content with path mapping support.

        Args:
            path: File path to write
            content: Content to write

        Raises:
            ValueError: If path resolution fails
            PermissionError: If file is not writable
        """
        resolved_path = self.resolve_path(path)

        try:
            # Ensure parent directory exists
            Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)

            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except PermissionError:
            raise PermissionError(f'Permission denied writing file: {resolved_path}')
        except Exception as e:
            raise ValueError(f'Error writing file {resolved_path}: {e}') from e

    def run_command(self, command: str, cwd: str | None = None) -> tuple[int, str, str]:
        """Run shell command with path mapping support.

        Args:
            command: Command to run
            cwd: Working directory (will be path-mapped if provided)

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            ValueError: If path resolution fails
        """
        # Resolve working directory if provided
        if cwd:
            cwd = self.resolve_path(cwd)
        else:
            # Use project root as default working directory
            project_root = self.get_project_root()
            if project_root:
                cwd = str(project_root)

        try:
            logger.debug(f'Running command in {cwd}: {command}')

            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.config.sandbox.timeout,
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            raise ValueError(
                f'Command timed out after {self.config.sandbox.timeout} seconds: {command}'
            )
        except Exception as e:
            raise ValueError(f'Error running command {command}: {e}') from e

    def get_runtime_info(self) -> dict[str, Any]:
        """Get runtime information for diagnostics.

        Returns:
            Dictionary with runtime information
        """
        project_root = self.get_project_root()

        info = {
            'runtime_type': 'local',
            'project_root': str(project_root) if project_root else None,
            'project_root_exists': project_root.exists() if project_root else False,
            'project_root_readable': False,
            'project_root_writable': False,
            'path_mapping_enabled': bool(
                self.local_config.mount_host_prefix
                and self.local_config.mount_container_prefix
            ),
            'mount_host_prefix': self.local_config.mount_host_prefix,
            'mount_container_prefix': self.local_config.mount_container_prefix,
            'user_id': self._user_id,
            'username': self._username,
            'is_windows': self.is_windows,
        }

        # Check permissions if project root exists
        if project_root and project_root.exists():
            info['project_root_readable'] = os.access(project_root, os.R_OK)
            info['project_root_writable'] = os.access(project_root, os.W_OK)

        return info

    def validate_path_access(self, path: str) -> tuple[bool, str]:
        """Validate that a path can be accessed with current configuration.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            resolved_path = self.resolve_path(path)

            # Check if path exists
            if not Path(resolved_path).exists():
                return False, f'Path does not exist: {resolved_path}'

            # Check if path is readable
            if not os.access(resolved_path, os.R_OK):
                return False, f'Path is not readable: {resolved_path}'

            return True, ''

        except Exception as e:
            return False, str(e)


# For backward compatibility, we can alias the enhanced version
LocalRuntime = EnhancedLocalRuntime
