# Changelog

All notable changes to OpenHands will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Runtime Selector & Project Memory

#### New Features
- **Runtime Selection System**: Choose between Docker and Local runtime modes through the UI
- **Local Runtime Support**: Run OpenHands directly on your local machine for project development
- **Project Memory (SQLite)**: Persistent project context storage for local runtime mode
- **Layered Configuration System**: Configuration precedence: CLI → ENV → User → Defaults
- **Diagnostics System**: Comprehensive system health checks with `openhands diagnose` command
- **Runtime-Aware Start Screen**: Dynamic UI that adapts based on selected runtime mode

#### Configuration Enhancements
- **Hot/Cold Configuration Keys**: Some settings can be changed at runtime, others require restart
- **Environment Variable Support**: All config keys can be set via `OPENHANDS_*` environment variables
- **Configuration File**: Automatic creation of `~/.openhands/config.toml` with sensible defaults
- **Restart Notifications**: Clear guidance when configuration changes require restart

#### User Experience Improvements
- **Quick Start Guide**: Updated README with Docker and Local mode setup instructions
- **Empty States**: Friendly UI when no project folder is selected in local mode
- **Copy-to-Clipboard**: Easy copying of restart commands and configuration snippets
- **Improved CLI Help**: Better examples and documentation for all commands

#### Developer Experience
- **Comprehensive Documentation**: New configuration guide covering all aspects
- **Better Error Messages**: Clear validation errors with actionable guidance
- **Troubleshooting Tools**: Built-in diagnostics for common setup issues

#### Technical Implementation
- **Project Memory Database**: SQLite-based storage at `~/.openhands/project_memory.db`
- **Configuration Validation**: Real-time validation of settings with error reporting
- **Runtime Detection**: Automatic detection of Docker vs Local environment
- **Graceful Degradation**: Features work appropriately in different runtime modes

### Changed
- **Start Screen**: Now shows different options based on runtime mode (Docker vs Local)
- **Settings UI**: Runtime selection with restart requirements clearly indicated
- **CLI Interface**: Enhanced help text with practical examples
- **Configuration Loading**: New precedence system with multiple sources

### Documentation
- **Configuration Guide**: Complete reference for all configuration options
- **Local Runtime Guide**: Detailed setup instructions for local development
- **Project Memory Guide**: How OpenHands remembers your project context
- **Diagnostics Guide**: Troubleshooting with the diagnostics system

### Migration Notes
- Existing configurations will continue to work without changes
- New `~/.openhands/config.toml` file will be created automatically
- Project memory is only available in local runtime mode
- Some configuration changes now require restart (clearly indicated in UI)

---

*For older changes, see the git history.*
