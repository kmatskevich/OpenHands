"""Tests for runtime factory."""

import tempfile
from unittest.mock import Mock, patch

import pytest

from openhands.core.config import OpenHandsConfig
from openhands.core.config.runtime_config import LocalRuntimeConfig, RuntimeConfig
from openhands.runtime.factory import RuntimeFactory, get_runtime_factory


class TestRuntimeFactory:
    """Test runtime factory functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RuntimeFactory()
        self.factory.clear_cache()  # Clear any cached state

        # Mock dependencies
        self.mock_event_stream = Mock()
        self.mock_llm_registry = Mock()

    def test_singleton_pattern(self):
        """Test that RuntimeFactory follows singleton pattern."""
        factory1 = RuntimeFactory()
        factory2 = RuntimeFactory()
        factory3 = get_runtime_factory()

        assert factory1 is factory2
        assert factory2 is factory3

    def test_get_runtime_name_legacy(self):
        """Test runtime name extraction from legacy configuration."""
        config = OpenHandsConfig(runtime='docker')

        runtime_name = self.factory._get_runtime_name(config)
        assert runtime_name == 'docker'

    def test_get_runtime_name_new_format(self):
        """Test runtime name extraction from new configuration format."""
        runtime_config = RuntimeConfig(environment='local')
        config = OpenHandsConfig(runtime='docker', runtime_config=runtime_config)

        runtime_name = self.factory._get_runtime_name(config)
        assert runtime_name == 'local'  # Should use new format

    def test_validate_runtime_config_valid(self):
        """Test validation of valid runtime configuration."""
        config = OpenHandsConfig(runtime='docker')

        # Should not raise exception
        self.factory._validate_runtime_config(config)

    @patch('openhands.runtime.factory.get_runtime_cls')
    def test_validate_runtime_config_invalid(self, mock_get_runtime_cls):
        """Test validation of invalid runtime configuration."""
        mock_get_runtime_cls.side_effect = ValueError('Invalid runtime')
        config = OpenHandsConfig(runtime='invalid_runtime')

        with pytest.raises(ValueError, match='Invalid runtime configuration'):
            self.factory._validate_runtime_config(config)

    def test_validate_local_runtime_config_valid(self):
        """Test validation of valid local runtime configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            runtime_config = RuntimeConfig(environment='local', local=local_config)
            config = OpenHandsConfig(runtime_config=runtime_config)

            # Should not raise exception
            self.factory._validate_local_runtime_config(config)

    def test_validate_local_runtime_config_nonexistent_path(self):
        """Test validation of local runtime with non-existent path."""
        nonexistent_path = '/path/that/does/not/exist'
        local_config = LocalRuntimeConfig(project_root=nonexistent_path)
        runtime_config = RuntimeConfig(environment='local', local=local_config)
        config = OpenHandsConfig(runtime_config=runtime_config)

        with pytest.raises(ValueError, match='does not exist'):
            self.factory._validate_local_runtime_config(config)

    def test_validate_local_runtime_config_invalid_path_mapping(self):
        """Test validation of invalid path mapping configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Only host prefix specified - this should fail during LocalRuntimeConfig creation
            with pytest.raises(
                ValueError,
                match='mount_host_prefix specified without mount_container_prefix',
            ):
                LocalRuntimeConfig(
                    project_root=temp_dir, mount_host_prefix='/host/path'
                )

    def test_validate_local_runtime_config_relative_path_mapping(self):
        """Test validation of relative path mapping configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Relative path should fail during LocalRuntimeConfig creation
            with pytest.raises(ValueError, match='must be absolute path'):
                LocalRuntimeConfig(
                    project_root=temp_dir,
                    mount_host_prefix='relative/path',  # Not absolute
                    mount_container_prefix='/container/path',
                )

    def test_calculate_cold_config_hash_consistency(self):
        """Test that cold config hash is consistent for same configuration."""
        config = OpenHandsConfig(runtime='docker')

        hash1 = self.factory._calculate_cold_config_hash(config)
        hash2 = self.factory._calculate_cold_config_hash(config)

        assert hash1 == hash2

    def test_calculate_cold_config_hash_different_configs(self):
        """Test that different configurations produce different hashes."""
        config1 = OpenHandsConfig(runtime='docker')
        config2 = OpenHandsConfig(runtime='docker', workspace_base='/different/path')

        hash1 = self.factory._calculate_cold_config_hash(config1)
        hash2 = self.factory._calculate_cold_config_hash(config2)

        assert hash1 != hash2

    @patch('openhands.runtime.factory.get_runtime_cls')
    def test_create_runtime_success(self, mock_get_runtime_cls):
        """Test successful runtime creation."""
        # Mock runtime class
        mock_runtime_cls = Mock()
        mock_runtime_instance = Mock()
        mock_runtime_cls.return_value = mock_runtime_instance
        mock_get_runtime_cls.return_value = mock_runtime_cls

        config = OpenHandsConfig(runtime='docker')

        runtime = self.factory.create_runtime(
            config=config,
            event_stream=self.mock_event_stream,
            llm_registry=self.mock_llm_registry,
            sid='test_session',
        )

        assert runtime is mock_runtime_instance
        # get_runtime_cls is called twice: once for validation, once for creation
        assert mock_get_runtime_cls.call_count == 2
        mock_runtime_cls.assert_called_once()

    @patch('openhands.runtime.factory.get_runtime_cls')
    def test_create_runtime_failure(self, mock_get_runtime_cls):
        """Test runtime creation failure."""
        mock_get_runtime_cls.side_effect = ValueError('Invalid runtime')

        config = OpenHandsConfig(runtime='invalid')

        with pytest.raises(ValueError, match='Invalid runtime configuration'):
            self.factory.create_runtime(
                config=config,
                event_stream=self.mock_event_stream,
                llm_registry=self.mock_llm_registry,
                sid='test_session',
            )

    @patch('openhands.runtime.factory.get_runtime_cls')
    def test_get_or_create_runtime_caching(self, mock_get_runtime_cls):
        """Test runtime caching behavior."""
        # Mock runtime class
        mock_runtime_cls = Mock()
        mock_runtime_instance = Mock()
        mock_runtime_instance.sid = 'test_session'
        mock_runtime_cls.return_value = mock_runtime_instance
        mock_get_runtime_cls.return_value = mock_runtime_cls

        config = OpenHandsConfig(runtime='docker')

        # First call should create runtime
        runtime1 = self.factory.get_or_create_runtime(
            config=config,
            event_stream=self.mock_event_stream,
            llm_registry=self.mock_llm_registry,
            sid='test_session',
        )

        # Second call with same config should return cached runtime
        runtime2 = self.factory.get_or_create_runtime(
            config=config,
            event_stream=self.mock_event_stream,
            llm_registry=self.mock_llm_registry,
            sid='test_session',
        )

        assert runtime1 is runtime2
        assert mock_runtime_cls.call_count == 1  # Only called once

    @patch('openhands.runtime.factory.get_runtime_cls')
    def test_get_or_create_runtime_config_change(self, mock_get_runtime_cls):
        """Test runtime recreation when configuration changes."""
        # Mock runtime class
        mock_runtime_cls = Mock()
        mock_runtime_instance1 = Mock()
        mock_runtime_instance1.sid = 'test_session'
        mock_runtime_instance2 = Mock()
        mock_runtime_instance2.sid = 'test_session'
        mock_runtime_cls.side_effect = [mock_runtime_instance1, mock_runtime_instance2]
        mock_get_runtime_cls.return_value = mock_runtime_cls

        config1 = OpenHandsConfig(runtime='docker')
        config2 = OpenHandsConfig(runtime='docker', workspace_base='/different/path')

        # First call
        runtime1 = self.factory.get_or_create_runtime(
            config=config1,
            event_stream=self.mock_event_stream,
            llm_registry=self.mock_llm_registry,
            sid='test_session',
        )

        # Second call with different config should create new runtime
        runtime2 = self.factory.get_or_create_runtime(
            config=config2,
            event_stream=self.mock_event_stream,
            llm_registry=self.mock_llm_registry,
            sid='test_session',
        )

        assert runtime1 is not runtime2
        assert mock_runtime_cls.call_count == 2  # Called twice

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Set up cached runtime
        self.factory._current_runtime = Mock()
        self.factory._current_config_hash = 'test_hash'

        # Clear cache
        self.factory.clear_cache()

        assert self.factory._current_runtime is None
        assert self.factory._current_config_hash is None


