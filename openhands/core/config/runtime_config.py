"""Runtime configuration models."""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocalRuntimeConfig(BaseModel):
    """Configuration for local runtime environment.

    Attributes:
        project_root: Working root directory for the local runtime.
            If not specified, uses workspace_base from main config.
        mount_host_prefix: Host path prefix for path mapping (e.g., /Users).
            Used when running inside Docker to map host paths to container paths.
        mount_container_prefix: Container path prefix for path mapping (e.g., /host/Users).
            Used when running inside Docker to map host paths to container paths.
    """

    project_root: str | None = Field(
        default=None,
        description='Working root directory for local runtime. If not specified, uses workspace_base.',
    )
    mount_host_prefix: str | None = Field(
        default=None,
        description='Host path prefix for path mapping when running inside Docker (e.g., /Users)',
    )
    mount_container_prefix: str | None = Field(
        default=None,
        description='Container path prefix for path mapping when running inside Docker (e.g., /host/Users)',
    )

    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='after')
    def validate_path_mapping(self) -> 'LocalRuntimeConfig':
        """Validate path mapping configuration."""
        if self.mount_host_prefix and not self.mount_container_prefix:
            raise ValueError(
                'mount_host_prefix specified without mount_container_prefix. '
                'Both must be provided for path mapping.'
            )

        if self.mount_container_prefix and not self.mount_host_prefix:
            raise ValueError(
                'mount_container_prefix specified without mount_host_prefix. '
                'Both must be provided for path mapping.'
            )

        if self.mount_host_prefix and self.mount_container_prefix:
            # Validate that mount paths are absolute
            if not os.path.isabs(self.mount_host_prefix):
                raise ValueError(
                    f'mount_host_prefix must be absolute path: {self.mount_host_prefix}'
                )

            if not os.path.isabs(self.mount_container_prefix):
                raise ValueError(
                    f'mount_container_prefix must be absolute path: {self.mount_container_prefix}'
                )

        return self

    def get_project_root(self, workspace_base: str | None = None) -> Path | None:
        """Get the resolved project root path.

        Args:
            workspace_base: Fallback workspace base path from main config

        Returns:
            Resolved project root path or None if not configured
        """
        project_root = self.project_root or workspace_base
        if project_root:
            return Path(project_root).expanduser().resolve()
        return None

    def validate_project_root(
        self, workspace_base: str | None = None
    ) -> tuple[bool, list[str]]:
        """Validate project root configuration.

        Args:
            workspace_base: Fallback workspace base path from main config

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        project_root_path = self.get_project_root(workspace_base)

        if not project_root_path:
            errors.append(
                'No project_root specified and no workspace_base fallback available'
            )
            return False, errors

        # Validate project root exists
        if not project_root_path.exists():
            errors.append(
                f'Project root does not exist: {project_root_path}. '
                f'Please create the directory or update the configuration.'
            )

        # Validate project root is a directory
        elif not project_root_path.is_dir():
            errors.append(
                f'Project root is not a directory: {project_root_path}. '
                f'Please specify a valid directory path.'
            )

        else:
            # Validate read/write permissions
            if not os.access(project_root_path, os.R_OK):
                errors.append(
                    f'Project root is not readable: {project_root_path}. '
                    f'Please check directory permissions.'
                )

            if not os.access(project_root_path, os.W_OK):
                errors.append(
                    f'Project root is not writable: {project_root_path}. '
                    f'Please check directory permissions.'
                )

        return len(errors) == 0, errors

    def map_path(self, path: str) -> str:
        """Map a host path to container path if mapping is configured.

        Args:
            path: Host path to map

        Returns:
            Mapped container path or original path if no mapping

        Raises:
            ValueError: If path is not under the mounted prefix
        """
        if not self.mount_host_prefix or not self.mount_container_prefix:
            return path

        # Normalize paths
        abs_path = os.path.abspath(path)
        host_prefix = os.path.abspath(self.mount_host_prefix)

        # Check if path is under the mounted prefix
        if not abs_path.startswith(host_prefix):
            raise ValueError(
                f'Path {abs_path} is not under mounted prefix {host_prefix}. '
                f'Only paths under the mounted prefix can be accessed.'
            )

        # Map to container path
        relative_path = os.path.relpath(abs_path, host_prefix)
        container_path = os.path.join(self.mount_container_prefix, relative_path)

        return os.path.normpath(container_path)


class RuntimeConfig(BaseModel):
    """Runtime configuration settings.

    Attributes:
        environment: Runtime environment type (docker, local, remote, etc.).
            Defaults to 'docker' for backward compatibility.
        local: Local runtime specific configuration.
    """

    environment: str = Field(
        default='docker',
        description='Runtime environment type (docker, local, remote, etc.)',
    )
    local: LocalRuntimeConfig = Field(
        default_factory=LocalRuntimeConfig,
        description='Local runtime specific configuration',
    )

    model_config = ConfigDict(extra='forbid')

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> 'RuntimeConfig':
        """Create RuntimeConfig from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            RuntimeConfig instance
        """
        # Handle legacy format where runtime is just a string
        if isinstance(data, str):
            return cls(environment=data)

        # Handle new format with nested configuration
        if isinstance(data, dict):
            return cls.model_validate(data)

        raise ValueError(f'Invalid runtime configuration data: {data}')

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return self.model_dump()

    def is_local_runtime(self) -> bool:
        """Check if this is a local runtime configuration.

        Returns:
            True if environment is 'local'
        """
        return self.environment == 'local'

    def validate_for_environment(
        self, workspace_base: str | None = None
    ) -> tuple[bool, list[str]]:
        """Validate configuration for the specified environment.

        Args:
            workspace_base: Workspace base path for validation

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate environment type
        valid_environments = {
            'docker',
            'local',
            'remote',
            'kubernetes',
            'cli',
            'e2b',
            'modal',
        }
        if self.environment not in valid_environments:
            errors.append(
                f'Invalid runtime environment: {self.environment}. '
                f'Valid options are: {", ".join(sorted(valid_environments))}'
            )

        # Validate local runtime specific configuration
        if self.environment == 'local':
            is_valid, local_errors = self.local.validate_project_root(workspace_base)
            errors.extend(local_errors)

        return len(errors) == 0, errors
