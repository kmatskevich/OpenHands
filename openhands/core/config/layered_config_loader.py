"""Layered configuration loader for OpenHands.

This module implements a layered configuration system with the following precedence:
1. CLI overrides (highest priority)
2. Environment variables (OPENHANDS_*)
3. User config (~/.openhands/config.toml or OPENHANDS_CONFIG)
4. Default config (lowest priority)

The loader also supports hot/cold key classification for runtime configuration changes.
"""

import os
import shutil
from typing import Any, Optional

import toml

from openhands.core import logger
from openhands.core.config.openhands_config import OpenHandsConfig


class ConfigSource:
    """Represents a configuration source with metadata."""

    def __init__(
        self,
        name: str,
        path: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ):
        self.name = name
        self.path = path
        self.data = data or {}
        self.loaded = False


class LayeredConfigLoader:
    """Layered configuration loader with hot/cold key classification."""

    # Cold keys that require restart when changed
    COLD_KEYS = {
        'runtime',
        'runtime.environment',
        'runtime.local.project_root',
        'sandbox.base_container_image',
        'sandbox.runtime_container_image',
        'sandbox.platform',
        'security.sandbox_mode',
        'llm.api_base',
        'llm.base_url',
    }

    def __init__(self):
        self._config: Optional[OpenHandsConfig] = None
        self._sources: dict[str, ConfigSource] = {}
        self._requires_restart = False
        self._user_config_path: Optional[str] = None

    def get_user_config_path(self) -> str:
        """Get the path to the user config file."""
        # Check OPENHANDS_CONFIG environment variable first
        env_config_path = os.getenv('OPENHANDS_CONFIG')
        if env_config_path:
            return os.path.expanduser(env_config_path)

        # Default to ~/.openhands/config.toml
        return os.path.expanduser('~/.openhands/config.toml')

    def ensure_user_config_exists(self) -> str:
        """Ensure user config file exists, creating from template if needed."""
        user_config_path = self.get_user_config_path()
        user_config_dir = os.path.dirname(user_config_path)

        # Create directory if it doesn't exist
        os.makedirs(user_config_dir, exist_ok=True)

        # If config file doesn't exist, create from template
        if not os.path.exists(user_config_path):
            template_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                'config.template.toml',
            )

            if os.path.exists(template_path):
                shutil.copy2(template_path, user_config_path)
                logger.openhands_logger.info(
                    f'Created user config file from template: {user_config_path}'
                )
            else:
                # Create minimal config if template not found
                minimal_config = """###################### OpenHands Configuration ######################
# This file was auto-created. Modify as needed.
##############################################################################

[core]
# Runtime environment (docker | local)
#runtime = "docker"

# Default agent
#default_agent = "CodeActAgent"

[llm]
# API key for your LLM provider
api_key = ""

# Model to use
model = "gpt-4o"

[agent]
# Agent configuration
enable_browsing = true
enable_editor = true
enable_jupyter = true
enable_cmd = true

[sandbox]
# Sandbox configuration
#timeout = 120
"""
                with open(user_config_path, 'w', encoding='utf-8') as f:
                    f.write(minimal_config)
                logger.openhands_logger.info(
                    f'Created minimal user config file: {user_config_path}'
                )

        return user_config_path

    def load_default_config(self) -> ConfigSource:
        """Load default configuration."""
        source = ConfigSource('default')
        # Default config is embedded in the OpenHandsConfig class defaults
        config = OpenHandsConfig()
        source.data = config.model_dump()
        source.loaded = True
        return source

    def load_user_config(self) -> ConfigSource:
        """Load user configuration from file."""
        user_config_path = self.ensure_user_config_exists()
        self._user_config_path = user_config_path

        source = ConfigSource('user', user_config_path)

        try:
            with open(user_config_path, 'r', encoding='utf-8') as f:
                source.data = toml.load(f)
            source.loaded = True
            logger.openhands_logger.debug(
                f'Loaded user config from: {user_config_path}'
            )
        except Exception as e:
            logger.openhands_logger.warning(
                f'Failed to load user config from {user_config_path}: {e}'
            )
            source.data = {}

        return source

    def merge_configs(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge two configuration dictionaries recursively."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def load_config(self) -> OpenHandsConfig:
        """Load configuration from all sources in precedence order."""
        # Load sources in reverse precedence order (lowest to highest)
        self._sources['default'] = self.load_default_config()
        self._sources['user'] = self.load_user_config()

        # Start with default config object
        self._config = OpenHandsConfig()

        # Apply user config using the existing TOML loading mechanism
        if self._sources['user'].loaded and self._sources['user'].data:
            try:
                # Use the existing load_from_toml logic but with our loaded data
                # Create a temporary file with the user config data
                import tempfile

                from openhands.core.config.utils import load_from_toml

                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.toml', delete=False
                ) as tmp_file:
                    toml.dump(self._sources['user'].data, tmp_file)
                    tmp_file.flush()

                    # Load using existing mechanism
                    load_from_toml(self._config, tmp_file.name)

                # Clean up temp file
                os.unlink(tmp_file.name)

            except Exception as e:
                logger.openhands_logger.warning(f'Failed to apply user config: {e}')

        return self._config

    def get_config(self) -> OpenHandsConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self.load_config()
        # At this point _config should never be None since load_config() always returns a config
        assert self._config is not None
        return self._config

    def get_user_config_path_resolved(self) -> Optional[str]:
        """Get the resolved path to the user config file."""
        return self._user_config_path

    def requires_restart(self) -> bool:
        """Check if configuration changes require a restart."""
        return self._requires_restart

    def get_source_info(self) -> dict[str, dict[str, Any]]:
        """Get information about configuration sources."""
        info = {}
        for name, source in self._sources.items():
            info[name] = {
                'name': source.name,
                'path': source.path,
                'loaded': source.loaded,
                'keys_count': len(source.data) if source.data else 0,
            }
        return info


# Global instance
_config_loader: Optional[LayeredConfigLoader] = None


def get_config_loader() -> LayeredConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = LayeredConfigLoader()
    return _config_loader


def load_config() -> OpenHandsConfig:
    """Load configuration using the layered loader."""
    return get_config_loader().load_config()


def get_config() -> OpenHandsConfig:
    """Get the current configuration."""
    return get_config_loader().get_config()
