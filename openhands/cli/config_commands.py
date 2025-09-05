"""CLI commands for configuration management."""

import json
import os
import sys
from typing import Any

import toml
import yaml

from openhands.core import logger
from openhands.core.config import (
    get_config,
    get_config_loader,
    requires_restart,
    reset_restart_flag,
    update_config,
)


def handle_config_command(args) -> None:
    """Handle config subcommands."""
    if not hasattr(args, 'config_command') or args.config_command is None:
        print('Error: No config command specified. Use --help for available commands.')
        sys.exit(1)

    try:
        if args.config_command == 'show':
            handle_config_show(args)
        elif args.config_command == 'get':
            handle_config_get(args)
        elif args.config_command == 'set':
            handle_config_set(args)
        elif args.config_command == 'validate':
            handle_config_validate(args)
        elif args.config_command == 'diagnostics':
            handle_config_diagnostics(args)
        elif args.config_command == 'reset':
            handle_config_reset(args)
        else:
            print(f'Error: Unknown config command: {args.config_command}')
            sys.exit(1)
    except Exception as e:
        logger.openhands_logger.error(f'Config command failed: {e}')
        print(f'Error: {e}')
        sys.exit(1)


def handle_config_show(args) -> None:
    """Show current configuration."""
    loader = get_config_loader()
    config = get_config()

    config_dict = config.model_dump()

    if args.sources:
        # Show configuration with source information
        output = {
            'configuration': config_dict,
            'sources': loader.get_source_info(),
            'requires_restart': requires_restart(),
        }
    else:
        output = config_dict

    # Format output
    if args.format == 'json':
        print(json.dumps(output, indent=2, default=str))
    elif args.format == 'yaml':
        print(yaml.dump(output, default_flow_style=False, sort_keys=False))
    elif args.format == 'toml':
        if args.sources:
            print('# Configuration with sources (TOML format only shows config)')
            print(toml.dumps(config_dict))
        else:
            print(toml.dumps(output))


def handle_config_get(args) -> None:
    """Get a specific configuration value."""
    config = get_config()
    config_dict = config.model_dump()

    # Navigate to the requested key
    keys = args.key.split('.')
    value = config_dict

    try:
        for key in keys:
            value = value[key]

        if isinstance(value, dict):
            print(yaml.dump(value, default_flow_style=False))
        else:
            print(value)
    except (KeyError, TypeError):
        print(f'Error: Configuration key "{args.key}" not found')
        sys.exit(1)


def handle_config_set(args) -> None:
    """Set a configuration value."""
    # Parse the key path
    keys = args.key.split('.')

    # Convert value to appropriate type
    value = _parse_config_value(args.value)

    # Build nested dictionary structure
    changes: dict[str, Any] = {}
    current = changes

    for i, key in enumerate(keys[:-1]):
        current[key] = {}
        current = current[key]

    current[keys[-1]] = value

    # Update configuration
    needs_restart = update_config(changes, args.source)

    print(f'Configuration updated: {args.key} = {args.value}')
    if needs_restart:
        print('⚠️  Restart required for changes to take effect.')
    else:
        print('✅ Changes applied immediately.')


def handle_config_validate(args) -> None:
    """Validate configuration."""
    if args.file:
        # Validate a specific file
        if not os.path.exists(args.file):
            print(f'Error: File not found: {args.file}')
            sys.exit(1)

        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                if args.file.endswith('.toml'):
                    config_data = toml.load(f)
                elif args.file.endswith(('.yaml', '.yml')):
                    config_data = yaml.safe_load(f)
                elif args.file.endswith('.json'):
                    config_data = json.load(f)
                else:
                    print(
                        'Error: Unsupported file format. Use .toml, .yaml, .yml, or .json'
                    )
                    sys.exit(1)

            # Validate the configuration using enhanced validation
            loader = get_config_loader()
            is_valid, errors, warnings = loader.validate_config(config_data)

            if is_valid:
                print(f'✅ Configuration file {args.file} is valid')
                if warnings:
                    print('\nWarnings:')
                    for warning in warnings:
                        print(f'  ⚠️  {warning}')
            else:
                print(f'❌ Configuration file {args.file} is invalid')
                print('\nErrors:')
                for error in errors:
                    print(f'  ❌ {error}')
                if warnings:
                    print('\nWarnings:')
                    for warning in warnings:
                        print(f'  ⚠️  {warning}')
                sys.exit(1)

        except Exception as e:
            print(f'Error reading file {args.file}: {e}')
            sys.exit(1)
    else:
        # Validate current configuration
        try:
            loader = get_config_loader()
            is_valid, errors, warnings = loader.validate_config()

            if is_valid:
                print('✅ Current configuration is valid')
                if warnings:
                    print('\nWarnings:')
                    for warning in warnings:
                        print(f'  ⚠️  {warning}')
            else:
                print('❌ Current configuration is invalid')
                print('\nErrors:')
                for error in errors:
                    print(f'  ❌ {error}')
                if warnings:
                    print('\nWarnings:')
                    for warning in warnings:
                        print(f'  ⚠️  {warning}')
                sys.exit(1)

            # Check for restart requirements
            if requires_restart():
                print('⚠️  Configuration changes require restart')
        except Exception as e:
            print(f'❌ Error validating configuration: {e}')
            sys.exit(1)


