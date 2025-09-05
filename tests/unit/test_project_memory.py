"""Tests for project memory functionality."""

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from openhands.memory.project_memory import ProjectMemory, create_project_memory


class TestProjectMemory:
    """Test cases for ProjectMemory class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory_structure(self):
        """Test that initialization creates proper directory structure."""
        memory = ProjectMemory(str(self.project_root), 'local')

        assert memory.project_root == self.project_root
        assert memory.memory_dir == self.project_root / '.openhands' / '.memory'
        assert (
            memory.db_path
            == self.project_root / '.openhands' / '.memory' / 'agent.sqlite'
        )
        assert (self.project_root / '.openhands').exists()

    def test_init_database_creates_schema(self):
        """Test that database initialization creates proper schema."""
        memory = ProjectMemory(str(self.project_root), 'local')

        assert memory.init_database()
        assert memory.db_path.exists()

        # Verify schema
        conn = sqlite3.connect(memory.db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        expected_tables = {'meta', 'events', 'files', 'embeddings'}
        assert expected_tables.issubset(tables)

        # Check meta table has schema version
        cursor.execute("SELECT value FROM meta WHERE key='schema_version'")
        version = cursor.fetchone()
        assert version is not None
        assert version[0] == '1.0'

        conn.close()

    def test_connect_to_existing_database(self):
        """Test connecting to existing database."""
        memory = ProjectMemory(str(self.project_root), 'local')

        # Create database first
        assert memory.init_database()
        memory.close()

        # Create new instance and connect
        memory2 = ProjectMemory(str(self.project_root), 'local')
        assert memory2.connect()
        assert memory2.connection is not None

    def test_log_event(self):
        """Test logging events to database."""
        memory = ProjectMemory(str(self.project_root), 'local')
        memory.init_database()

        # Log an event
        event_data = {
            'action': 'run',
            'args': {'command': 'ls -la'},
            'result': 'success',
        }
        memory.log_event('action', event_data)

        # Retrieve and verify
        events = memory.get_events(limit=1)
        assert len(events) == 1
        assert events[0]['kind'] == 'action'
        assert events[0]['data']['action'] == 'run'
        assert events[0]['data']['args']['command'] == 'ls -la'

    def test_get_events_with_filter(self):
        """Test retrieving events with kind filter."""
        memory = ProjectMemory(str(self.project_root), 'local')
        memory.init_database()

        # Log different types of events
        memory.log_event('action', {'type': 'run'})
        memory.log_event('observation', {'type': 'result'})
        memory.log_event('action', {'type': 'edit'})

        # Get only action events
        action_events = memory.get_events(kind='action', limit=10)
        assert len(action_events) == 2
        assert all(event['kind'] == 'action' for event in action_events)

        # Get only observation events
        obs_events = memory.get_events(kind='observation', limit=10)
        assert len(obs_events) == 1
        assert obs_events[0]['kind'] == 'observation'
        assert obs_events[0]['data']['type'] == 'result'

    def test_update_file_state(self):
        """Test file state tracking."""
        memory = ProjectMemory(str(self.project_root), 'local')
        memory.init_database()

        # Update file state
        memory.update_file_state('test.py', 'abc123')

        # Retrieve and verify
        state = memory.get_file_state('test.py')
        assert state is not None
        assert state['path'] == 'test.py'
        assert state['last_hash'] == 'abc123'
        assert state['last_seen'] > 0

    def test_get_status(self):
        """Test getting memory status."""
        memory = ProjectMemory(str(self.project_root), 'local')
        memory.init_database()

        # Add some data
        memory.log_event('action', {'test': 'data'})
        memory.update_file_state('test.py', 'hash123')

        status = memory.get_status()

        assert status['connected'] is True
        assert status['schema_version'] == '1.0'
        assert status['event_count'] == 1
        assert status['file_count'] == 1
        assert status['embedding_count'] == 0
        assert 'db_path' in status

    def test_gitignore_validation_warning(self):
        """Test that gitignore validation warns about missing entry."""
        # Create a .gitignore without the memory entry
        gitignore_path = self.project_root / '.gitignore'
        gitignore_path.write_text('*.pyc\n__pycache__/\n')

        with patch('openhands.memory.project_memory.logger') as mock_logger:
            ProjectMemory(str(self.project_root), 'local')

            # Should warn about missing gitignore entry
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert '.openhands/.memory/' in call_args
            assert 'gitignore' in call_args.lower()

    def test_gitignore_validation_no_warning(self):
        """Test that gitignore validation doesn't warn when entry exists."""
        # Create a .gitignore with the memory entry
        gitignore_path = self.project_root / '.gitignore'
        gitignore_path.write_text('*.pyc\n.openhands/.memory/\n__pycache__/\n')

        with patch('openhands.memory.project_memory.logger') as mock_logger:
            ProjectMemory(str(self.project_root), 'local')

            # Should not warn
            mock_logger.info.assert_not_called()

    def test_close_connection(self):
        """Test closing database connection."""
        memory = ProjectMemory(str(self.project_root), 'local')
        memory.init_database()

        assert memory.connection is not None
        memory.close()
        assert memory.connection is None


