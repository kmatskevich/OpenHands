"""Project memory system using SQLite for local runtime environments."""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional, Union

from openhands.core.logger import openhands_logger as logger


class ProjectMemory:
    """Manages project-specific memory using SQLite database."""

    def __init__(self, project_root: str, runtime_env: str = 'local'):
        """Initialize project memory.

        Args:
            project_root: Root directory of the project
            runtime_env: Runtime environment ('local' or 'docker')
        """
        self.project_root = Path(project_root)
        self.runtime_env = runtime_env
        self.memory_dir = self.project_root / '.openhands' / '.memory'
        self.db_path = self.memory_dir / 'agent.sqlite'
        self.connection: Optional[sqlite3.Connection] = None

        # Add validation for .openhands directory structure
        self._validate_openhands_directory()

    def init_database(self) -> bool:
        """Initialize the SQLite database and create schema.

        Returns:
            True if database was created/initialized successfully
        """
        try:
            # Create memory directory if it doesn't exist
            self.memory_dir.mkdir(parents=True, exist_ok=True)

            # Check if directory is writable
            if not os.access(self.memory_dir, os.W_OK):
                logger.error(f'Memory directory is not writable: {self.memory_dir}')
                return False

            # Connect to database
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row

            # Create schema
            self._create_schema()

            # Set schema version
            self._set_meta('schema_version', '1.0')

            logger.info(f'Project memory initialized at: {self.db_path}')
            return True

        except Exception as e:
            logger.error(f'Failed to initialize project memory: {e}')
            return False

    def connect(self) -> bool:
        """Connect to existing database.

        Returns:
            True if connection successful
        """
        try:
            if not self.db_path.exists():
                logger.warning(f'Project memory database not found: {self.db_path}')
                return False

            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row

            logger.info(f'Connected to project memory: {self.db_path}')
            return True

        except Exception as e:
            logger.error(f'Failed to connect to project memory: {e}')
            return False

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self.connection is not None

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def _create_schema(self):
        """Create database schema."""
        if not self.connection:
            return
        cursor = self.connection.cursor()

        # Meta table for key-value storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Events table for agent action logging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT,
                details TEXT
            )
        """)

        # Files table for file state tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                last_hash TEXT,
                last_seen REAL
            )
        """)

        # Embeddings table for vector storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                chunk_start INTEGER,
                chunk_end INTEGER,
                vector BLOB
            )
        """)

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_last_seen ON files(last_seen)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_embeddings_path ON embeddings(path)'
        )

        if self.connection:
            self.connection.commit()

    def _set_meta(self, key: str, value: str):
        """Set metadata value."""
        if not self.connection:
            return

        cursor = self.connection.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', (key, value)
        )
        self.connection.commit()

    def get_meta(self, key: str) -> Optional[str]:
        """Get metadata value."""
        if not self.connection:
            return None

        cursor = self.connection.cursor()
        cursor.execute('SELECT value FROM meta WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else None

    def log_event(
        self,
        kind: str,
        summary: Union[str, dict[str, Any]],
        details: Optional[str] = None,
    ):
        """Log an agent event.

        Args:
            kind: Type of event (e.g., 'action', 'observation')
            summary: Brief description or data dict of the event
            details: Optional detailed information
        """
        if not self.connection:
            return

        # Convert dict to JSON string if needed
        if isinstance(summary, dict):
            summary_str = json.dumps(summary)
        else:
            summary_str = summary

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO events (ts, kind, summary, details)
            VALUES (?, ?, ?, ?)
        """,
            (time.time(), kind, summary_str, details),
        )
        self.connection.commit()

        logger.debug(f'Logged event: {kind} - {summary}')

    def get_events(self, kind: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Get recent events.

        Args:
            kind: Filter by event kind
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        if not self.connection:
            return []

        cursor = self.connection.cursor()

        if kind:
            cursor.execute(
                """
                SELECT * FROM events WHERE kind = ?
                ORDER BY ts DESC LIMIT ?
            """,
                (kind, limit),
            )
        else:
            cursor.execute('SELECT * FROM events ORDER BY ts DESC LIMIT ?', (limit,))

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Try to parse summary as JSON if it looks like JSON
            try:
                if event['summary'].startswith('{') or event['summary'].startswith('['):
                    event['data'] = json.loads(event['summary'])
                else:
                    event['data'] = event['summary']
            except (json.JSONDecodeError, AttributeError):
                event['data'] = event['summary']
            events.append(event)
        return events

    def update_file_state(self, path: str, file_hash: str):
        """Update file state tracking.

        Args:
            path: File path relative to project root
            file_hash: Hash of file content
        """
        if not self.connection:
            return

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO files (path, last_hash, last_seen)
            VALUES (?, ?, ?)
        """,
            (path, file_hash, time.time()),
        )
        self.connection.commit()

    def get_file_state(self, path: str) -> Optional[dict]:
        """Get file state information.

        Args:
            path: File path relative to project root

        Returns:
            Dictionary with file state or None
        """
        if not self.connection:
            return None

        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def _validate_openhands_directory(self):
        """Validate .openhands directory structure and suggest .gitignore updates."""
        openhands_dir = self.project_root / '.openhands'
        gitignore_path = self.project_root / '.gitignore'

        # Check if .openhands directory exists
        if not openhands_dir.exists():
            logger.debug(f'Creating .openhands directory at {openhands_dir}')
            openhands_dir.mkdir(parents=True, exist_ok=True)

        # Check .gitignore for .openhands/.memory/ entry
        gitignore_needs_update = True
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r') as f:
                    content = f.read()
                    if '.openhands/.memory/' in content:
                        gitignore_needs_update = False
            except Exception as e:
                logger.warning(f'Could not read .gitignore: {e}')

        if gitignore_needs_update:
            logger.info(
                "Consider adding '.openhands/.memory/' to your .gitignore file "
                'to avoid committing project memory database'
            )

    def get_status(self) -> dict:
        """Get memory status information.

        Returns:
            Dictionary with status information
        """
        status = {
            'db_path': str(self.db_path),
            'exists': self.db_path.exists(),
            'connected': self.is_connected(),
            'schema_version': None,
            'event_count': 0,
            'file_count': 0,
            'embedding_count': 0,
            'last_event_ts': None,
        }

        if self.is_connected() and self.connection:
            status['schema_version'] = self.get_meta('schema_version')

            cursor = self.connection.cursor()

            # Get counts
            cursor.execute('SELECT COUNT(*) as count FROM events')
            status['event_count'] = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM files')
            status['file_count'] = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM embeddings')
            status['embedding_count'] = cursor.fetchone()['count']

            # Get last event timestamp
            cursor.execute('SELECT MAX(ts) as last_ts FROM events')
            row = cursor.fetchone()
            status['last_event_ts'] = row['last_ts'] if row['last_ts'] else None

        return status


def create_project_memory(
    project_root: str, runtime_env: str
) -> Optional[ProjectMemory]:
    """Create and initialize project memory for local runtime.

    Args:
        project_root: Root directory of the project
        runtime_env: Runtime environment ('local' or 'docker')

    Returns:
        ProjectMemory instance or None if not applicable
    """
    if runtime_env != 'local':
        logger.debug(f'Skipping project memory for runtime: {runtime_env}')
        return None

    memory = ProjectMemory(project_root, runtime_env)

    # Try to connect to existing database first
    if memory.connect():
        return memory

    # If no existing database, initialize new one
    if memory.init_database():
        return memory

    logger.error('Failed to create project memory')
    return None
