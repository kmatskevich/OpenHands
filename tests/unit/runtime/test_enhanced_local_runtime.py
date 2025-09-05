"""Tests for enhanced local runtime."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from openhands.core.config import OpenHandsConfig
from openhands.core.config.runtime_config import LocalRuntimeConfig, RuntimeConfig
from openhands.runtime.impl.local.enhanced_local_runtime import EnhancedLocalRuntime


class TestEnhancedLocalRuntime:
    """Test enhanced local runtime functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_stream = Mock()
        self.mock_llm_registry = Mock()

    def test_get_local_config_new_format(self):
        """Test local config extraction from new format."""
        local_config = LocalRuntimeConfig(project_root='/test/path')
        runtime_config = RuntimeConfig(environment='local', local=local_config)
        config = OpenHandsConfig(runtime_config=runtime_config)

        with (
            patch.object(EnhancedLocalRuntime, '_validate_configuration'),
            patch.object(EnhancedLocalRuntime, '_setup_workspace'),
            patch.object(EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None),
        ):
            runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
            extracted_config = runtime._get_local_config(config)

            assert extracted_config.project_root == '/test/path'

    def test_get_local_config_legacy_format(self):
        """Test local config extraction from legacy format."""
        config = OpenHandsConfig(runtime='local')

        with (
            patch.object(EnhancedLocalRuntime, '_validate_configuration'),
            patch.object(EnhancedLocalRuntime, '_setup_workspace'),
            patch.object(EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None),
        ):
            runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
            extracted_config = runtime._get_local_config(config)

            assert isinstance(extracted_config, LocalRuntimeConfig)
            assert extracted_config.project_root is None

    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            runtime_config = RuntimeConfig(environment='local', local=local_config)
            config = OpenHandsConfig(runtime_config=runtime_config)

            with (
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config

                # Should not raise exception
                runtime._validate_configuration(config)

    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        local_config = LocalRuntimeConfig(project_root='/nonexistent/path')
        runtime_config = RuntimeConfig(environment='local', local=local_config)
        config = OpenHandsConfig(runtime_config=runtime_config)

        with (
            patch.object(EnhancedLocalRuntime, '_setup_workspace'),
            patch.object(EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None),
        ):
            runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
            runtime.local_config = local_config

            with pytest.raises(ValueError, match='validation failed'):
                runtime._validate_configuration(config)

    def test_setup_workspace_with_project_root(self):
        """Test workspace setup with configured project root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.sid = 'test'

                runtime._setup_workspace(config)

                assert config.workspace_mount_path_in_sandbox == temp_dir

    def test_setup_workspace_without_project_root(self):
        """Test workspace setup without configured project root."""
        local_config = LocalRuntimeConfig()
        config = OpenHandsConfig()

        with (
            patch.object(EnhancedLocalRuntime, '_validate_configuration'),
            patch.object(EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None),
            patch(
                'tempfile.mkdtemp', return_value='/tmp/test_workspace'
            ) as mock_mkdtemp,
        ):
            runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
            runtime.local_config = local_config
            runtime.sid = 'test'

            runtime._setup_workspace(config)

            assert config.workspace_mount_path_in_sandbox == '/tmp/test_workspace'
            mock_mkdtemp.assert_called_once()

    def test_get_project_root(self):
        """Test project root retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                project_root = runtime.get_project_root()

                assert project_root == Path(temp_dir).resolve()

    def test_resolve_path_without_mapping(self):
        """Test path resolution without path mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                test_path = os.path.join(temp_dir, 'test.txt')
                resolved_path = runtime.resolve_path(test_path)

                assert resolved_path == str(Path(test_path).resolve())

    def test_resolve_path_with_mapping(self):
        """Test path resolution with path mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(
                project_root=temp_dir,
                mount_host_prefix='/host',
                mount_container_prefix='/container',
            )
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                # Test path under mounted prefix
                host_path = '/host/subdir/file.txt'
                resolved_path = runtime.resolve_path(host_path)

                expected_path = str(Path('/container/subdir/file.txt').resolve())
                assert resolved_path == expected_path

    def test_resolve_path_mapping_failure(self):
        """Test path resolution failure with invalid mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(
                project_root=temp_dir,
                mount_host_prefix='/host',
                mount_container_prefix='/container',
            )
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                # Test path outside mounted prefix
                invalid_path = '/other/path/file.txt'

                with pytest.raises(ValueError, match='Path resolution failed'):
                    runtime.resolve_path(invalid_path)

    def test_read_file_success(self):
        """Test successful file reading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, 'test.txt')
            test_content = 'Hello, World!'
            with open(test_file, 'w') as f:
                f.write(test_content)

            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                content = runtime.read_file(test_file)
                assert content == test_content

    def test_read_file_not_found(self):
        """Test file reading with non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                nonexistent_file = os.path.join(temp_dir, 'nonexistent.txt')

                with pytest.raises(FileNotFoundError):
                    runtime.read_file(nonexistent_file)

    def test_write_file_success(self):
        """Test successful file writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                test_file = os.path.join(temp_dir, 'test.txt')
                test_content = 'Hello, World!'

                runtime.write_file(test_file, test_content)

                # Verify file was written
                with open(test_file, 'r') as f:
                    assert f.read() == test_content

    def test_write_file_create_directories(self):
        """Test file writing with directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                # File in nested directory that doesn't exist
                test_file = os.path.join(temp_dir, 'subdir', 'nested', 'test.txt')
                test_content = 'Hello, World!'

                runtime.write_file(test_file, test_content)

                # Verify file was written and directories created
                assert os.path.exists(test_file)
                with open(test_file, 'r') as f:
                    assert f.read() == test_content

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()
            config.sandbox.timeout = 30

            # Mock successful command result
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'command output'
            mock_result.stderr = ''
            mock_run.return_value = mock_result

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                exit_code, stdout, stderr = runtime.run_command('echo "test"')

                assert exit_code == 0
                assert stdout == 'command output'
                assert stderr == ''

                mock_run.assert_called_once_with(
                    'echo "test"',
                    shell=True,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

    @patch('subprocess.run')
    def test_run_command_with_cwd(self, mock_run):
        """Test command execution with custom working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()
            config.sandbox.timeout = 30

            # Mock successful command result
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'command output'
            mock_result.stderr = ''
            mock_run.return_value = mock_result

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                custom_cwd = os.path.join(temp_dir, 'subdir')
                os.makedirs(custom_cwd)

                runtime.run_command('echo "test"', cwd=custom_cwd)

                mock_run.assert_called_once_with(
                    'echo "test"',
                    shell=True,
                    cwd=custom_cwd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

    def test_get_runtime_info(self):
        """Test runtime information retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(
                project_root=temp_dir,
                mount_host_prefix='/host',
                mount_container_prefix='/container',
            )
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config
                runtime._user_id = 1000
                runtime._username = 'testuser'
                runtime.is_windows = False

                info = runtime.get_runtime_info()

                assert info['runtime_type'] == 'local'
                assert info['project_root'] == temp_dir
                assert info['project_root_exists'] is True
                assert info['project_root_readable'] is True
                assert info['project_root_writable'] is True
                assert info['path_mapping_enabled'] is True
                assert info['mount_host_prefix'] == '/host'
                assert info['mount_container_prefix'] == '/container'
                assert info['user_id'] == 1000
                assert info['username'] == 'testuser'
                assert info['is_windows'] is False

    def test_validate_path_access_success(self):
        """Test successful path access validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')

            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                is_valid, error_msg = runtime.validate_path_access(test_file)

                assert is_valid is True
                assert error_msg == ''

    def test_validate_path_access_nonexistent(self):
        """Test path access validation for non-existent path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config = LocalRuntimeConfig(project_root=temp_dir)
            config = OpenHandsConfig()

            with (
                patch.object(EnhancedLocalRuntime, '_validate_configuration'),
                patch.object(EnhancedLocalRuntime, '_setup_workspace'),
                patch.object(
                    EnhancedLocalRuntime, '__init__', lambda x, **kwargs: None
                ),
            ):
                runtime = EnhancedLocalRuntime.__new__(EnhancedLocalRuntime)
                runtime.local_config = local_config
                runtime.config = config

                nonexistent_file = os.path.join(temp_dir, 'nonexistent.txt')
                is_valid, error_msg = runtime.validate_path_access(nonexistent_file)

                assert is_valid is False
                assert 'does not exist' in error_msg
