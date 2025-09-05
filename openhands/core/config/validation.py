"""Configuration validation and diagnostics utilities."""

import os
import re
from typing import Any

from openhands.core import logger
from openhands.core.config.openhands_config import OpenHandsConfig


class ConfigValidationError(Exception):
    """Configuration validation error."""

    pass


class ConfigValidator:
    """Configuration validator with comprehensive validation rules."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(
        self, config_data: dict[str, Any]
    ) -> tuple[bool, list[str], list[str]]:
        """Validate configuration data and return validation results.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        try:
            # Basic Pydantic validation
            OpenHandsConfig(**config_data)

            # Additional custom validation
            self._validate_llm_config(config_data.get('llms', {}))
            self._validate_runtime_config(config_data.get('runtime', 'docker'))
            self._validate_new_runtime_config(
                config_data.get('runtime_config', {}), config_data
            )
            self._validate_sandbox_config(config_data.get('sandbox', {}))
            self._validate_agent_config(config_data.get('agents', {}))
            self._validate_security_config(config_data.get('security', {}))
            self._validate_file_paths(config_data)
            self._validate_deprecated_keys(config_data)

        except Exception as e:
            self.errors.append(f'Configuration validation failed: {str(e)}')

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_llm_config(self, llm_config: dict[str, Any]) -> None:
        """Validate LLM configuration."""
        if not llm_config:
            self.warnings.append('No LLM configuration found')
            return

        llm = llm_config.get('llm', {})
        if not llm:
            self.errors.append('Missing default LLM configuration')
            return

        model = llm.get('model')
        if not model:
            self.errors.append('LLM model is required')

        # Validate API key for certain providers
        api_key = llm.get('api_key', '')
        base_url = llm.get('base_url')

        if model and not api_key and not base_url:
            if any(
                provider in model.lower()
                for provider in ['openai', 'gpt', 'anthropic', 'claude']
            ):
                self.warnings.append(f'API key may be required for model: {model}')

        # Validate temperature range
        temperature = llm.get('temperature')
        if temperature is not None:
            if (
                not isinstance(temperature, (int, float))
                or temperature < 0
                or temperature > 2
            ):
                self.errors.append('LLM temperature must be between 0 and 2')

        # Validate top_p range
        top_p = llm.get('top_p')
        if top_p is not None:
            if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1:
                self.errors.append('LLM top_p must be between 0 and 1')

        # Validate timeout
        timeout = llm.get('timeout')
        if timeout is not None and timeout <= 0:
            self.errors.append('LLM timeout must be positive')

        # Validate retry settings
        num_retries = llm.get('num_retries')
        if num_retries is not None and num_retries < 0:
            self.errors.append('LLM num_retries must be non-negative')

    def _validate_runtime_config(self, runtime: str) -> None:
        """Validate runtime configuration."""
        valid_runtimes = [
            'docker',
            'local',
            'remote',
            'e2b',
            'modal',
            'kubernetes',
            'cli',
        ]
        if runtime not in valid_runtimes:
            self.errors.append(
                f'Invalid runtime: {runtime}. Must be one of: {valid_runtimes}'
            )

        if runtime == 'local':
            self.warnings.append('Local runtime may have security implications')

    def _validate_new_runtime_config(
        self, runtime_config: dict[str, Any], main_config: dict[str, Any]
    ) -> None:
        """Validate new runtime_config structure."""
        if not runtime_config:
            return

        # Validate environment
        environment = runtime_config.get('environment', 'docker')
        valid_runtimes = [
            'docker',
            'local',
            'remote',
            'e2b',
            'modal',
            'kubernetes',
            'cli',
        ]
        if environment not in valid_runtimes:
            self.errors.append(
                f'Invalid runtime environment: {environment}. Must be one of: {valid_runtimes}'
            )

        # Validate local runtime configuration
        if environment == 'local':
            self.warnings.append(
                'Local runtime has security implications - no sandboxing is provided'
            )
            local_config = runtime_config.get('local', {})
            self._validate_local_runtime_config(local_config, main_config)

    def _validate_local_runtime_config(
        self, local_config: dict[str, Any], main_config: dict[str, Any]
    ) -> None:
        """Validate local runtime specific configuration."""
        import os
        from pathlib import Path

        # Validate project root
        project_root = local_config.get('project_root') or main_config.get(
            'workspace_base'
        )
        if project_root:
            try:
                project_root_path = Path(project_root).expanduser().resolve()

                if not project_root_path.exists():
                    self.errors.append(
                        f'Local runtime project_root does not exist: {project_root_path}'
                    )
                elif not project_root_path.is_dir():
                    self.errors.append(
                        f'Local runtime project_root is not a directory: {project_root_path}'
                    )
                else:
                    # Check permissions
                    if not os.access(project_root_path, os.R_OK):
                        self.errors.append(
                            f'Local runtime project_root is not readable: {project_root_path}'
                        )
                    if not os.access(project_root_path, os.W_OK):
                        self.errors.append(
                            f'Local runtime project_root is not writable: {project_root_path}'
                        )
            except Exception as e:
                self.errors.append(f'Error validating project_root: {e}')
        else:
            self.warnings.append(
                'No project_root specified for local runtime - will use temporary directory'
            )

        # Validate path mapping
        mount_host_prefix = local_config.get('mount_host_prefix')
        mount_container_prefix = local_config.get('mount_container_prefix')

        if mount_host_prefix and not mount_container_prefix:
            self.errors.append(
                'mount_host_prefix specified without mount_container_prefix'
            )
        elif mount_container_prefix and not mount_host_prefix:
            self.errors.append(
                'mount_container_prefix specified without mount_host_prefix'
            )
        elif mount_host_prefix and mount_container_prefix:
            if not os.path.isabs(mount_host_prefix):
                self.errors.append(
                    f'mount_host_prefix must be absolute path: {mount_host_prefix}'
                )
            if not os.path.isabs(mount_container_prefix):
                self.errors.append(
                    f'mount_container_prefix must be absolute path: {mount_container_prefix}'
                )

    def _validate_sandbox_config(self, sandbox_config: dict[str, Any]) -> None:
        """Validate sandbox configuration."""
        if not sandbox_config:
            return

        # Validate container images
        base_image = sandbox_config.get('base_container_image')
        if base_image and not self._is_valid_docker_image(base_image):
            self.warnings.append(f'Invalid Docker image format: {base_image}')

        runtime_image = sandbox_config.get('runtime_container_image')
        if runtime_image and not self._is_valid_docker_image(runtime_image):
            self.warnings.append(f'Invalid Docker image format: {runtime_image}')

        # Validate platform
        platform = sandbox_config.get('platform')
        if platform:
            valid_platforms = ['linux/amd64', 'linux/arm64', 'linux/arm/v7']
            if platform not in valid_platforms:
                self.warnings.append(f'Uncommon platform: {platform}')

    def _validate_agent_config(self, agents_config: dict[str, Any]) -> None:
        """Validate agent configuration."""
        if not agents_config:
            return

        for agent_name, agent_config in agents_config.items():
            if not isinstance(agent_config, dict):
                continue

            # Validate memory settings
            memory_config = agent_config.get('memory', {})
            if memory_config:
                max_threads = memory_config.get('max_threads')
                if max_threads is not None and max_threads <= 0:
                    self.errors.append(
                        f'Agent {agent_name}: max_threads must be positive'
                    )

                condenser_config = memory_config.get('condenser', {})
                if condenser_config:
                    condenser_type = condenser_config.get('type')
                    if condenser_type and condenser_type not in [
                        'truncation',
                        'summary',
                    ]:
                        self.warnings.append(
                            f'Agent {agent_name}: unknown condenser type: {condenser_type}'
                        )

    def _validate_security_config(self, security_config: dict[str, Any]) -> None:
        """Validate security configuration."""
        if not security_config:
            return

        sandbox_mode = security_config.get('sandbox_mode')
        if sandbox_mode not in ['strict', 'permissive', 'disabled']:
            self.errors.append(
                'Security sandbox_mode must be: strict, permissive, or disabled'
            )

        if sandbox_mode == 'disabled':
            self.warnings.append('Security sandbox is disabled - this may be unsafe')

    def _validate_file_paths(self, config_data: dict[str, Any]) -> None:
        """Validate file paths in configuration."""

        def check_path(path: str, description: str) -> None:
            if path and not os.path.exists(path):
                self.warnings.append(f'{description} path does not exist: {path}')

        # Check runtime paths
        runtime_config = config_data.get('runtime', {})
        if isinstance(runtime_config, dict):
            local_config = runtime_config.get('local', {})
            if local_config:
                project_root = local_config.get('project_root')
                if project_root:
                    check_path(project_root, 'Runtime project root')

    def _validate_deprecated_keys(self, config_data: dict[str, Any]) -> None:
        """Check for deprecated configuration keys."""
        deprecated_keys = {
            'llm_config': 'Use llms.llm instead',
            'agent_config': 'Use agents.default instead',
            'max_iterations': 'Use agents.default.max_iterations instead',
        }

        def check_deprecated(data: dict[str, Any], prefix: str = '') -> None:
            for key, value in data.items():
                full_key = f'{prefix}.{key}' if prefix else key

                if key in deprecated_keys:
                    self.warnings.append(
                        f'Deprecated key "{full_key}": {deprecated_keys[key]}'
                    )

                if isinstance(value, dict):
                    check_deprecated(value, full_key)

        check_deprecated(config_data)

    def _is_valid_docker_image(self, image: str) -> bool:
        """Check if a Docker image name is valid."""
        # Basic Docker image name validation
        pattern = r'^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[a-zA-Z0-9._-]+)?$'
        return bool(re.match(pattern, image.lower()))


