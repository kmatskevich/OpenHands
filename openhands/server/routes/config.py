"""Configuration management REST API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openhands.core import logger
from openhands.core.config import (
    get_config,
    get_config_loader,
    requires_restart,
    reset_restart_flag,
    update_config,
)
from openhands.server.dependencies import get_dependencies

app = APIRouter(prefix='/api/config', dependencies=get_dependencies())


class ConfigResponse(BaseModel):
    """Response model for configuration data."""

    config: dict[str, Any]
    sources: dict[str, dict[str, Any]]
    requires_restart: bool


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates."""

    changes: dict[str, Any]
    source: str = 'user'


class ConfigUpdateResponse(BaseModel):
    """Response model for configuration updates."""

    success: bool
    requires_restart: bool
    message: str


class ConfigValidationResponse(BaseModel):
    """Response model for configuration validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]


class ConfigDiagnosticsResponse(BaseModel):
    """Response model for configuration diagnostics."""

    config_path: Optional[str]
    sources: dict[str, dict[str, Any]]
    cold_keys: list[str]
    hot_keys: list[str]
    requires_restart: bool
    environment_overrides: dict[str, Any]
    cli_overrides: dict[str, Any]


@app.get(
    '/',
    response_model=ConfigResponse,
    responses={
        500: {'description': 'Error loading configuration', 'model': dict},
    },
)
async def get_configuration() -> ConfigResponse | JSONResponse:
    """Get the current configuration from all sources."""
    try:
        loader = get_config_loader()
        config = get_config()

        # Convert config to dictionary for JSON serialization
        config_dict = config.model_dump()

        return ConfigResponse(
            config=config_dict,
            sources=loader.get_source_info(),
            requires_restart=requires_restart(),
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error loading configuration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error loading configuration: {str(e)}'},
        )


@app.post(
    '/update',
    response_model=ConfigUpdateResponse,
    responses={
        400: {'description': 'Invalid configuration data', 'model': dict},
        500: {'description': 'Error updating configuration', 'model': dict},
    },
)
async def update_configuration(
    request: ConfigUpdateRequest,
) -> ConfigUpdateResponse | JSONResponse:
    """Update configuration with new values."""
    try:
        # Validate source parameter
        valid_sources = ['user', 'env', 'cli']
        if request.source not in valid_sources:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={'error': f'Invalid source. Must be one of: {valid_sources}'},
            )

        # Update configuration
        needs_restart = update_config(request.changes, request.source)

        message = 'Configuration updated successfully'
        if needs_restart:
            message += '. Restart required for changes to take effect.'

        return ConfigUpdateResponse(
            success=True,
            requires_restart=needs_restart,
            message=message,
        )
    except ValueError as e:
        logger.openhands_logger.warning(f'Invalid configuration data: {e}')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'error': f'Invalid configuration data: {str(e)}'},
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error updating configuration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error updating configuration: {str(e)}'},
        )


@app.post(
    '/validate',
    response_model=ConfigValidationResponse,
    responses={
        500: {'description': 'Error validating configuration', 'model': dict},
    },
)
async def validate_configuration(
    config_data: dict[str, Any],
) -> ConfigValidationResponse | JSONResponse:
    """Validate configuration data without applying it."""
    try:
        loader = get_config_loader()
        is_valid, errors, warnings = loader.validate_config(config_data)

        return ConfigValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error validating configuration: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error validating configuration: {str(e)}'},
        )


@app.get(
    '/diagnostics',
    response_model=dict,
    responses={
        500: {'description': 'Error getting configuration diagnostics', 'model': dict},
    },
)
async def get_configuration_diagnostics() -> JSONResponse:
    """Get detailed configuration diagnostics and metadata."""
    try:
        loader = get_config_loader()
        diagnostics = loader.get_diagnostics()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=diagnostics,
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error getting configuration diagnostics: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error getting configuration diagnostics: {str(e)}'},
        )


@app.post(
    '/reset-restart-flag',
    response_model=dict,
    responses={
        200: {'description': 'Restart flag reset successfully', 'model': dict},
        500: {'description': 'Error resetting restart flag', 'model': dict},
    },
)
async def reset_restart_flag_endpoint() -> JSONResponse:
    """Reset the requires restart flag (call after restart)."""
    try:
        reset_restart_flag()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Restart flag reset successfully'},
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error resetting restart flag: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error resetting restart flag: {str(e)}'},
        )


@app.get(
    '/schema',
    response_model=dict,
    responses={
        500: {'description': 'Error getting configuration schema', 'model': dict},
    },
)
async def get_configuration_schema() -> JSONResponse:
    """Get the configuration schema for validation and documentation."""
    try:
        from openhands.core.config.openhands_config import OpenHandsConfig

        schema = OpenHandsConfig.model_json_schema()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=schema,
        )
    except Exception as e:
        logger.openhands_logger.error(f'Error getting configuration schema: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error getting configuration schema: {str(e)}'},
        )
