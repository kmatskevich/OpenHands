"""Unified diagnostics endpoint for OpenHands."""

import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from openhands.core.logger import openhands_logger as logger
from openhands.memory.project_memory import create_project_memory
from openhands.server.shared import config

router = APIRouter(prefix='/api')


class DiagnosticsResponse:
    """Structured diagnostics response."""

    def __init__(self):
        self.runtime: dict[str, Any] = {}
        self.paths: dict[str, Any] = {}
        self.memory: dict[str, Any] = {}
        self.validation: dict[str, Any] = {}
        self.env: dict[str, Any] = {}
        self.versions: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            'runtime': self.runtime,
            'paths': self.paths,
            'memory': self.memory,
            'validation': self.validation,
            'env': self.env,
            'versions': self.versions,
        }


def get_runtime_info() -> dict[str, Any]:
    """Get runtime information."""
    runtime_info = {
        'kind': config.runtime,
        'requires_restart': False,
    }

    # Check if restart is needed based on config changes
    # This is a placeholder - actual logic would depend on config change detection
    if hasattr(config, '_requires_restart'):
        runtime_info['requires_restart'] = config._requires_restart

    return runtime_info


def get_paths_info() -> dict[str, Any]:
    """Get path information."""
    paths_info: dict[str, Any] = {
        'config_path': None,
        'project_root': None,
        'workspace_mount_path': None,
        'workspace_base': None,
    }

    try:
        # Try to load config to get paths
        from openhands.core.config import load_openhands_config

        config = load_openhands_config()

        # Get config path
        if hasattr(config, 'config_file') and config.config_file:
            paths_info['config_path'] = str(config.config_file)

        # Get project root for local runtime
        if config.runtime == 'local':
            if hasattr(config, 'workspace_base') and config.workspace_base:
                paths_info['project_root'] = str(config.workspace_base)
                paths_info['workspace_base'] = str(config.workspace_base)

        # Get workspace mount path
        if hasattr(config, 'workspace_mount_path') and config.workspace_mount_path:
            paths_info['workspace_mount_path'] = str(config.workspace_mount_path)
    except Exception as e:
        logger.debug(f'Failed to get paths info: {e}')

    return paths_info


def get_memory_info() -> dict[str, Any]:
    """Get project memory information."""
    memory_info: dict[str, Any] = {
        'backend': None,
        'connected': False,
        'db_path': None,
        'schema_version': None,
        'events_count': 0,
        'files_indexed': 0,
        'last_event_ts': None,
    }

    try:
        # Try to create/connect to project memory
        from openhands.core.config import load_openhands_config

        config = load_openhands_config()
        if (
            config.runtime == 'local'
            and hasattr(config, 'workspace_base')
            and config.workspace_base
        ):
            memory = create_project_memory(str(config.workspace_base), config.runtime)
            if memory and hasattr(memory, 'is_connected') and memory.is_connected():
                memory_info['backend'] = 'sqlite'
                memory_info['connected'] = True
                if hasattr(memory, 'db_path'):
                    memory_info['db_path'] = str(memory.db_path)

                # Get status from memory
                if hasattr(memory, 'get_status'):
                    status = memory.get_status()
                    memory_info.update(
                        {
                            'schema_version': status.get('schema_version'),
                            'events_count': status.get('event_count', 0),
                            'files_indexed': status.get('file_count', 0),
                            'last_event_ts': status.get('last_event_ts'),
                        }
                    )
                elif hasattr(memory, 'get_events_count'):
                    # Fallback to individual methods
                    memory_info['events_count'] = memory.get_events_count()
                    if hasattr(memory, 'get_files_indexed_count'):
                        memory_info['files_indexed'] = memory.get_files_indexed_count()

    except Exception as e:
        logger.debug(f'Failed to get memory info: {e}')

    return memory_info


def get_validation_info() -> dict[str, Any]:
    """Get validation information."""
    validation_info: dict[str, Any] = {
        'errors': [],
        'warnings': [],
    }

    try:
        # Validate current configuration
        # This would use existing validation logic
        errors, warnings = _validate_config()
        validation_info['errors'] = errors
        validation_info['warnings'] = warnings

    except Exception as e:
        logger.debug(f'Failed to validate config: {e}')
        validation_info['errors'].append(f'Validation failed: {str(e)}')

    return validation_info


def _validate_config() -> tuple[list[str], list[str]]:
    """Validate configuration and return errors and warnings."""
    errors = []
    warnings = []

    try:
        from openhands.core.config import load_openhands_config

        config = load_openhands_config()

        # Basic validation checks
        if not hasattr(config, 'llms') or not config.llms:
            errors.append('LLM model is not configured')
        else:
            # Get first LLM config
            first_llm_key = next(iter(config.llms.keys())) if config.llms else None
            if not first_llm_key or not config.llms[first_llm_key].model:
                errors.append('LLM model is not configured')

        if config.runtime == 'local':
            if not hasattr(config, 'workspace_base') or not config.workspace_base:
                errors.append('Workspace base path is required for local runtime')
            elif not Path(config.workspace_base).exists():
                errors.append(
                    f'Workspace base path does not exist: {config.workspace_base}'
                )

        # Check for common warnings
        if config.runtime == 'docker' and not hasattr(
            config.sandbox, 'base_container_image'
        ):
            warnings.append('No container image specified for Docker runtime')
    except Exception as e:
        errors.append(f'Config validation error: {str(e)}')

    return errors, warnings


def get_env_info() -> dict[str, Any]:
    """Get environment variable information."""
    env_info: dict[str, Any] = {
        'openhands_overrides': [],
    }

    # Find OPENHANDS_* environment variables (names only, no values)
    openhands_vars = []
    for key in os.environ:
        if key.startswith('OPENHANDS_'):
            openhands_vars.append(key)

    env_info['openhands_overrides'] = sorted(openhands_vars)
    return env_info


def get_versions_info() -> dict[str, Any]:
    """Get version information."""
    versions_info: dict[str, Any] = {
        'app_version': None,
        'git_sha': None,
        'git_branch': None,
    }

    try:
        # Try to get version from package
        try:
            import openhands

            if hasattr(openhands, '__version__'):
                versions_info['app_version'] = openhands.__version__
        except (ImportError, AttributeError):
            pass

        # Try to get git information
        try:
            # Get git SHA
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                versions_info['git_sha'] = result.stdout.strip()[:8]

            # Get git branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                versions_info['git_branch'] = result.stdout.strip()

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    except Exception as e:
        logger.debug(f'Failed to get version info: {e}')

    return versions_info


@router.get('/diagnostics')
async def get_diagnostics() -> dict[str, Any]:
    """Get comprehensive diagnostics information.

    Returns:
        Structured diagnostics data with sections for runtime, paths,
        memory, validation, environment, and versions.
    """
    try:
        response = DiagnosticsResponse()

        # Populate all sections
        response.runtime = get_runtime_info()
        response.paths = get_paths_info()
        response.memory = get_memory_info()
        response.validation = get_validation_info()
        response.env = get_env_info()
        response.versions = get_versions_info()

        return response.to_dict()

    except Exception as e:
        logger.error(f'Diagnostics failed: {e}')
        # Return minimal error response
        return {
            'runtime': {'kind': 'unknown', 'requires_restart': False},
            'paths': {},
            'memory': {'backend': None, 'connected': False},
            'validation': {'errors': [f'Diagnostics failed: {str(e)}'], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {},
        }


# Alias for consistency with other route files
app = router
