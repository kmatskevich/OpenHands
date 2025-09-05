# Runtime Selector & Project Memory - Complete Implementation

## 🎯 Overview

This PR implements a comprehensive **Runtime Selector & Project Memory** system for OpenHands, enabling users to choose between Docker and Local runtime modes with persistent project context storage.

## ✨ Key Features

### 🔄 Runtime Selection System
- **Docker Runtime**: Traditional containerized execution (existing behavior)
- **Local Runtime**: Direct execution on user's machine for project development
- **Runtime-Aware UI**: Dynamic interface that adapts based on selected runtime mode
- **Seamless Switching**: Easy runtime mode changes with clear restart requirements

### 💾 Project Memory (SQLite)
- **Persistent Storage**: SQLite database at `~/.openhands/project_memory.db`
- **Project Context**: Remembers conversations, settings, and project-specific data
- **Local Runtime Only**: Memory features available when running in local mode
- **Automatic Management**: Database creation and migration handled automatically

### ⚙️ Layered Configuration System
- **Configuration Precedence**: CLI → ENV → User → Defaults
- **Hot/Cold Keys**: Some settings change immediately, others require restart
- **Environment Variables**: All config keys available as `OPENHANDS_*` env vars
- **Auto-Creation**: `~/.openhands/config.toml` created with sensible defaults

### 🔍 Diagnostics System
- **Health Checks**: Comprehensive system status validation
- **CLI Command**: `openhands diagnose` with JSON and verbose modes
- **Troubleshooting**: Built-in guidance for common setup issues
- **Runtime Detection**: Automatic Docker vs Local environment detection

## 🚀 User Experience Improvements

### 📋 Start Screen Enhancements
- **Runtime-Aware Interface**: Different options based on Docker vs Local mode
- **Local Project Selector**: Browse and select project folders in local mode
- **Empty States**: Friendly UI when no project folder is selected
- **Clear Guidance**: Step-by-step instructions for each runtime mode

### 📖 Documentation & Help
- **Quick Start Guide**: Updated README with Docker and Local mode instructions
- **Configuration Reference**: Complete guide covering all configuration options
- **CLI Help**: Enhanced help text with practical, copy-pasteable examples
- **Troubleshooting**: Comprehensive diagnostics and error resolution

### 🎨 UX Polish
- **Copy-to-Clipboard**: Easy copying of restart commands and config snippets
- **Restart Notifications**: Clear guidance when configuration changes require restart
- **Better Error Messages**: Actionable validation errors with specific guidance
- **Improved Navigation**: Intuitive flow between different runtime modes

## 📚 Documentation

### New Documentation Pages
- **[Configuration Guide](docs/usage/configuration.mdx)**: Complete reference for all configuration options
- **[CHANGELOG.md](CHANGELOG.md)**: Detailed documentation of all changes and migration notes

### Updated Documentation
- **[README.md](README.md)**: Enhanced Quick Start section with Docker and Local mode setup
- **CLI Help**: Improved help text for all commands with practical examples

## 🧪 Testing & Quality Assurance

### QA Checklist Completed ✅
- [x] File syntax validation (Python, TypeScript)
- [x] TypeScript compilation fixes
- [x] Pre-commit hooks passing
- [x] Configuration validation
- [x] CLI help text verification
- [x] Documentation completeness

### Manual Testing Required
- [ ] Docker mode: Start screen, configuration, diagnostics
- [ ] Local mode: Runtime switching, folder selection, project memory
- [ ] Configuration: File creation, environment variables, precedence
- [ ] Diagnostics: Health checks, JSON output, troubleshooting
- [ ] CLI: Help text, command examples, error handling

## 🔧 Technical Implementation

### Backend Changes
- **Configuration System**: Layered config with validation and hot/cold keys
- **Diagnostics Engine**: Comprehensive system health checks
- **Project Memory**: SQLite-based storage for local runtime
- **CLI Enhancements**: Better argument parsing and help text

### Frontend Changes
- **Runtime Selection**: UI components for choosing Docker vs Local mode
- **Start Screen**: Dynamic interface based on runtime mode
- **Project Selector**: Local folder browsing and selection
- **Diagnostics UI**: System status display with troubleshooting

### Infrastructure
- **Database Schema**: SQLite tables for project memory storage
- **Configuration Files**: Auto-creation of `~/.openhands/config.toml`
- **Environment Detection**: Automatic Docker vs Local runtime detection

## 🔄 Migration & Compatibility

### Backward Compatibility
- ✅ Existing configurations continue to work without changes
- ✅ Docker runtime remains the default behavior
- ✅ No breaking changes to existing APIs or workflows

### Migration Notes
- New `~/.openhands/config.toml` file created automatically
- Project memory only available in local runtime mode
- Some configuration changes now require restart (clearly indicated)
- Environment variables follow new `OPENHANDS_*` naming convention

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Documentation reviewed and approved
- [ ] QA testing completed for both runtime modes
- [ ] Performance impact assessed
- [ ] Security review completed

### Post-Deployment
- [ ] Monitor for configuration-related issues
- [ ] Verify project memory database creation
- [ ] Check diagnostics system functionality
- [ ] Validate runtime switching behavior

## 🔗 Related Issues & PRs

- Addresses runtime selection requirements
- Implements project memory for local development
- Enhances configuration management system
- Improves user onboarding and troubleshooting

## 🎉 Summary

This PR delivers a complete **Runtime Selector & Project Memory** system that significantly enhances OpenHands' flexibility and user experience. Users can now choose between Docker and Local runtime modes, with persistent project context storage and comprehensive configuration management.

The implementation includes extensive documentation, improved UX, and robust diagnostics to ensure a smooth user experience across all runtime modes.