class ConfigDiagnostics:
    """Configuration diagnostics and health checks."""

    def __init__(self, config_loader):
        self.loader = config_loader

    def run_diagnostics(self) -> dict[str, Any]:
        """Run comprehensive configuration diagnostics."""
        diagnostics = {
            'config_health': self._check_config_health(),
            'source_analysis': self._analyze_sources(),
            'key_analysis': self._analyze_keys(),
            'runtime_analysis': self._analyze_runtime(),
            'environment_analysis': self._analyze_environment(),
            'recommendations': self._generate_recommendations(),
        }

        return diagnostics

    def _check_config_health(self) -> dict[str, Any]:
        """Check overall configuration health."""
        try:
            config = self.loader.get_config()
            validator = ConfigValidator()
            is_valid, errors, warnings = validator.validate(config.model_dump())

            return {
                'status': 'healthy' if is_valid else 'unhealthy',
                'errors': errors,
                'warnings': warnings,
                'requires_restart': self.loader.requires_restart(),
            }
        except Exception as e:
            return {
                'status': 'error',
                'errors': [str(e)],
                'warnings': [],
                'requires_restart': False,
            }

    def _analyze_sources(self) -> dict[str, Any]:
        """Analyze configuration sources."""
        sources = self.loader.get_source_info()
        analysis = {}

        for name, info in sources.items():
            analysis[name] = {
                'loaded': info['loaded'],
                'keys_count': info['keys_count'],
                'path': info.get('path'),
                'status': 'active' if info['loaded'] else 'inactive',
            }

        return analysis

    def _analyze_keys(self) -> dict[str, Any]:
        """Analyze configuration keys."""
        config = self.loader.get_config()
        config_dict = config.model_dump()

        all_keys = set()

        def collect_keys(data: dict[str, Any], prefix: str = '') -> None:
            for key, value in data.items():
                full_key = f'{prefix}.{key}' if prefix else key
                all_keys.add(full_key)
                if isinstance(value, dict):
                    collect_keys(value, full_key)

        collect_keys(config_dict)

        cold_keys = [key for key in all_keys if self.loader.is_cold_key(key)]
        hot_keys = [key for key in all_keys if not self.loader.is_cold_key(key)]

        return {
            'total_keys': len(all_keys),
            'cold_keys': {
                'count': len(cold_keys),
                'keys': sorted(cold_keys),
            },
            'hot_keys': {
                'count': len(hot_keys),
                'keys': sorted(hot_keys),
            },
        }

    def _analyze_runtime(self) -> dict[str, Any]:
        """Analyze runtime configuration and status."""
        try:
            config = self.loader.get_config()

            # Get runtime name
            runtime_name = config.runtime
            if hasattr(config, 'runtime_config') and config.runtime_config:
                runtime_name = config.runtime_config.environment

            runtime_info = {
                'current_runtime': runtime_name,
                'legacy_runtime': config.runtime,
                'runtime_status': 'configured',
            }

            # Add local runtime specific information
            if (
                runtime_name == 'local'
                and hasattr(config, 'runtime_config')
                and config.runtime_config
            ):
                local_config = config.runtime_config.local
                project_root = local_config.get_project_root(config.workspace_base)

                runtime_info.update(
                    {
                        'project_root': str(project_root) if project_root else None,
                        'project_root_exists': project_root.exists()
                        if project_root
                        else False,
                        'path_mapping_enabled': bool(
                            local_config.mount_host_prefix
                            and local_config.mount_container_prefix
                        ),
                        'mount_host_prefix': local_config.mount_host_prefix,
                        'mount_container_prefix': local_config.mount_container_prefix,
                    }
                )

                # Check permissions if project root exists
                if project_root and project_root.exists():
                    import os

                    runtime_info.update(
                        {
                            'project_root_readable': os.access(project_root, os.R_OK),
                            'project_root_writable': os.access(project_root, os.W_OK),
                        }
                    )
                else:
                    runtime_info.update(
                        {
                            'project_root_readable': False,
                            'project_root_writable': False,
                        }
                    )

            return runtime_info

        except Exception as e:
            return {
                'current_runtime': 'unknown',
                'runtime_status': 'error',
                'error': str(e),
            }

    def _analyze_environment(self) -> dict[str, Any]:
        """Analyze environment configuration."""
        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith('OPENHANDS_'):
                config_key = key[10:].lower()  # Remove OPENHANDS_ prefix
                env_vars[config_key] = value

        return {
            'openhands_env_vars': env_vars,
            'env_overrides': self.loader._env_overrides,
            'cli_overrides': self.loader._cli_overrides,
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate configuration recommendations."""
        recommendations = []

        try:
            config = self.loader.get_config()
            config_dict = config.model_dump()

            # Check for missing API keys
            llms_config = config_dict.get('llms', {})
            llm_config = llms_config.get('llm', {})
            if llm_config:
                api_key = llm_config.get('api_key', '')
                base_url = llm_config.get('base_url', '')
                model = llm_config.get('model', '')

                if not api_key and not base_url and model:
                    if any(
                        provider in model.lower()
                        for provider in ['openai', 'gpt', 'anthropic', 'claude']
                    ):
                        recommendations.append(
                            'Consider setting an API key for your LLM model'
                        )

            # Check runtime configuration
            runtime = config_dict.get('runtime', 'docker')
            if runtime == 'local':
                recommendations.append(
                    'Local runtime is less secure - consider using Docker runtime'
                )

            # Check security settings
            security_config = config_dict.get('security', {})
            if security_config.get('sandbox_mode') == 'disabled':
                recommendations.append(
                    'Security sandbox is disabled - enable for better security'
                )

            # Check for restart requirements
            if self.loader.requires_restart():
                recommendations.append(
                    'Configuration changes require restart to take effect'
                )

            # Check for environment overrides
            if self.loader._env_overrides:
                recommendations.append(
                    'Environment variables are overriding configuration - ensure this is intentional'
                )

        except Exception as e:
            logger.openhands_logger.warning(f'Error generating recommendations: {e}')

        return recommendations
