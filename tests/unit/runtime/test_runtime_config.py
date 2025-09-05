"""Tests for runtime configuration models."""

import os
import tempfile
from pathlib import Path

import pytest

from openhands.core.config.runtime_config import LocalRuntimeConfig, RuntimeConfig


class TestLocalRuntimeConfig:
    """Test LocalRuntimeConfig functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LocalRuntimeConfig()

        assert config.project_root is None
        assert config.mount_host_prefix is None
        assert config.mount_container_prefix is None

    def test_path_mapping_validation_success(self):
        """Test successful path mapping validation."""
        config = LocalRuntimeConfig(
            mount_host_prefix='/host/path', mount_container_prefix='/container/path'
        )

        # Should not raise exception
        assert config.mount_host_prefix == '/host/path'
        assert config.mount_container_prefix == '/container/path'

    def test_path_mapping_validation_missing_container_prefix(self):
        """Test path mapping validation with missing container prefix."""
        with pytest.raises(
            ValueError,
            match='mount_host_prefix specified without mount_container_prefix',
        ):
            LocalRuntimeConfig(mount_host_prefix='/host/path')

    def test_path_mapping_validation_missing_host_prefix(self):
        """Test path mapping validation with missing host prefix."""
        with pytest.raises(
            ValueError,
            match='mount_container_prefix specified without mount_host_prefix',
        ):
            LocalRuntimeConfig(mount_container_prefix='/container/path')

    def test_path_mapping_validation_relative_host_prefix(self):
        """Test path mapping validation with relative host prefix."""
        with pytest.raises(ValueError, match='mount_host_prefix must be absolute path'):
            LocalRuntimeConfig(
                mount_host_prefix='relative/path',
                mount_container_prefix='/container/path',
            )

    def test_path_mapping_validation_relative_container_prefix(self):
        """Test path mapping validation with relative container prefix."""
        with pytest.raises(
            ValueError, match='mount_container_prefix must be absolute path'
        ):
            LocalRuntimeConfig(
                mount_host_prefix='/host/path', mount_container_prefix='relative/path'
            )

    def test_get_project_root_with_config(self):
        """Test project root retrieval with configured path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LocalRuntimeConfig(project_root=temp_dir)

            project_root = config.get_project_root()

            assert project_root == Path(temp_dir).resolve()

    def test_get_project_root_with_fallback(self):
        """Test project root retrieval with workspace_base fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LocalRuntimeConfig()  # No project_root specified

            project_root = config.get_project_root(workspace_base=temp_dir)

            assert project_root == Path(temp_dir).resolve()

    def test_get_project_root_none(self):
        """Test project root retrieval with no configuration."""
        config = LocalRuntimeConfig()

        project_root = config.get_project_root()

        assert project_root is None

    def test_validate_project_root_success(self):
        """Test successful project root validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LocalRuntimeConfig(project_root=temp_dir)

            is_valid, errors = config.validate_project_root()

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_project_root_nonexistent(self):
        """Test project root validation with non-existent path."""
        config = LocalRuntimeConfig(project_root='/nonexistent/path')

        is_valid, errors = config.validate_project_root()

        assert is_valid is False
        assert len(errors) == 1
        assert 'does not exist' in errors[0]

    def test_validate_project_root_not_directory(self):
        """Test project root validation with file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            config = LocalRuntimeConfig(project_root=temp_file.name)

            is_valid, errors = config.validate_project_root()

            assert is_valid is False
            assert len(errors) == 1
            assert 'not a directory' in errors[0]

    def test_validate_project_root_no_config(self):
        """Test project root validation with no configuration."""
        config = LocalRuntimeConfig()

        is_valid, errors = config.validate_project_root()

        assert is_valid is False
        assert len(errors) == 1
        assert 'No project_root specified' in errors[0]

    def test_validate_project_root_with_fallback(self):
        """Test project root validation with workspace_base fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LocalRuntimeConfig()  # No project_root specified

            is_valid, errors = config.validate_project_root(workspace_base=temp_dir)

            assert is_valid is True
            assert len(errors) == 0

    def test_map_path_no_mapping(self):
        """Test path mapping without configuration."""
        config = LocalRuntimeConfig()

        original_path = '/some/path/file.txt'
        mapped_path = config.map_path(original_path)

        assert mapped_path == original_path

    def test_map_path_with_mapping(self):
        """Test path mapping with configuration."""
        config = LocalRuntimeConfig(
            mount_host_prefix='/host', mount_container_prefix='/container'
        )

        host_path = '/host/subdir/file.txt'
        mapped_path = config.map_path(host_path)

        expected_path = os.path.normpath('/container/subdir/file.txt')
        assert mapped_path == expected_path

    def test_map_path_outside_prefix(self):
        """Test path mapping with path outside mounted prefix."""
        config = LocalRuntimeConfig(
            mount_host_prefix='/host', mount_container_prefix='/container'
        )

        outside_path = '/other/path/file.txt'

        with pytest.raises(ValueError, match='not under mounted prefix'):
            config.map_path(outside_path)

    def test_map_path_nested_prefix(self):
        """Test path mapping with nested paths."""
        config = LocalRuntimeConfig(
            mount_host_prefix='/host/workspace',
            mount_container_prefix='/container/workspace',
        )

        host_path = '/host/workspace/project/src/file.py'
        mapped_path = config.map_path(host_path)

        expected_path = os.path.normpath('/container/workspace/project/src/file.py')
        assert mapped_path == expected_path


