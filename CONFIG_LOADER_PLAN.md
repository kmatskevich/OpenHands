# Config Loader Plan

## Configuration Precedence Order

Configuration values are loaded in the following order (later sources override earlier ones):

1. **Default values** - Built-in defaults in code
2. **User config file** - `~/.openhands/config.toml`
3. **Environment variables** - `OPENHANDS_*` prefixed env vars
4. **CLI arguments** - Command-line flags and options

## Configuration Key Classification

### Cold Keys (Require Restart)

These configuration changes require a full application restart to take effect:

- `runtime.environment` - Runtime environment type (local, docker, remote, etc.)
- `runtime.base_image` - Docker base image for runtime
- `runtime.platform` - Target platform architecture
- `security.sandbox_mode` - Security sandbox configuration
- `llm.api_base` - LLM API endpoint base URL
- `server.port` - Server listening port
- `server.host` - Server bind address

### Hot Keys (Reloadable)

These configuration changes can be applied without restart:

- `llm.model` - Active LLM model selection
- `llm.temperature` - LLM temperature parameter
- `llm.max_tokens` - Maximum tokens per request
- `agent.memory_enabled` - Agent memory feature toggle
- `agent.max_iterations` - Maximum agent iterations
- `ui.theme` - UI theme selection
- `ui.language` - Interface language
- `logging.level` - Log level configuration
- `workspace.mount_path` - Workspace mount directory

## Implementation Notes

- Cold key changes should trigger a warning/confirmation dialog
- Hot key changes should be applied immediately with visual feedback
- Configuration validation should occur at load time for all keys
- Runtime environment changes require graceful shutdown and restart sequence