class TestRuntimeFactoryIntegration:
    """Integration tests for runtime factory."""

    def test_local_runtime_with_temp_directory(self):
        """Test local runtime configuration with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            runtime_config = RuntimeConfig(environment='local', local=local_config)
            config = OpenHandsConfig(runtime_config=runtime_config)

            factory = RuntimeFactory()

            # Should validate successfully
            factory._validate_runtime_config(config)

            # Should get correct runtime name
            runtime_name = factory._get_runtime_name(config)
            assert runtime_name == 'local'

    def test_path_mapping_validation(self):
        """Test path mapping validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(
                project_root=temp_dir,
                mount_host_prefix='/host/path',
                mount_container_prefix='/container/path',
            )
            runtime_config = RuntimeConfig(environment='local', local=local_config)
            config = OpenHandsConfig(runtime_config=runtime_config)

            factory = RuntimeFactory()

            # Should validate successfully
            factory._validate_runtime_config(config)

    def test_workspace_base_fallback(self):
        """Test fallback to workspace_base when project_root not specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig()  # No project_root specified
            runtime_config = RuntimeConfig(environment='local', local=local_config)
            config = OpenHandsConfig(
                runtime_config=runtime_config, workspace_base=temp_dir
            )

            factory = RuntimeFactory()

            # Should validate successfully using workspace_base
            factory._validate_runtime_config(config)
