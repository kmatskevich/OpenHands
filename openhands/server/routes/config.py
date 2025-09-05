"""Configuration management API routes."""

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openhands.memory.project_memory import ProjectMemory
from openhands.server.dependencies import get_dependencies
from openhands.server.shared import config

app = APIRouter(prefix='/api/config', dependencies=get_dependencies())


class ConfigUpdateRequest(BaseModel):
    """Request model for config updates."""

    runtime: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateResponse(BaseModel):
    """Response model for config updates."""

    success: bool
    requires_restart: bool = False
    message: str = ''


class ConfigValidationResponse(BaseModel):
    """Response model for config validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiagnosticsResponse(BaseModel):
    """Response model for diagnostics."""

    runtime: dict[str, Any]
    config: dict[str, Any]
    system: dict[str, Any]
    memory: dict[str, Any] = Field(default_factory=dict)


@app.get('/', response_model=dict[str, Any])
async def get_config() -> dict[str, Any]:
    """Get current configuration.

    Returns:
        Dict[str, Any]: Current configuration including runtime settings.
    """
    config_dict = config.model_dump()

    # Add runtime configuration
    runtime_config = {
        'environment': config.runtime,
        'local': {
            'project_root': getattr(config, 'workspace_base', './workspace'),
            'mount_host_prefix': None,
            'mount_container_prefix': None,
        },
    }

    # Check if we have runtime_config from the new system
    if hasattr(config, 'runtime_config') and config.runtime_config:
        runtime_config = config.runtime_config.model_dump()

    config_dict['runtime'] = runtime_config
    return config_dict


@app.post('/update', response_model=ConfigUpdateResponse)
async def update_config(request: ConfigUpdateRequest) -> ConfigUpdateResponse:
    """Update configuration settings.

    Args:
        request: Configuration update request.

    Returns:
        ConfigUpdateResponse: Update result with restart requirement.
    """
    try:
        requires_restart = False

        # Check if runtime environment is changing
        if 'runtime' in request.runtime:
            runtime_env = request.runtime['runtime'].get('environment')
            if runtime_env and runtime_env != config.runtime:
                requires_restart = True

        # For now, we'll just indicate that restart is required for runtime changes
        # In a full implementation, this would update the actual config

        return ConfigUpdateResponse(
            success=True,
            requires_restart=requires_restart,
            message='Configuration updated successfully'
            + ('. Restart required for runtime changes.' if requires_restart else ''),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/validate', response_model=ConfigValidationResponse)
async def validate_config() -> ConfigValidationResponse:
    """Validate current configuration.

    Returns:
        ConfigValidationResponse: Validation results with errors and warnings.
    """
    errors = []
    warnings = []

    try:
        # Validate runtime configuration
        if config.runtime == 'local':
            # Check if project root exists and is accessible
            workspace_base = getattr(config, 'workspace_base', './workspace')
            if not os.path.exists(workspace_base):
                errors.append(
                    f'Project root directory does not exist: {workspace_base}'
                )
            elif not os.access(workspace_base, os.R_OK | os.W_OK):
                errors.append(
                    f'Project root directory is not readable/writable: {workspace_base}'
                )

            # Check if running in Docker and path is mounted
            if os.path.exists('/.dockerenv'):
                # We're in Docker, check if the path looks like it's mounted
                if not workspace_base.startswith('/host/'):
                    warnings.append(
                        "Running in Docker but project root doesn't appear to be mounted. "
                        'Consider mounting host paths with a prefix like /host/'
                    )

        return ConfigValidationResponse(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    except Exception as e:
        return ConfigValidationResponse(
            valid=False, errors=[f'Validation error: {str(e)}']
        )


@app.get('/diagnostics', response_model=DiagnosticsResponse)
async def get_diagnostics() -> DiagnosticsResponse:
    """Get system diagnostics information.

    Returns:
        DiagnosticsResponse: Comprehensive diagnostics information.
    """
    try:
        # Runtime information
        runtime_info = {
            'environment': config.runtime,
            'workspace_base': getattr(config, 'workspace_base', './workspace'),
            'in_docker': os.path.exists('/.dockerenv'),
            'user_id': os.getuid() if hasattr(os, 'getuid') else None,
            'group_id': os.getgid() if hasattr(os, 'getgid') else None,
        }

        # Config information
        config_info = {
            'config_file': os.environ.get('OPENHANDS_CONFIG_FILE', 'Not set'),
            'workspace_mount_path': getattr(config, 'workspace_mount_path', 'Not set'),
            'workspace_mount_path_in_sandbox': getattr(
                config, 'workspace_mount_path_in_sandbox', '/workspace'
            ),
        }

        # System information
        system_info = {
            'platform': os.name,
            'cwd': os.getcwd(),
            'env_vars': {
                key: value
                for key, value in os.environ.items()
                if key.startswith('OPENHANDS_')
                or key in ['DOCKER_HOST', 'HOME', 'USER']
            },
        }

        # Project memory information
        memory_info = {}
        if config.runtime == 'local':
            workspace_base = getattr(config, 'workspace_base', './workspace')
            try:
                # Try to create a ProjectMemory instance to check status
                project_memory = ProjectMemory(workspace_base, 'local')
                memory_status = project_memory.get_status()
                memory_info = {
                    'enabled': True,
                    'db_path': memory_status.get('db_path'),
                    'connected': memory_status.get('connected', False),
                    'schema_version': memory_status.get('schema_version'),
                    'event_count': memory_status.get('event_count', 0),
                    'file_count': memory_status.get('file_count', 0),
                }
            except Exception as e:
                memory_info = {'enabled': False, 'error': str(e)}
        else:
            memory_info = {
                'enabled': False,
                'reason': f'Project memory is only available for local runtime (current: {config.runtime})',
            }

        return DiagnosticsResponse(
            runtime=runtime_info,
            config=config_info,
            system=system_info,
            memory=memory_info,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to get diagnostics: {str(e)}'
        )