class TestRuntimeConfig:
    """Test RuntimeConfig functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RuntimeConfig()

        assert config.environment == 'docker'
        assert isinstance(config.local, LocalRuntimeConfig)

    def test_custom_environment(self):
        """Test custom environment configuration."""
        config = RuntimeConfig(environment='local')

        assert config.environment == 'local'

    def test_custom_local_config(self):
        """Test custom local configuration."""
        local_config = LocalRuntimeConfig(project_root='/test/path')
        config = RuntimeConfig(environment='local', local=local_config)

        assert config.environment == 'local'
        assert config.local.project_root == '/test/path'

    def test_from_dict_string(self):
        """Test creation from string (legacy format)."""
        config = RuntimeConfig.from_dict('local')

        assert config.environment == 'local'
        assert isinstance(config.local, LocalRuntimeConfig)

    def test_from_dict_object(self):
        """Test creation from dictionary."""
        data = {
            'environment': 'local',
            'local': {
                'project_root': '/test/path',
                'mount_host_prefix': '/host',
                'mount_container_prefix': '/container',
            },
        }

        config = RuntimeConfig.from_dict(data)

        assert config.environment == 'local'
        assert config.local.project_root == '/test/path'
        assert config.local.mount_host_prefix == '/host'
        assert config.local.mount_container_prefix == '/container'

    def test_to_dict(self):
        """Test conversion to dictionary."""
        local_config = LocalRuntimeConfig(
            project_root='/test/path',
            mount_host_prefix='/host',
            mount_container_prefix='/container',
        )
        config = RuntimeConfig(environment='local', local=local_config)

        data = config.to_dict()

        assert data['environment'] == 'local'
        assert data['local']['project_root'] == '/test/path'
        assert data['local']['mount_host_prefix'] == '/host'
        assert data['local']['mount_container_prefix'] == '/container'

    def test_is_local_runtime(self):
        """Test local runtime detection."""
        local_config = RuntimeConfig(environment='local')
        docker_config = RuntimeConfig(environment='docker')

        assert local_config.is_local_runtime() is True
        assert docker_config.is_local_runtime() is False

    def test_validate_for_environment_valid(self):
        """Test validation for valid environment."""
        config = RuntimeConfig(environment='docker')

        is_valid, errors = config.validate_for_environment()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_for_environment_invalid(self):
        """Test validation for invalid environment."""
        config = RuntimeConfig(environment='invalid_runtime')

        is_valid, errors = config.validate_for_environment()

        assert is_valid is False
        assert len(errors) == 1
        assert 'Invalid runtime environment' in errors[0]

    def test_validate_for_environment_local_valid(self):
        """Test validation for valid local environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = RuntimeConfig(environment='local', local=local_config)

            is_valid, errors = config.validate_for_environment()

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_for_environment_local_invalid(self):
        """Test validation for invalid local environment."""
        local_config = LocalRuntimeConfig(project_root='/nonexistent/path')
        config = RuntimeConfig(environment='local', local=local_config)

        is_valid, errors = config.validate_for_environment()

        assert is_valid is False
        assert len(errors) >= 1
        assert any('does not exist' in error for error in errors)

    def test_validate_for_environment_with_workspace_base(self):
        """Test validation with workspace_base fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig()  # No project_root specified
            config = RuntimeConfig(environment='local', local=local_config)

            is_valid, errors = config.validate_for_environment(workspace_base=temp_dir)

            assert is_valid is True
            assert len(errors) == 0


class TestRuntimeConfigIntegration:
    """Integration tests for runtime configuration."""

    def test_full_local_configuration(self):
        """Test complete local runtime configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(
                project_root=temp_dir,
                mount_host_prefix='/host/workspace',
                mount_container_prefix='/container/workspace',
            )
            config = RuntimeConfig(environment='local', local=local_config)

            # Test all functionality
            assert config.is_local_runtime() is True

            project_root = config.local.get_project_root()
            assert project_root == Path(temp_dir).resolve()

            is_valid, errors = config.validate_for_environment()
            assert is_valid is True
            assert len(errors) == 0

            # Test path mapping
            host_path = '/host/workspace/project/file.py'
            mapped_path = config.local.map_path(host_path)
            expected_path = os.path.normpath('/container/workspace/project/file.py')
            assert mapped_path == expected_path

            # Test serialization
            data = config.to_dict()
            restored_config = RuntimeConfig.from_dict(data)
            assert restored_config.environment == config.environment
            assert restored_config.local.project_root == config.local.project_root

    def test_permission_validation(self):
        """Test permission validation for project root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory with restricted permissions
            restricted_dir = os.path.join(temp_dir, 'restricted')
            os.makedirs(restricted_dir)

            # Remove write permissions (if not on Windows and not running as root)
            if os.name != 'nt' and os.getuid() != 0:
                os.chmod(restricted_dir, 0o444)  # Read-only

                try:
                    local_config = LocalRuntimeConfig(project_root=restricted_dir)
                    is_valid, errors = local_config.validate_project_root()

                    assert is_valid is False
                    assert any('not writable' in error for error in errors)
                finally:
                    # Restore permissions for cleanup
                    os.chmod(restricted_dir, 0o755)
            else:
                # Skip permission test if running as root or on Windows
                pytest.skip(
                    'Permission test skipped when running as root or on Windows'
                )

    def test_expanduser_in_paths(self):
        """Test that paths with ~ are properly expanded."""
        # Use a path with ~ that should expand
        home_path = '~/test_project'
        local_config = LocalRuntimeConfig(project_root=home_path)

        project_root = local_config.get_project_root()

        # Should expand ~ to actual home directory
        assert project_root == Path(home_path).expanduser().resolve()
        assert '~' not in str(project_root)
