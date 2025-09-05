# Config Loader — Minimal Plan

## Scope

Introduce a layered configuration loader and key classification to support switching runtime between docker and local, while keeping most settings hot-reloadable. Target platforms: macOS/Linux only (no Windows support).

## Precedence (highest wins)

1. **CLI overrides** (explicit flags/options)
2. **Environment variables** (OPENHANDS_*)
3. **User config** — ~/.openhands/config.toml (or path from OPENHANDS_CONFIG)
4. **Default config** — baked into the image/binary (default.toml)

### Notes:
- On startup, if ~/.openhands/config.toml is missing, create the directory and copy a template user config there, then continue boot.
- In Docker, user config should be bind-mounted (host ~/.openhands/config.toml → container path), but loader logic is identical.

## Key classification

### Cold keys (require agent restart after change)
- `runtime.environment` (docker | local)
- Any key that changes the runtime implementation, process model, container mounts, or core dependency wiring; initial set:
- `runtime.local.project_root`
- `runtime.docker.*` (if present, e.g., image, container name, mount roots)
- Low-level service wiring toggles (e.g., switching major backends)

**Behavior:**
- When a cold key is changed (via CLI/REST/ENV), the system records "Needs restart" and surfaces a clear banner/message; running services do not hot-swap.

### Hot keys (reloadable without restart)
- Logging: log.level, log.format
- Timeouts/retry/backoff values not tied to runtime initialization
- Feature toggles that alter analysis behavior only (enable/disable steps, thresholds)
- Memory/telemetry toggles that don't change storage backend type
- UI preferences

**Behavior:**
- On change, emit a "config reloaded" event and notify subscribed components to re-read their section.

## Change application model
- Provide a single "Apply config change" path (CLI/REST).
- After apply:
  - If only hot keys changed → hot-reload and return requiresRestart=false.
  - If any cold key changed → persist change, return requiresRestart=true with guidance to restart the agent/container.

## Validation
- Validate presence and readability of runtime.local.project_root only when runtime.environment=local.
- Fail fast with actionable error if required values are missing or paths are inaccessible.

## Observability
- diagnose output must include: active runtime, resolved user-config path, whether a restart is required, and any validation errors.

## Acceptance criteria
- Loader respects the precedence order above.
- First run creates ~/.openhands/config.toml from template when missing.
- Changing runtime.environment sets requiresRestart=true; other listed hot keys reload in place.
- diagnose exposes runtime, config source paths, and restart status.
