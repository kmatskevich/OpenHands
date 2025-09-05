# Project Memory System

OpenHands includes a project memory system that automatically tracks agent actions, file changes, and project context in a local SQLite database. This system helps maintain continuity across sessions and provides insights into project evolution.

## Overview

The project memory system:
- **Automatically tracks** agent actions and observations
- **Monitors file changes** with hash-based tracking
- **Stores data locally** in `.openhands/.memory/agent.sqlite`
- **Works only with local runtime** for security and privacy
- **Provides diagnostics** via API and CLI commands

## Storage Location

Project memory data is stored in:
```
<project_root>/.openhands/.memory/agent.sqlite
```

The `.openhands` directory structure:
```
.openhands/
├── .memory/
│   └── agent.sqlite      # Project memory database
├── config.toml           # Project-specific configuration (optional)
└── microagents/          # Project-specific microagents (optional)
```

## Database Schema

The SQLite database contains four main tables:

### `meta` Table
Stores metadata about the database:
- `key`: Metadata key (e.g., 'schema_version')
- `value`: Metadata value

### `events` Table
Tracks agent actions and observations:
- `id`: Auto-incrementing primary key
- `ts`: Timestamp (Unix time)
- `kind`: Event type ('action' or 'observation')
- `summary`: JSON-encoded event data
- `details`: Optional additional details

### `files` Table
Monitors file state changes:
- `path`: File path relative to project root
- `last_hash`: SHA-256 hash of last seen content
- `last_seen`: Timestamp when file was last observed

### `embeddings` Table
Reserved for future vector storage:
- `id`: Auto-incrementing primary key
- `content_hash`: Hash of content being embedded
- `embedding`: Vector embedding data
- `metadata`: Additional embedding metadata

## Runtime Requirements

Project memory is **only available for local runtime environments**:

✅ **Supported**: `runtime = "local"`
❌ **Not supported**: `runtime = "docker"`, `runtime = "remote"`

This restriction ensures:
- **Data privacy**: Memory stays on your local machine
- **Security**: No sensitive project data in containers
- **Persistence**: Database survives container restarts

## Configuration

### Automatic Initialization

Project memory initializes automatically when:
1. Using local runtime (`runtime = "local"`)
2. Agent controller starts up
3. `.openhands` directory is created if needed

### Git Integration

Add to your `.gitignore`:
```gitignore
# OpenHands Project Memory
.openhands/.memory/
```

OpenHands will warn if this entry is missing and suggest adding it.

## Usage

### CLI Commands

Check project memory status:
```bash
/memory
```

This displays:
- Database path and connection status
- Schema version
- Event and file counts
- Overall health status

### API Diagnostics

Project memory status is included in the diagnostics endpoint:
```
GET /api/config/diagnostics
```

Response includes `memory` section with:
```json
{
  "memory": {
    "connected": true,
    "db_path": "/path/to/project/.openhands/.memory/agent.sqlite",
    "schema_version": "1.0",
    "event_count": 42,
    "file_count": 15,
    "embedding_count": 0,
    "last_event_ts": 1640995200.0
  }
}
```

## Data Types Tracked

### Agent Actions
- **Run commands**: Shell commands and their results
- **File operations**: Create, edit, delete operations
- **Code analysis**: Compilation, testing, linting
- **Web browsing**: Page visits and interactions

### File Changes
- **Content hashing**: SHA-256 of file contents
- **Modification tracking**: When files were last seen
- **Path normalization**: Relative to project root

### Future Extensions
- **Vector embeddings**: Code and documentation embeddings
- **Conversation context**: Chat history and decisions
- **Performance metrics**: Build times, test results

## Troubleshooting

### Common Issues

**Memory not initializing**
```
Error: Project memory not available
```
- Check runtime is set to `local`
- Verify write permissions in project directory
- Check disk space availability

**Database corruption**
```
Error: database disk image is malformed
```
- Delete `.openhands/.memory/agent.sqlite`
- Restart OpenHands to recreate database
- Previous memory data will be lost

**Permission errors**
```
Error: unable to open database file
```
- Check file permissions on `.openhands` directory
- Ensure user has write access to project root
- Verify no other process is locking the database

### Diagnostic Commands

Check memory status:
```bash
# In OpenHands CLI
/memory

# Check diagnostics API
curl http://localhost:3000/api/config/diagnostics
```

Verify database integrity:
```bash
# Direct SQLite check
sqlite3 .openhands/.memory/agent.sqlite "PRAGMA integrity_check;"
```

### Recovery Procedures

**Reset project memory**:
```bash
# Remove database (loses all memory data)
rm -rf .openhands/.memory/

# Restart OpenHands to recreate
```

**Backup project memory**:
```bash
# Create backup
cp .openhands/.memory/agent.sqlite .openhands/.memory/agent.sqlite.backup

# Restore from backup
cp .openhands/.memory/agent.sqlite.backup .openhands/.memory/agent.sqlite
```

## Privacy and Security

### Data Locality
- All data stored locally on your machine
- No data transmitted to external services
- Database files excluded from version control

### Sensitive Information
- Project memory may contain sensitive data
- Always add `.openhands/.memory/` to `.gitignore`
- Consider encryption for highly sensitive projects

### Data Retention
- No automatic cleanup of old data
- Database grows with project activity
- Manual cleanup may be needed for long-running projects

## Performance Considerations

### Database Size
- Typical size: 1-10 MB for most projects
- Large projects: May reach 50-100 MB
- Growth rate: ~1-5 MB per 1000 actions

### Query Performance
- Indexed on timestamp and event kind
- Fast retrieval of recent events
- Efficient file state lookups

### Maintenance
- No regular maintenance required
- SQLite handles optimization automatically
- Consider periodic VACUUM for large databases

## Development and Extension

### Adding New Event Types

To track new types of events:

1. **Log events** in your code:
```python
from openhands.memory.project_memory import ProjectMemory

memory = ProjectMemory(project_root, 'local')
memory.log_event('custom_action', {
    'type': 'my_action',
    'data': {'key': 'value'},
    'timestamp': time.time()
})
```

2. **Query events**:
```python
# Get recent custom actions
events = memory.get_events(kind='custom_action', limit=10)
```

### Database Schema Evolution

Future schema changes will:
- Include migration scripts
- Maintain backward compatibility
- Update schema version in `meta` table

### Integration Points

Project memory integrates with:
- **Agent Controller**: Automatic action logging
- **File System**: Change detection and hashing
- **Diagnostics API**: Status reporting
- **CLI Interface**: User-facing commands

## Limitations

### Current Limitations
- Local runtime only
- No automatic cleanup
- Limited query capabilities
- No cross-project memory sharing

### Future Enhancements
- Vector similarity search
- Advanced querying and filtering
- Memory compression and archiving
- Cross-session context preservation
- Integration with external knowledge bases

## FAQ

**Q: Can I disable project memory?**
A: Project memory is automatically disabled for non-local runtimes. For local runtime, it initializes automatically but can be ignored.

**Q: How much disk space does it use?**
A: Typically 1-10 MB for most projects. Large, active projects may use 50-100 MB.

**Q: Is the data encrypted?**
A: No, data is stored in plain SQLite format. Use filesystem encryption for sensitive projects.

**Q: Can I query the database directly?**
A: Yes, it's a standard SQLite database. Use any SQLite client or the `sqlite3` command-line tool.

**Q: What happens if I delete the database?**
A: OpenHands will recreate it automatically. All previous memory data will be lost.

**Q: Can I share project memory between team members?**
A: Not recommended. Project memory may contain sensitive local paths and personal workflow data.