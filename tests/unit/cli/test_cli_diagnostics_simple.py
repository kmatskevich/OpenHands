"""Tests for the CLI diagnostics command."""

import argparse
import json
from unittest.mock import Mock, patch

from openhands.cli.diagnose import run_diagnose_command


class TestCLIDiagnostics:
    """Test the CLI diagnostics command functionality."""

    @patch('openhands.cli.diagnose.load_openhands_config')
    @patch('openhands.cli.diagnose.get_diagnostics_data')
    def test_diagnose_command_json_output(self, mock_get_diagnostics, mock_load_config):
        """Test diagnose command with JSON output."""
        # Mock config loading
        mock_load_config.return_value = Mock()

        # Mock the diagnostics data
        mock_response = {
            'runtime': {'kind': 'local', 'requires_restart': False},
            'paths': {'config_path': '/test/config.toml'},
            'memory': {'connected': False, 'events_count': 0, 'files_indexed': 0},
            'validation': {'errors': [], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {'app_version': '1.0.0'},
        }
        mock_get_diagnostics.return_value = mock_response

        # Test JSON output
        with patch('builtins.print') as mock_print:
            with patch('sys.exit') as mock_exit:
                args = argparse.Namespace(json=True, verbose=False, config_file=None)
                run_diagnose_command(args)

                # Should print JSON
                mock_print.assert_called_once()
                output = mock_print.call_args[0][0]

                # Verify it's valid JSON
                parsed = json.loads(output)
                assert parsed['runtime']['kind'] == 'local'

                # Should exit with success code 0
                mock_exit.assert_called_once_with(0)

    @patch('openhands.cli.diagnose.load_openhands_config')
    @patch('openhands.cli.diagnose.get_diagnostics_data')
    def test_diagnose_command_human_output(
        self, mock_get_diagnostics, mock_load_config
    ):
        """Test diagnose command with human-readable output."""
        # Mock config loading
        mock_load_config.return_value = Mock()

        # Mock the diagnostics data
        mock_response = {
            'runtime': {'kind': 'docker', 'requires_restart': True},
            'paths': {
                'config_path': '/test/config.toml',
                'workspace_base': '/workspace',
            },
            'memory': {
                'connected': True,
                'events_count': 42,
                'files_indexed': 15,
                'backend': 'sqlite',
            },
            'validation': {'errors': ['Config error'], 'warnings': ['Config warning']},
            'env': {'openhands_overrides': ['OPENHANDS_TEST']},
            'versions': {
                'app_version': '1.0.0',
                'git_sha': 'abc123',
                'git_branch': 'main',
            },
        }
        mock_get_diagnostics.return_value = mock_response

        # Test human-readable output
        with patch(
            'openhands.cli.diagnose.print_human_readable_diagnostics'
        ) as mock_print_human:
            with patch('sys.exit') as mock_exit:
                args = argparse.Namespace(json=False, verbose=False, config_file=None)
                run_diagnose_command(args)

                # Should call human-readable print function
                mock_print_human.assert_called_once_with(mock_response, verbose=False)

                # Should exit with error code 2 (has errors)
                mock_exit.assert_called_once_with(2)

    @patch('openhands.cli.diagnose.load_openhands_config')
    @patch('openhands.cli.diagnose.get_diagnostics_data')
    def test_diagnose_command_with_errors(self, mock_get_diagnostics, mock_load_config):
        """Test diagnose command when there are validation errors."""
        # Mock config loading
        mock_load_config.return_value = Mock()

        # Mock diagnostics with errors
        mock_response = {
            'runtime': {'kind': 'local', 'requires_restart': False},
            'paths': {},
            'memory': {'connected': False, 'events_count': 0, 'files_indexed': 0},
            'validation': {'errors': ['Critical error'], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {},
        }
        mock_get_diagnostics.return_value = mock_response

        # Test that it exits with code 2 when there are errors
        with patch('builtins.print'):
            with patch('sys.exit') as mock_exit:
                args = argparse.Namespace(json=True, verbose=False, config_file=None)
                run_diagnose_command(args)

                # Should exit with error code 2
                mock_exit.assert_called_once_with(2)

    @patch('openhands.cli.diagnose.load_openhands_config')
    @patch('openhands.cli.diagnose.get_diagnostics_data')
    def test_diagnose_command_success(self, mock_get_diagnostics, mock_load_config):
        """Test diagnose command when there are no errors."""
        # Mock config loading
        mock_load_config.return_value = Mock()

        # Mock diagnostics without errors
        mock_response = {
            'runtime': {'kind': 'local', 'requires_restart': False},
            'paths': {},
            'memory': {'connected': False, 'events_count': 0, 'files_indexed': 0},
            'validation': {'errors': [], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {},
        }
        mock_get_diagnostics.return_value = mock_response

        # Test that it exits with code 0 when there are no errors
        with patch('builtins.print'):
            with patch('sys.exit') as mock_exit:
                args = argparse.Namespace(json=True, verbose=False, config_file=None)
                run_diagnose_command(args)

                # Should exit with success code 0
                mock_exit.assert_called_once_with(0)

    @patch('openhands.cli.diagnose.load_openhands_config')
    def test_diagnose_command_exception_handling(self, mock_load_config):
        """Test diagnose command exception handling."""
        # Mock config loading to raise an exception
        mock_load_config.side_effect = Exception('Config load failed')

        # Test that exceptions are handled gracefully
        with patch('sys.exit') as mock_exit:
            with patch('builtins.print') as mock_print:
                args = argparse.Namespace(json=True, verbose=False, config_file=None)
                run_diagnose_command(args)

                # Should exit with error code 2
                mock_exit.assert_called_once_with(2)

                # Should print error response in JSON format
                mock_print.assert_called_once()
                output = mock_print.call_args[0][0]
                parsed = json.loads(output)
                assert 'Diagnostics failed' in parsed['validation']['errors'][0]
