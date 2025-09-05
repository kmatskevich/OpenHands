"""Tests for configuration REST API routes."""

import json
import tempfile
import toml
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from openhands.server.app import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def temp_config_file():
    """Fixture for temporary config file."""
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / 'config.toml'
    
    # Create initial config
    initial_config = {
        'runtime': 'docker',
        'llms': {
            'llm': {
                'model': 'gpt-4',
                'temperature': 0.7
            }
        }
    }
    
    with open(config_path, 'w') as f:
        toml.dump(initial_config, f)
    
    yield str(config_path)
    
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigRoutes:
    """Test cases for configuration REST API routes."""

    def test_get_config(self, client):
        """Test GET /api/config/ endpoint."""
        response = client.get('/api/config/')
        assert response.status_code == 200
        
        data = response.json()
        assert 'config' in data
        assert 'sources' in data
        assert 'requires_restart' in data
        
        # Verify config structure
        config = data['config']
        assert 'runtime' in config
        assert 'llms' in config

    def test_get_config_with_sources(self, client):
        """Test GET /api/config/ with include_sources parameter."""
        response = client.get('/api/config/?include_sources=true')
        assert response.status_code == 200
        
        data = response.json()
        assert 'sources' in data
        sources = data['sources']
        assert 'default' in sources
        assert 'user' in sources

    def test_update_config(self, client):
        """Test POST /api/config/update endpoint."""
        update_data = {
            'updates': {
                'llms.llm.temperature': 0.8
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert 'requires_restart' in data

    def test_update_config_invalid_key(self, client):
        """Test POST /api/config/update with invalid key."""
        update_data = {
            'updates': {
                'invalid.key.path': 'value'
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 400
        assert 'error' in response.json()

    def test_update_config_cold_key(self, client):
        """Test POST /api/config/update with cold key."""
        update_data = {
            'updates': {
                'runtime': 'local'
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert data['requires_restart'] is True

    def test_validate_config(self, client):
        """Test POST /api/config/validate endpoint."""
        valid_config = {
            'runtime': 'docker',
            'llms': {
                'llm': {
                    'model': 'gpt-4',
                    'temperature': 0.7
                }
            },
            'security': {
                'sandbox_mode': 'strict'
            }
        }
        
        response = client.post('/api/config/validate', json=valid_config)
        assert response.status_code == 200
        
        data = response.json()
        assert 'valid' in data
        assert 'errors' in data
        assert 'warnings' in data

    def test_validate_config_invalid(self, client):
        """Test POST /api/config/validate with invalid config."""
        invalid_config = {
            'runtime': 'invalid-runtime',
            'llms': {
                'llm': {
                    'temperature': 5.0  # Invalid range
                }
            }
        }
        
        response = client.post('/api/config/validate', json=invalid_config)
        assert response.status_code == 200
        
        data = response.json()
        assert data['valid'] is False
        assert len(data['errors']) > 0

    def test_get_diagnostics(self, client):
        """Test GET /api/config/diagnostics endpoint."""
        response = client.get('/api/config/diagnostics')
        assert response.status_code == 200
        
        data = response.json()
        assert 'config_health' in data
        assert 'source_analysis' in data
        assert 'key_analysis' in data
        assert 'environment_analysis' in data
        assert 'recommendations' in data

    def test_reset_restart_flag(self, client):
        """Test POST /api/config/reset-restart-flag endpoint."""
        # First, make a change that requires restart
        update_data = {
            'updates': {
                'runtime': 'local'
            }
        }
        client.post('/api/config/update', json=update_data)
        
        # Reset the restart flag
        response = client.post('/api/config/reset-restart-flag')
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True

    def test_get_config_schema(self, client):
        """Test GET /api/config/schema endpoint."""
        response = client.get('/api/config/schema')
        assert response.status_code == 200
        
        data = response.json()
        assert 'schema' in data
        assert 'cold_keys' in data
        assert 'hot_keys' in data
        
        # Verify schema structure
        schema = data['schema']
        assert 'properties' in schema
        assert 'type' in schema

    @patch('openhands.core.config.layered_config_loader.LayeredConfigLoader.get_config')
    def test_get_config_error_handling(self, mock_get_config, client):
        """Test error handling in GET /api/config/."""
        mock_get_config.side_effect = Exception('Test error')
        
        response = client.get('/api/config/')
        assert response.status_code == 500
        assert 'error' in response.json()

    @patch('openhands.core.config.layered_config_loader.LayeredConfigLoader.update_config')
    def test_update_config_error_handling(self, mock_update_config, client):
        """Test error handling in POST /api/config/update."""
        mock_update_config.side_effect = Exception('Test error')
        
        update_data = {
            'updates': {
                'llms.llm.temperature': 0.8
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 500
        assert 'error' in response.json()

    @patch('openhands.core.config.layered_config_loader.LayeredConfigLoader.validate_config')
    def test_validate_config_error_handling(self, mock_validate_config, client):
        """Test error handling in POST /api/config/validate."""
        mock_validate_config.side_effect = Exception('Test error')
        
        config_data = {'runtime': 'docker'}
        
        response = client.post('/api/config/validate', json=config_data)
        assert response.status_code == 500
        assert 'error' in response.json()

    @patch('openhands.core.config.layered_config_loader.LayeredConfigLoader.get_diagnostics')
    def test_diagnostics_error_handling(self, mock_get_diagnostics, client):
        """Test error handling in GET /api/config/diagnostics."""
        mock_get_diagnostics.side_effect = Exception('Test error')
        
        response = client.get('/api/config/diagnostics')
        assert response.status_code == 500
        assert 'error' in response.json()

    def test_update_config_missing_updates(self, client):
        """Test POST /api/config/update with missing updates field."""
        response = client.post('/api/config/update', json={})
        assert response.status_code == 422  # Validation error

    def test_update_config_empty_updates(self, client):
        """Test POST /api/config/update with empty updates."""
        update_data = {
            'updates': {}
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True

    def test_validate_config_empty_data(self, client):
        """Test POST /api/config/validate with empty data."""
        response = client.post('/api/config/validate', json={})
        assert response.status_code == 200
        
        data = response.json()
        assert 'valid' in data
        assert 'errors' in data
        assert 'warnings' in data

    def test_config_type_conversion(self, client):
        """Test configuration type conversion in updates."""
        update_data = {
            'updates': {
                'llms.llm.temperature': '0.8',  # String that should be converted to float
                'llms.llm.num_retries': '3'     # String that should be converted to int
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        
        # Verify the values were converted correctly
        config_response = client.get('/api/config/')
        config_data = config_response.json()
        
        assert config_data['config']['llms']['llm']['temperature'] == 0.8
        assert config_data['config']['llms']['llm']['num_retries'] == 3

    def test_nested_config_updates(self, client):
        """Test nested configuration updates."""
        update_data = {
            'updates': {
                'agents.default.max_iterations': 50,
                'agents.default.memory.max_threads': 10
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True

    def test_config_validation_warnings(self, client):
        """Test configuration validation with warnings."""
        config_with_warnings = {
            'runtime': 'local',  # Should generate warning
            'llms': {
                'llm': {
                    'model': 'gpt-4',
                    'api_key': '',  # Should generate warning for missing API key
                    'base_url': ''
                }
            }
        }
        
        response = client.post('/api/config/validate', json=config_with_warnings)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['warnings']) > 0
        assert any('security implications' in warning for warning in data['warnings'])

    def test_diagnostics_comprehensive_data(self, client):
        """Test that diagnostics returns comprehensive data."""
        response = client.get('/api/config/diagnostics')
        assert response.status_code == 200
        
        data = response.json()
        
        # Check config health
        health = data['config_health']
        assert 'status' in health
        assert 'errors' in health
        assert 'warnings' in health
        assert 'requires_restart' in health
        
        # Check source analysis
        source_analysis = data['source_analysis']
        assert 'default' in source_analysis
        assert 'user' in source_analysis
        
        # Check key analysis
        key_analysis = data['key_analysis']
        assert 'total_keys' in key_analysis
        assert 'cold_keys' in key_analysis
        assert 'hot_keys' in key_analysis
        
        # Check environment analysis
        env_analysis = data['environment_analysis']
        assert 'openhands_env_vars' in env_analysis
        assert 'env_overrides' in env_analysis
        assert 'cli_overrides' in env_analysis
        
        # Check recommendations
        assert 'recommendations' in data
        assert isinstance(data['recommendations'], list)

    def test_schema_endpoint_structure(self, client):
        """Test configuration schema endpoint structure."""
        response = client.get('/api/config/schema')
        assert response.status_code == 200
        
        data = response.json()
        
        # Check schema
        schema = data['schema']
        assert 'type' in schema
        assert 'properties' in schema
        assert schema['type'] == 'object'
        
        # Check cold/hot keys
        assert 'cold_keys' in data
        assert 'hot_keys' in data
        assert isinstance(data['cold_keys'], list)
        assert isinstance(data['hot_keys'], list)
        
        # Verify some expected keys
        assert 'runtime' in data['cold_keys']
        assert len(data['hot_keys']) > len(data['cold_keys'])


class TestConfigRoutesIntegration:
    """Integration tests for configuration routes."""

    def test_full_config_workflow(self, client):
        """Test complete configuration workflow."""
        # 1. Get initial config
        response = client.get('/api/config/')
        assert response.status_code == 200
        initial_config = response.json()
        
        # 2. Update configuration
        update_data = {
            'updates': {
                'llms.llm.temperature': 0.9,
                'runtime': 'local'  # Cold key
            }
        }
        
        response = client.post('/api/config/update', json=update_data)
        assert response.status_code == 200
        update_result = response.json()
        assert update_result['success'] is True
        assert update_result['requires_restart'] is True
        
        # 3. Verify changes
        response = client.get('/api/config/')
        assert response.status_code == 200
        updated_config = response.json()
        assert updated_config['config']['llms']['llm']['temperature'] == 0.9
        assert updated_config['config']['runtime'] == 'local'
        assert updated_config['requires_restart'] is True
        
        # 4. Validate configuration
        response = client.post('/api/config/validate', json=updated_config['config'])
        assert response.status_code == 200
        validation_result = response.json()
        # Should have warnings about local runtime
        assert len(validation_result['warnings']) > 0
        
        # 5. Get diagnostics
        response = client.get('/api/config/diagnostics')
        assert response.status_code == 200
        diagnostics = response.json()
        assert diagnostics['config_health']['requires_restart'] is True
        
        # 6. Reset restart flag
        response = client.post('/api/config/reset-restart-flag')
        assert response.status_code == 200
        
        # 7. Verify restart flag is reset
        response = client.get('/api/config/')
        assert response.status_code == 200
        final_config = response.json()
        assert final_config['requires_restart'] is False

    def test_error_recovery(self, client):
        """Test error recovery in configuration operations."""
        # Try to update with invalid data
        invalid_update = {
            'updates': {
                'nonexistent.deeply.nested.key': 'value'
            }
        }
        
        response = client.post('/api/config/update', json=invalid_update)
        assert response.status_code == 400
        
        # Verify system is still functional
        response = client.get('/api/config/')
        assert response.status_code == 200
        
        # Try valid update after error
        valid_update = {
            'updates': {
                'llms.llm.temperature': 0.7
            }
        }
        
        response = client.post('/api/config/update', json=valid_update)
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_concurrent_updates(self, client):
        """Test handling of concurrent configuration updates."""
        # This test simulates concurrent updates by making multiple requests
        # In a real scenario, this would test thread safety
        
        updates = [
            {'updates': {'llms.llm.temperature': 0.5}},
            {'updates': {'llms.llm.top_p': 0.9}},
            {'updates': {'llms.llm.num_retries': 5}}
        ]
        
        responses = []
        for update in updates:
            response = client.post('/api/config/update', json=update)
            responses.append(response)
        
        # All updates should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()['success'] is True
        
        # Verify final state
        response = client.get('/api/config/')
        assert response.status_code == 200
        config = response.json()['config']
        
        assert config['llms']['llm']['temperature'] == 0.5
        assert config['llms']['llm']['top_p'] == 0.9
        assert config['llms']['llm']['num_retries'] == 5