def handle_config_diagnostics(args) -> None:
    """Show configuration diagnostics."""
    loader = get_config_loader()
    diagnostics = loader.get_diagnostics()

    print('Configuration Diagnostics')
    print('=' * 50)

    # Config health
    health = diagnostics['config_health']
    status_icon = '✅' if health['status'] == 'healthy' else '❌'
    print(f'Overall Status: {status_icon} {health["status"].title()}')
    print(f'Requires restart: {health["requires_restart"]}')
    print()

    # Show errors and warnings
    if health['errors']:
        print('❌ Configuration Errors:')
        for error in health['errors']:
            print(f'  • {error}')
        print()

    if health['warnings']:
        print('⚠️  Configuration Warnings:')
        for warning in health['warnings']:
            print(f'  • {warning}')
        print()

    # Source analysis
    print('Configuration Sources:')
    for name, info in diagnostics['source_analysis'].items():
        status = '✅' if info['status'] == 'active' else '❌'
        print(f'  {status} {name}: {info["keys_count"]} keys')
        if info['path']:
            print(f'      Path: {info["path"]}')
    print()

    # Environment analysis
    env_analysis = diagnostics['environment_analysis']
    if env_analysis['openhands_env_vars']:
        print('Environment Variables:')
        for key, value in env_analysis['openhands_env_vars'].items():
            print(f'  OPENHANDS_{key.upper()}: {value}')
        print()

    if env_analysis['env_overrides']:
        print('Environment Overrides:')
        for key, value in env_analysis['env_overrides'].items():
            print(f'  {key}: {value}')
        print()

    if env_analysis['cli_overrides']:
        print('CLI Overrides:')
        for key, value in env_analysis['cli_overrides'].items():
            print(f'  {key}: {value}')
        print()

    # Key analysis
    key_analysis = diagnostics['key_analysis']
    cold_keys = key_analysis['cold_keys']['keys']
    hot_keys = key_analysis['hot_keys']['keys']

    print(f'Cold Keys ({len(cold_keys)} total - require restart):')
    for key in sorted(cold_keys):
        print(f'  • {key}')
    print()

    print(f'Hot Keys ({len(hot_keys)} total - applied immediately):')
    for key in sorted(hot_keys)[:10]:  # Show first 10
        print(f'  • {key}')
    if len(hot_keys) > 10:
        print(f'  ... and {len(hot_keys) - 10} more')
    print()

    # Recommendations
    recommendations = diagnostics['recommendations']
    if recommendations:
        print('💡 Recommendations:')
        for rec in recommendations:
            print(f'  • {rec}')
        print()


def handle_config_reset(args) -> None:
    """Reset configuration to defaults."""
    if not args.confirm:
        print('This will reset your configuration to defaults.')
        print('Use --confirm to proceed with the reset.')
        sys.exit(1)

    loader = get_config_loader()
    user_config_path = loader.get_user_config_path_resolved()

    if user_config_path and os.path.exists(user_config_path):
        # Backup existing config
        backup_path = f'{user_config_path}.backup'
        try:
            import shutil

            shutil.copy2(user_config_path, backup_path)
            print(f'Backed up existing config to: {backup_path}')
        except Exception as e:
            print(f'Warning: Could not create backup: {e}')

        # Remove user config file
        try:
            os.remove(user_config_path)
            print(f'Removed user config file: {user_config_path}')
        except Exception as e:
            print(f'Error removing config file: {e}')
            sys.exit(1)

    # Reset restart flag
    reset_restart_flag()

    print('✅ Configuration reset to defaults')
    print('A new config file will be created on next run.')


def _parse_config_value(value_str: str) -> Any:
    """Parse a configuration value from string to appropriate type."""
    # Try to parse as JSON first (handles booleans, numbers, strings, etc.)
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        # If JSON parsing fails, treat as string
        return value_str
