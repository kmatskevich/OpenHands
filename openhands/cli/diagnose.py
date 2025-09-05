"""CLI diagnostics command implementation."""

import json
import sys
from typing import Any

# Removed prompt_toolkit dependency for compatibility
from openhands.core.config import load_openhands_config
from openhands.core.logger import openhands_logger as logger
from openhands.server.routes.diagnostics import (
    get_env_info,
    get_memory_info,
    get_paths_info,
    get_runtime_info,
    get_validation_info,
    get_versions_info,
)


def run_diagnose_command(args) -> None:
    """Run the diagnose command with the given arguments."""
    try:
        # Load configuration
        config = load_openhands_config(config_file=args.config_file)

        # Get diagnostics data
        diagnostics = get_diagnostics_data(config)

        # Output based on format
        if args.json:
            print(json.dumps(diagnostics, indent=2))
        else:
            print_human_readable_diagnostics(diagnostics, verbose=args.verbose)

        # Exit with appropriate code
        has_errors = bool(diagnostics.get('validation', {}).get('errors', []))
        sys.exit(2 if has_errors else 0)

    except Exception as e:
        logger.error(f'Diagnostics command failed: {e}')
        if args.json:
            error_response = {
                'error': str(e),
                'runtime': {'kind': 'unknown', 'requires_restart': False},
                'paths': {},
                'memory': {'backend': None, 'connected': False},
                'validation': {
                    'errors': [f'Diagnostics failed: {str(e)}'],
                    'warnings': [],
                },
                'env': {'openhands_overrides': []},
                'versions': {},
            }
            print(json.dumps(error_response, indent=2))
        else:
            print(f'Error: {e}')
        sys.exit(2)


def get_diagnostics_data(config) -> dict[str, Any]:
    """Get diagnostics data using the same logic as the API endpoint."""
    diagnostics = {}

    try:
        diagnostics['runtime'] = get_runtime_info()
        diagnostics['paths'] = get_paths_info()
        diagnostics['memory'] = get_memory_info()
        diagnostics['validation'] = get_validation_info()
        diagnostics['env'] = get_env_info()
        diagnostics['versions'] = get_versions_info()
    except Exception as e:
        logger.error(f'Failed to get diagnostics data: {e}')
        # Return minimal error response
        diagnostics = {
            'runtime': {'kind': 'unknown', 'requires_restart': False},
            'paths': {},
            'memory': {'backend': None, 'connected': False},
            'validation': {'errors': [f'Diagnostics failed: {str(e)}'], 'warnings': []},
            'env': {'openhands_overrides': []},
            'versions': {},
        }

    return diagnostics


def format_diagnostics_human(diagnostics: dict[str, Any], verbose: bool = False) -> str:
    """Format diagnostics data as human-readable text."""
    output = []

    output.append('=== OpenHands Diagnostics ===\n')

    # Runtime Information
    output.append('Runtime Information:')
    runtime = diagnostics.get('runtime', {})
    output.append(f'  Runtime: {runtime.get("kind", "unknown")}')
    restart_required = runtime.get('requires_restart', False)
    output.append(f'  Restart Required: {"Yes" if restart_required else "No"}')

    if restart_required:
        runtime_kind = runtime.get('kind', 'unknown')
        if runtime_kind == 'docker':
            output.append('  Restart Command: docker compose restart openhands')
        elif runtime_kind == 'local':
            output.append('  Restart: Stop the current process and restart OpenHands')
    output.append('')

    # Path Information
    output.append('Path Information:')
    paths = diagnostics.get('paths', {})
    if verbose:
        for key, value in paths.items():
            if value:
                output.append(f'  {key.replace("_", " ").title()}: {value}')
    else:
        config_path = paths.get('config_path')
        if config_path:
            output.append(f'  Config File: {config_path}')
        workspace_base = paths.get('workspace_base')
        if workspace_base:
            output.append(f'  Workspace Base: {workspace_base}')
    output.append('')

    # Project Memory
    output.append('Project Memory:')
    memory = diagnostics.get('memory', {})
    connected = memory.get('connected', False)
    output.append(f'  Status: {"Connected" if connected else "Not Available"}')
    if connected:
        output.append(f'  Backend: {memory.get("backend", "unknown")}')
        output.append(f'  Events: {memory.get("events_count", 0)}')
        output.append(f'  Files Indexed: {memory.get("files_indexed", 0)}')
        if verbose and memory.get('db_path'):
            output.append(f'  Database Path: {memory.get("db_path")}')
    output.append('')

    # Validation Results
    output.append('Validation Results:')
    validation = diagnostics.get('validation', {})
    errors = validation.get('errors', [])
    warnings = validation.get('warnings', [])

    if errors:
        output.append(f'  Errors ({len(errors)}):')
        for error in errors:
            output.append(f'    - {error}')
    else:
        output.append('  No validation errors found')

    if warnings:
        output.append(f'  Warnings ({len(warnings)}):')
        for warning in warnings:
            output.append(f'    - {warning}')
    else:
        output.append('  No validation warnings found')
    output.append('')

    # Environment
    output.append('Environment:')
    env = diagnostics.get('env', {})
    overrides = env.get('openhands_overrides', [])
    if overrides:
        output.append(f'  Environment Overrides ({len(overrides)}):')
        for override in overrides:
            output.append(f'    - {override}')
    else:
        output.append('  No environment overrides detected')
    output.append('')

    # Version Information
    output.append('Version Information:')
    versions = diagnostics.get('versions', {})
    app_version = versions.get('app_version')
    if app_version:
        output.append(f'  App Version: {app_version}')
    git_sha = versions.get('git_sha')
    if git_sha:
        output.append(f'  Git SHA: {git_sha}')
    git_branch = versions.get('git_branch')
    if git_branch:
        output.append(f'  Git Branch: {git_branch}')

    return '\n'.join(output)