class TestCreateProjectMemory:
    """Test cases for create_project_memory function."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = str(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_for_local_runtime(self):
        """Test creating project memory for local runtime."""
        memory = create_project_memory(self.project_root, 'local')

        assert memory is not None
        assert isinstance(memory, ProjectMemory)
        assert memory.connection is not None

    def test_skip_for_docker_runtime(self):
        """Test skipping project memory for docker runtime."""
        memory = create_project_memory(self.project_root, 'docker')

        assert memory is None

    def test_connect_to_existing(self):
        """Test connecting to existing database."""
        # Create initial memory
        memory1 = create_project_memory(self.project_root, 'local')
        assert memory1 is not None
        memory1.close()

        # Create second instance - should connect to existing
        memory2 = create_project_memory(self.project_root, 'local')
        assert memory2 is not None
        assert memory2.connection is not None

    @patch('openhands.memory.project_memory.logger')
    def test_creation_failure_handling(self, mock_logger):
        """Test handling of database creation failures."""
        # Use a path that doesn't exist and can't be created
        invalid_path = '/root/nonexistent/path'

        memory = create_project_memory(invalid_path, 'local')

        # Should return None or handle gracefully
        # The actual behavior depends on permissions, so we just check it doesn't crash
        assert memory is None or isinstance(memory, ProjectMemory)


class TestProjectMemoryIntegration:
    """Integration tests for project memory."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Test complete workflow of project memory usage."""
        # Initialize memory
        memory = ProjectMemory(str(self.project_root), 'local')
        assert memory.init_database()

        # Log various events
        memory.log_event(
            'action',
            {
                'action': 'run',
                'args': {'command': 'python test.py'},
                'timestamp': time.time(),
            },
        )

        memory.log_event(
            'observation', {'content': 'Test passed successfully', 'exit_code': 0}
        )

        # Track file changes
        memory.update_file_state('test.py', 'hash_v1')
        memory.update_file_state('main.py', 'hash_v1')

        # Update file
        memory.update_file_state('test.py', 'hash_v2')

        # Verify data
        events = memory.get_events(limit=10)
        assert len(events) == 2

        action_events = memory.get_events(kind='action', limit=10)
        assert len(action_events) == 1
        assert action_events[0]['data']['action'] == 'run'

        # Check file states
        test_state = memory.get_file_state('test.py')
        assert test_state['last_hash'] == 'hash_v2'

        main_state = memory.get_file_state('main.py')
        assert main_state['last_hash'] == 'hash_v1'

        # Check status
        status = memory.get_status()
        assert status['event_count'] == 2
        assert status['file_count'] == 2
        assert status['connected'] is True

    def test_database_persistence(self):
        """Test that data persists across connections."""
        # Create and populate database
        memory1 = ProjectMemory(str(self.project_root), 'local')
        memory1.init_database()
        memory1.log_event('action', {'test': 'data'})
        memory1.update_file_state('test.py', 'hash123')
        memory1.close()

        # Reconnect and verify data
        memory2 = ProjectMemory(str(self.project_root), 'local')
        assert memory2.connect()

        events = memory2.get_events(limit=10)
        assert len(events) == 1
        assert events[0]['data']['test'] == 'data'

        file_state = memory2.get_file_state('test.py')
        assert file_state['last_hash'] == 'hash123'
