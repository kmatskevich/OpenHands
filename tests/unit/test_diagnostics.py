"""Tests for the unified diagnostics system."""

import json
import os
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from openhands.cli.diagnose import format_diagnostics_human, format_diagnostics_json
from openhands.server.app import app
from openhands.server.routes.diagnostics import (
    get_env_info,
    get_memory_info,
    get_paths_info,
    get_runtime_info,
    get_validation_info,
    get_versions_info,
)


class TestDiagnosticsAPI:
    """Test the diagnostics API endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_diagnostics_endpoint_exists(self):
        """Test that the diagnostics endpoint exists and returns 200."""
        response = self.client.get('/api/diagnostics')
        assert response.status_code == 200

    def test_diagnostics_response_structure(self):
        """Test that the diagnostics response has the expected structure."""
        response = self.client.get('/api/diagnostics')
        data = response.json()

        # Check top-level keys
        expected_keys = {'runtime', 'paths', 'memory', 'validation', 'env', 'versions'}
        assert set(data.keys()) == expected_keys

        # Check runtime section
        assert 'kind' in data['runtime']
        assert 'requires_restart' in data['runtime']
        assert isinstance(data['runtime']['requires_restart'], bool)

        # Check paths section
        paths_keys = {
            'config_path',
            'project_root',
            'workspace_mount_path',
            'workspace_base',
        }
        assert all(key in data['paths'] for key in paths_keys)

        # Check memory section
        memory_keys = {
            'backend',
            'connected',
            'db_path',
            'schema_version',
            'events_count',
            'files_indexed',
            'last_event_ts',
        }
        assert all(key in data['memory'] for key in memory_keys)
        assert isinstance(data['memory']['connected'], bool)
        assert isinstance(data['memory']['events_count'], int)
        assert isinstance(data['memory']['files_indexed'], int)

        # Check validation section
        assert 'errors' in data['validation']
        assert 'warnings' in data['validation']
        assert isinstance(data['validation']['errors'], list)
        assert isinstance(data['validation']['warnings'], list)

        # Check env section
        assert 'openhands_overrides' in data['env']
        assert isinstance(data['env']['openhands_overrides'], list)

        # Check versions section
        versions_keys = {'app_version', 'git_sha', 'git_branch'}
        assert all(key in data['versions'] for key in versions_keys)


class TestDiagnosticsHelpers:
    """Test individual diagnostics helper functions."""

    def test_get_runtime_info(self):
        """Test runtime info extraction."""
        with patch.dict(os.environ, {'RUNTIME': 'docker'}):
            runtime_info = get_runtime_info()
            assert runtime_info['kind'] == 'docker'
            assert isinstance(runtime_info['requires_restart'], bool)

    def test_get_paths_info(self):
        """Test paths info extraction."""
        paths_info = get_paths_info()
        assert 'config_path' in paths_info
        assert 'project_root' in paths_info
        assert 'workspace_base' in paths_info

    def test_get_memory_info_no_connection(self):
        """Test memory info when no project memory is available."""
        memory_info = get_memory_info()
        assert memory_info['connected'] is False
        assert memory_info['events_count'] == 0
        assert memory_info['files_indexed'] == 0

    @patch('openhands.server.routes.diagnostics.create_project_memory')
    @patch('openhands.core.config.load_openhands_config')
    def test_get_memory_info_with_connection(
        self, mock_load_config, mock_create_memory
    ):
        """Test memory info when project memory is available."""
        # Mock config
        mock_config = Mock()
        mock_config.runtime = 'local'
        mock_config.workspace_base = '/test/workspace'
        mock_load_config.return_value = mock_config

        # Mock project memory
        mock_memory = Mock()
        mock_memory.is_connected.return_value = True
        mock_memory.get_events_count.return_value = 42
        mock_memory.get_files_indexed_count.return_value = 15
        mock_memory.get_last_event_timestamp.return_value = '2024-01-01T12:00:00Z'
        mock_memory.db_path = '/tmp/test.db'
        mock_memory.schema_version = '1.0'

        # Mock get_status method
        mock_status = {
            'schema_version': '1.0',
            'event_count': 42,
            'file_count': 15,
            'last_event_ts': '2024-01-01T12:00:00Z',
        }
        mock_memory.get_status.return_value = mock_status

        mock_create_memory.return_value = mock_memory

        memory_info = get_memory_info()
        assert memory_info['connected'] is True
        assert memory_info['events_count'] == 42
        assert memory_info['files_indexed'] == 15
        assert memory_info['last_event_ts'] == '2024-01-01T12:00:00Z'
        assert memory_info['db_path'] == '/tmp/test.db'
        assert memory_info['schema_version'] == '1.0'

    def test_get_validation_info(self):
        """Test validation info extraction."""
        validation_info = get_validation_info()
        assert isinstance(validation_info['errors'], list)
        assert isinstance(validation_info['warnings'], list)

    def test_get_env_info(self):
        """Test environment info extraction."""
        with patch.dict(os.environ, {'OPENHANDS_TEST_VAR': 'test_value'}):
            env_info = get_env_info()
            assert isinstance(env_info['openhands_overrides'], list)
            assert 'OPENHANDS_TEST_VAR' in env_info['openhands_overrides']

    @patch('subprocess.run')
    def test_get_versions_info_with_git(self, mock_run):
        """Test versions info with git available."""
        # Mock git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout='abc123\n'),  # git rev-parse HEAD
            Mock(returncode=0, stdout='main\n'),  # git branch --show-current
        ]

        versions_info = get_versions_info()
        assert versions_info['git_sha'] == 'abc123'
        assert versions_info['git_branch'] == 'main'

    @patch('subprocess.run')
    def test_get_versions_info_no_git(self, mock_run):
        """Test versions info without git available."""
        # Mock git commands failing
        mock_run.side_effect = [
            Mock(returncode=1, stdout=''),  # git rev-parse HEAD fails
            Mock(returncode=1, stdout=''),  # git branch --show-current fails
        ]

        versions_info = get_versions_info()
        assert versions_info['git_sha'] is None
        assert versions_info['git_branch'] is None


class TestDiagnosticsCLI:
    """Test the CLI diagnostics functionality."""

    def test_format_diagnostics_json(self):
        """Test JSON formatting of diagnostics."""
        sample_data = {
            'runtime': {'kind': 'local', 'requires_restart': False},
            'paths': {'config_path': '/test/config.toml'},
            'memory': {'connected': False, 'events_count': 0, 'files_indexed': 0},
            'validation': {'errors': [], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {'app_version': '1.0.0'},
        }

        result = format_diagnostics_json(sample_data)
        parsed = json.loads(result)

        assert parsed['runtime']['kind'] == 'local'
        assert parsed['runtime']['requires_restart'] is False
        assert parsed['paths']['config_path'] == '/test/config.toml'

    def test_format_diagnostics_human_readable(self):
        """Test human-readable formatting of diagnostics."""
        sample_data = {
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

        result = format_diagnostics_human(sample_data)

        # Check that key information is present
        assert 'Runtime: docker' in result
        assert 'Restart Required: Yes' in result
        assert 'Config File: /test/config.toml' in result
        assert 'Status: Connected' in result
        assert 'Events: 42' in result
        assert 'Files Indexed: 15' in result
        assert 'Errors (1):' in result
        assert 'Config error' in result
        assert 'Warnings (1):' in result
        assert 'Config warning' in result
        assert 'Environment Overrides (1):' in result
        assert 'OPENHANDS_TEST' in result
        assert 'App Version: 1.0.0' in result
        assert 'Git SHA: abc123' in result
        assert 'Git Branch: main' in result

    def test_format_diagnostics_human_no_issues(self):
        """Test human-readable formatting with no validation issues."""
        sample_data = {
            'runtime': {'kind': 'local', 'requires_restart': False},
            'paths': {},
            'memory': {'connected': False, 'events_count': 0, 'files_indexed': 0},
            'validation': {'errors': [], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {},
        }

        result = format_diagnostics_human(sample_data)

        assert 'Runtime: local' in result
        assert 'Restart Required: No' in result
        assert 'Status: Not Available' in result
        assert 'No validation errors found' in result
        assert 'No validation warnings found' in result
        assert 'No environment overrides detected' in result


class TestDiagnosticsIntegration:
    """Integration tests for the diagnostics system."""

    def test_full_diagnostics_flow(self):
        """Test the complete diagnostics flow from API to CLI formatting."""
        # Get diagnostics from API
        client = TestClient(app)
        response = client.get('/api/diagnostics')
        assert response.status_code == 200

        data = response.json()

        # Test both formatting options
        json_output = format_diagnostics_json(data)
        human_output = format_diagnostics_human(data)

        # Verify JSON is valid
        parsed_json = json.loads(json_output)
        assert 'runtime' in parsed_json

        # Verify human output contains key sections
        assert '=== OpenHands Diagnostics ===' in human_output
        assert 'Runtime Information' in human_output
        assert 'Path Information' in human_output
        assert 'Project Memory' in human_output
        assert 'Validation Results' in human_output
        assert 'Environment' in human_output
        assert 'Version Information' in human_output

    @patch.dict(os.environ, {'RUNTIME': 'docker', 'OPENHANDS_TEST': 'value'})
    def test_diagnostics_with_environment_overrides(self):
        """Test diagnostics with environment variables set."""
        client = TestClient(app)
        response = client.get('/api/diagnostics')
        data = response.json()

        assert data['runtime']['kind'] == 'docker'
        assert 'OPENHANDS_TEST' in data['env']['openhands_overrides']

    def test_diagnostics_error_handling(self):
        """Test that diagnostics handles errors gracefully."""
        # Even if some components fail, the endpoint should still return data
        client = TestClient(app)
        response = client.get('/api/diagnostics')

        # Should always return 200 with basic structure
        assert response.status_code == 200
        data = response.json()

        # Basic structure should always be present
        required_keys = {'runtime', 'paths', 'memory', 'validation', 'env', 'versions'}
        assert all(key in data for key in required_keys)
