"""Tests for configuration CLI commands."""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import toml
import yaml

from openhands.cli.config_commands import (
    handle_config_diagnostics,
    handle_config_get,
    handle_config_reset,
    handle_config_set,
    handle_config_show,
    handle_config_validate,
)


@pytest.fixture
def temp_config_file():
    """Fixture for temporary config file."""
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / 'config.toml'

    # Create initial config
    initial_config = {
        'runtime': 'docker',
        'llms': {'llm': {'model': 'gpt-4', 'temperature': 0.7}},
    }

    with open(config_path, 'w') as f:
        toml.dump(initial_config, f)

    yield str(config_path)

    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


class MockArgs:
    """Mock arguments class for testing CLI commands."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestConfigShow:
    """Test cases for config show command."""

    @patch('openhands.cli.config_commands.get_config')
    @patch('openhands.cli.config_commands.get_config_loader')
    def test_show_default_format(self, mock_get_loader, mock_get_config):
        """Test config show with default JSON format."""
        # Mock config
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {
            'runtime': 'docker',
            'llms': {'llm': {'model': 'gpt-4'}},
        }
        mock_get_config.return_value = mock_config

        # Mock loader
        mock_loader = MagicMock()
        mock_loader.get_source_info.return_value = {
            'default': {'loaded': True, 'keys_count': 10}
        }
        mock_get_loader.return_value = mock_loader

        args = MockArgs(format='json', sources=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_show(args)
            output = mock_stdout.getvalue()

            # Should be valid JSON
            config_data = json.loads(output)
            assert 'runtime' in config_data
            assert config_data['runtime'] == 'docker'

    @patch('openhands.cli.config_commands.get_config')
    @patch('openhands.cli.config_commands.get_config_loader')
    def test_show_yaml_format(self, mock_get_loader, mock_get_config):
        """Test config show with YAML format."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {
            'runtime': 'docker',
            'llms': {'llm': {'model': 'gpt-4'}},
        }
        mock_get_config.return_value = mock_config

        mock_loader = MagicMock()
        mock_loader.get_source_info.return_value = {}
        mock_get_loader.return_value = mock_loader

        args = MockArgs(format='yaml', sources=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_show(args)
            output = mock_stdout.getvalue()

            # Should be valid YAML
            config_data = yaml.safe_load(output)
            assert 'runtime' in config_data
            assert config_data['runtime'] == 'docker'

    @patch('openhands.cli.config_commands.get_config')
    @patch('openhands.cli.config_commands.get_config_loader')
    def test_show_toml_format(self, mock_get_loader, mock_get_config):
        """Test config show with TOML format."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {
            'runtime': 'docker',
            'llms': {'llm': {'model': 'gpt-4'}},
        }
        mock_get_config.return_value = mock_config

        mock_loader = MagicMock()
        mock_loader.get_source_info.return_value = {}
        mock_get_loader.return_value = mock_loader

        args = MockArgs(format='toml', sources=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_show(args)
            output = mock_stdout.getvalue()

            # Should be valid TOML
            config_data = toml.loads(output)
            assert 'runtime' in config_data
            assert config_data['runtime'] == 'docker'

    @patch('openhands.cli.config_commands.get_config')
    @patch('openhands.cli.config_commands.get_config_loader')
    def test_show_with_sources(self, mock_get_loader, mock_get_config):
        """Test config show with source information."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {'runtime': 'docker'}
        mock_get_config.return_value = mock_config

        mock_loader = MagicMock()
        mock_loader.get_source_info.return_value = {
            'default': {'loaded': True, 'keys_count': 10, 'path': None},
            'user': {'loaded': True, 'keys_count': 2, 'path': '/path/to/config.toml'},
        }
        mock_get_loader.return_value = mock_loader

        args = MockArgs(format='json', sources=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_show(args)
            output = mock_stdout.getvalue()

            data = json.loads(output)
            assert 'config' in data
            assert 'sources' in data
            assert 'default' in data['sources']
            assert 'user' in data['sources']


class TestConfigGet:
    """Test cases for config get command."""

    @patch('openhands.cli.config_commands.get_config')
    def test_get_simple_key(self, mock_get_config):
        """Test getting a simple configuration key."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {'runtime': 'docker'}
        mock_get_config.return_value = mock_config

        args = MockArgs(key='runtime')

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_get(args)
            output = mock_stdout.getvalue().strip()
            assert output == 'docker'

    @patch('openhands.cli.config_commands.get_config')
    def test_get_nested_key(self, mock_get_config):
        """Test getting a nested configuration key."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {
            'llms': {'llm': {'model': 'gpt-4', 'temperature': 0.7}}
        }
        mock_get_config.return_value = mock_config

        args = MockArgs(key='llms.llm.model')

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_get(args)
            output = mock_stdout.getvalue().strip()
            assert output == 'gpt-4'

    @patch('openhands.cli.config_commands.get_config')
    def test_get_nonexistent_key(self, mock_get_config):
        """Test getting a non-existent configuration key."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {'runtime': 'docker'}
        mock_get_config.return_value = mock_config

        args = MockArgs(key='nonexistent.key')

        with patch('sys.stdout', new_callable=StringIO):
            with pytest.raises(SystemExit):
                handle_config_get(args)


class TestConfigSet:
    """Test cases for config set command."""

    @patch('openhands.cli.config_commands.get_config_loader')
    @patch('openhands.cli.config_commands.requires_restart')
    def test_set_hot_key(self, mock_requires_restart, mock_get_loader):
        """Test setting a hot configuration key."""
        mock_loader = MagicMock()
        mock_loader.is_cold_key.return_value = False
        mock_get_loader.return_value = mock_loader
        mock_requires_restart.return_value = False

        args = MockArgs(key='llms.llm.temperature', value='0.8')

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_set(args)
            output = mock_stdout.getvalue()

            assert 'Configuration updated' in output
            assert 'Changes applied immediately' in output
            mock_loader.update_config.assert_called_once_with(
                'llms.llm.temperature', 0.8
            )

    @patch('openhands.cli.config_commands.get_config_loader')
    @patch('openhands.cli.config_commands.requires_restart')
    def test_set_cold_key(self, mock_requires_restart, mock_get_loader):
        """Test setting a cold configuration key."""
        mock_loader = MagicMock()
        mock_loader.is_cold_key.return_value = True
        mock_get_loader.return_value = mock_loader
        mock_requires_restart.return_value = True

        args = MockArgs(key='runtime', value='local')

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_set(args)
            output = mock_stdout.getvalue()

            assert 'Configuration updated' in output
            assert 'Restart required' in output
            mock_loader.update_config.assert_called_once_with('runtime', 'local')

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_set_type_conversion(self, mock_get_loader):
        """Test automatic type conversion in config set."""
        mock_loader = MagicMock()
        mock_loader.is_cold_key.return_value = False
        mock_get_loader.return_value = mock_loader

        # Test float conversion
        args = MockArgs(key='llms.llm.temperature', value='0.8')
        handle_config_set(args)
        mock_loader.update_config.assert_called_with('llms.llm.temperature', 0.8)

        # Test int conversion
        args = MockArgs(key='llms.llm.num_retries', value='5')
        handle_config_set(args)
        mock_loader.update_config.assert_called_with('llms.llm.num_retries', 5)

        # Test boolean conversion
        args = MockArgs(key='agents.default.enable_browsing', value='true')
        handle_config_set(args)
        mock_loader.update_config.assert_called_with(
            'agents.default.enable_browsing', True
        )

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_set_update_error(self, mock_get_loader):
        """Test error handling in config set."""
        mock_loader = MagicMock()
        mock_loader.update_config.side_effect = Exception('Update failed')
        mock_get_loader.return_value = mock_loader

        args = MockArgs(key='runtime', value='local')

        with patch('sys.stdout', new_callable=StringIO):
            with pytest.raises(SystemExit):
                handle_config_set(args)


class TestConfigValidate:
    """Test cases for config validate command."""

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_validate_current_config_valid(self, mock_get_loader):
        """Test validating current configuration (valid)."""
        mock_loader = MagicMock()
        mock_loader.validate_config.return_value = (True, [], ['Some warning'])
        mock_get_loader.return_value = mock_loader

        args = MockArgs(file=None)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_validate(args)
            output = mock_stdout.getvalue()

            assert '✅ Current configuration is valid' in output
            assert 'Some warning' in output

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_validate_current_config_invalid(self, mock_get_loader):
        """Test validating current configuration (invalid)."""
        mock_loader = MagicMock()
        mock_loader.validate_config.return_value = (
            False,
            ['Error message'],
            ['Warning'],
        )
        mock_get_loader.return_value = mock_loader

        args = MockArgs(file=None)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit):
                handle_config_validate(args)
                output = mock_stdout.getvalue()
                assert '❌ Current configuration is invalid' in output
                assert 'Error message' in output

    def test_validate_file_toml(self, temp_config_file):
        """Test validating a TOML configuration file."""
        with patch(
            'openhands.cli.config_commands.get_config_loader'
        ) as mock_get_loader:
            mock_loader = MagicMock()
            mock_loader.validate_config.return_value = (True, [], [])
            mock_get_loader.return_value = mock_loader

            args = MockArgs(file=temp_config_file)

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                handle_config_validate(args)
                output = mock_stdout.getvalue()

                assert f'✅ Configuration file {temp_config_file} is valid' in output

    def test_validate_file_json(self):
        """Test validating a JSON configuration file."""
        temp_dir = tempfile.mkdtemp()
        json_file = Path(temp_dir) / 'config.json'

        config_data = {'runtime': 'docker', 'llms': {'llm': {'model': 'gpt-4'}}}

        with open(json_file, 'w') as f:
            json.dump(config_data, f)

        try:
            with patch(
                'openhands.cli.config_commands.get_config_loader'
            ) as mock_get_loader:
                mock_loader = MagicMock()
                mock_loader.validate_config.return_value = (True, [], [])
                mock_get_loader.return_value = mock_loader

                args = MockArgs(file=str(json_file))

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    handle_config_validate(args)
                    output = mock_stdout.getvalue()

                    assert f'✅ Configuration file {json_file} is valid' in output
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        args = MockArgs(file='/nonexistent/file.toml')

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit):
                handle_config_validate(args)
                output = mock_stdout.getvalue()
                assert 'File not found' in output

    def test_validate_unsupported_format(self):
        """Test validating a file with unsupported format."""
        temp_dir = tempfile.mkdtemp()
        unsupported_file = Path(temp_dir) / 'config.xml'

        with open(unsupported_file, 'w') as f:
            f.write('<config></config>')

        try:
            args = MockArgs(file=str(unsupported_file))

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit):
                    handle_config_validate(args)
                    output = mock_stdout.getvalue()
                    assert 'Unsupported file format' in output
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigDiagnostics:
    """Test cases for config diagnostics command."""

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_diagnostics_healthy_config(self, mock_get_loader):
        """Test diagnostics with healthy configuration."""
        mock_loader = MagicMock()
        mock_diagnostics = {
            'config_health': {
                'status': 'healthy',
                'errors': [],
                'warnings': [],
                'requires_restart': False,
            },
            'source_analysis': {
                'default': {'status': 'active', 'keys_count': 10, 'path': None},
                'user': {
                    'status': 'active',
                    'keys_count': 2,
                    'path': '/path/config.toml',
                },
            },
            'key_analysis': {
                'cold_keys': {'keys': ['runtime']},
                'hot_keys': {'keys': ['llms.llm.temperature']},
            },
            'environment_analysis': {
                'openhands_env_vars': {},
                'env_overrides': {},
                'cli_overrides': {},
            },
            'recommendations': [],
        }
        mock_loader.get_diagnostics.return_value = mock_diagnostics
        mock_get_loader.return_value = mock_loader

        args = MockArgs()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_diagnostics(args)
            output = mock_stdout.getvalue()

            assert 'Configuration Diagnostics' in output
            assert '✅ Healthy' in output
            assert 'runtime' in output

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_diagnostics_unhealthy_config(self, mock_get_loader):
        """Test diagnostics with unhealthy configuration."""
        mock_loader = MagicMock()
        mock_diagnostics = {
            'config_health': {
                'status': 'unhealthy',
                'errors': ['Configuration error'],
                'warnings': ['Configuration warning'],
                'requires_restart': True,
            },
            'source_analysis': {
                'default': {'status': 'active', 'keys_count': 10, 'path': None}
            },
            'key_analysis': {'cold_keys': {'keys': []}, 'hot_keys': {'keys': []}},
            'environment_analysis': {
                'openhands_env_vars': {'runtime': 'local'},
                'env_overrides': {'runtime': 'local'},
                'cli_overrides': {},
            },
            'recommendations': ['Fix the configuration error'],
        }
        mock_loader.get_diagnostics.return_value = mock_diagnostics
        mock_get_loader.return_value = mock_loader

        args = MockArgs()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            handle_config_diagnostics(args)
            output = mock_stdout.getvalue()

            assert '❌ Unhealthy' in output
            assert 'Configuration error' in output
            assert 'Configuration warning' in output
            assert 'Fix the configuration error' in output


class TestConfigReset:
    """Test cases for config reset command."""

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_reset_without_confirmation(self, mock_get_loader):
        """Test reset without confirmation flag."""
        args = MockArgs(confirm=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit):
                handle_config_reset(args)
                output = mock_stdout.getvalue()
                assert 'This will reset all configuration' in output

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_reset_with_confirmation(self, mock_get_loader):
        """Test reset with confirmation flag."""
        mock_loader = MagicMock()
        mock_loader.get_user_config_path_resolved.return_value = '/path/to/config.toml'
        mock_get_loader.return_value = mock_loader

        args = MockArgs(confirm=True)

        with patch('os.path.exists', return_value=True):
            with patch('shutil.copy2') as mock_copy:
                with patch('os.remove') as mock_remove:
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_reset(args)
                        output = mock_stdout.getvalue()

                        assert 'Configuration reset successfully' in output
                        mock_copy.assert_called_once()  # Backup created
                        mock_remove.assert_called_once()  # Config file removed

    @patch('openhands.cli.config_commands.get_config_loader')
    def test_reset_no_config_file(self, mock_get_loader):
        """Test reset when no config file exists."""
        mock_loader = MagicMock()
        mock_loader.get_user_config_path_resolved.return_value = '/path/to/config.toml'
        mock_get_loader.return_value = mock_loader

        args = MockArgs(confirm=True)

        with patch('os.path.exists', return_value=False):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                handle_config_reset(args)
                output = mock_stdout.getvalue()

                assert 'No user configuration file found' in output


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_cli_workflow(self, temp_config_file):
        """Test complete CLI workflow."""
        with patch(
            'openhands.cli.config_commands.get_config_loader'
        ) as mock_get_loader:
            # Mock loader
            mock_loader = MagicMock()
            mock_loader.get_user_config_path_resolved.return_value = temp_config_file
            mock_loader.is_cold_key.return_value = False
            mock_loader.validate_config.return_value = (True, [], [])
            mock_loader.get_diagnostics.return_value = {
                'config_health': {
                    'status': 'healthy',
                    'errors': [],
                    'warnings': [],
                    'requires_restart': False,
                },
                'source_analysis': {},
                'key_analysis': {'cold_keys': {'keys': []}, 'hot_keys': {'keys': []}},
                'environment_analysis': {
                    'openhands_env_vars': {},
                    'env_overrides': {},
                    'cli_overrides': {},
                },
                'recommendations': [],
            }
            mock_get_loader.return_value = mock_loader

            with patch('openhands.cli.config_commands.get_config') as mock_get_config:
                mock_config = MagicMock()
                mock_config.model_dump.return_value = {
                    'runtime': 'docker',
                    'llms': {'llm': {'model': 'gpt-4', 'temperature': 0.7}},
                }
                mock_get_config.return_value = mock_config

                with patch(
                    'openhands.cli.config_commands.requires_restart', return_value=False
                ):
                    # Test show command
                    args = MockArgs(format='json', sources=False)
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_show(args)
                        output = mock_stdout.getvalue()
                        config_data = json.loads(output)
                        assert config_data['runtime'] == 'docker'

                    # Test get command
                    args = MockArgs(key='runtime')
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_get(args)
                        output = mock_stdout.getvalue().strip()
                        assert output == 'docker'

                    # Test set command
                    args = MockArgs(key='llms.llm.temperature', value='0.8')
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_set(args)
                        output = mock_stdout.getvalue()
                        assert 'Configuration updated' in output

                    # Test validate command
                    args = MockArgs(file=None)
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_validate(args)
                        output = mock_stdout.getvalue()
                        assert '✅ Current configuration is valid' in output

                    # Test diagnostics command
                    args = MockArgs()
                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        handle_config_diagnostics(args)
                        output = mock_stdout.getvalue()
                        assert 'Configuration Diagnostics' in output

    def test_error_handling_across_commands(self):
        """Test error handling across different CLI commands."""
        with patch(
            'openhands.cli.config_commands.get_config_loader'
        ) as mock_get_loader:
            # Mock loader that raises exceptions
            mock_loader = MagicMock()
            mock_loader.get_config.side_effect = Exception('Config error')
            mock_loader.update_config.side_effect = Exception('Update error')
            mock_loader.validate_config.side_effect = Exception('Validation error')
            mock_get_loader.return_value = mock_loader

            # Test that all commands handle errors gracefully
            commands_and_args = [
                (handle_config_get, MockArgs(key='runtime')),
                (handle_config_set, MockArgs(key='runtime', value='local')),
                (handle_config_validate, MockArgs(file=None)),
            ]

            for command, args in commands_and_args:
                with patch('sys.stdout', new_callable=StringIO):
                    with pytest.raises(SystemExit):
                        command(args)