def format_diagnostics_json(diagnostics: dict[str, Any]) -> str:
    """Format diagnostics data as JSON."""
    return json.dumps(diagnostics, indent=2)


def print_human_readable_diagnostics(
    diagnostics: dict[str, Any], verbose: bool = False
) -> None:
    """Print diagnostics in human-readable format."""
    print('OpenHands Diagnostics')
    print('===================')
    print()

    # Runtime section
    runtime = diagnostics.get('runtime', {})
    print_section_header('Runtime')
    print_status_line('Kind', runtime.get('kind', 'unknown'))
    if runtime.get('requires_restart'):
        print('⚠ Restart required')
        print_restart_guidance(runtime.get('kind'))
    else:
        print('✓ No restart needed')
    print()

    # Paths section
    paths = diagnostics.get('paths', {})
    print_section_header('Paths')
    for key, value in paths.items():
        if value:
            print_status_line(key.replace('_', ' ').title(), value)
    print()

    # Memory section
    memory = diagnostics.get('memory', {})
    print_section_header('Project Memory')
    if memory.get('connected'):
        print('✓ Connected')
        print_status_line('Backend', memory.get('backend', 'unknown'))
        print_status_line('Database', memory.get('db_path', 'unknown'))
        print_status_line('Events', str(memory.get('events_count', 0)))
        print_status_line('Files Indexed', str(memory.get('files_indexed', 0)))
        if memory.get('last_event_ts'):
            print_status_line('Last Event', memory.get('last_event_ts'))
    else:
        print(('⚠ Not available (Docker runtime or not initialized)'))
    print()

    # Validation section
    validation = diagnostics.get('validation', {})
    print_section_header('Validation')
    errors = validation.get('errors', [])
    warnings = validation.get('warnings', [])

    if errors:
        print('✗ Errors found:')
        for error in errors:
            print(f'  • {error}')

    if warnings:
        print('⚠ Warnings:')
        for warning in warnings:
            print(f'  • {warning}')

    if not errors and not warnings:
        print('✓ No issues found')
    print()

    # Environment section
    env = diagnostics.get('env', {})
    print_section_header('Environment')
    overrides = env.get('openhands_overrides', [])
    if overrides:
        print('Environment overrides detected:')
        for override in overrides:
            print(f'  • {override}')
    else:
        print('✓ No environment overrides')
    print()

    # Versions section
    versions = diagnostics.get('versions', {})
    print_section_header('Versions')
    if versions.get('app_version'):
        print_status_line('App Version', versions['app_version'])
    if versions.get('git_sha'):
        print_status_line('Git SHA', versions['git_sha'])
    if versions.get('git_branch'):
        print_status_line('Git Branch', versions['git_branch'])
    print()

    # Verbose information
    if verbose:
        print_section_header('Verbose Details')
        print('Full diagnostics data:')
        print(json.dumps(diagnostics, indent=2))


def print_section_header(title: str) -> None:
    """Print a section header."""
    print(f'{title}')


def print_status_line(label: str, value: str) -> None:
    """Print a status line with label and value."""
    print(f'  {label}: {value}')


def print_restart_guidance(runtime_kind: str) -> None:
    """Print restart guidance based on runtime kind."""
    if runtime_kind == 'docker':
        print('  To restart: docker compose restart openhands')
    elif runtime_kind == 'local':
        print('  To restart: Stop the current process and run openhands again')
    else:
        print('  Restart method depends on how OpenHands was started')
