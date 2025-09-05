"""Centralized command line argument configuration for OpenHands CLI and headless modes."""

import argparse
from argparse import ArgumentParser, _SubParsersAction


def get_subparser(parser: ArgumentParser, name: str) -> ArgumentParser:
    for action in parser._actions:
        if isinstance(action, _SubParsersAction):
            if name in action.choices:
                return action.choices[name]
    raise ValueError(f"Subparser '{name}' not found")


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared between CLI and headless modes."""
    parser.add_argument(
        '--config-file',
        type=str,
        default='config.toml',
        help='Path to the config file (default: config.toml in the current directory)',
    )
    parser.add_argument(
        '-t',
        '--task',
        type=str,
        default='',
        help='The task for the agent to perform',
    )
    parser.add_argument(
        '-f',
        '--file',
        type=str,
        help='Path to a file containing the task. Overrides -t if both are provided.',
    )
    parser.add_argument(
        '-n',
        '--name',
        help='Session name',
        type=str,
        default='',
    )
    parser.add_argument(
        '--log-level',
        help='Set the log level',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-l',
        '--llm-config',
        default=None,
        type=str,
        help='Replace default LLM ([llm] section in config.toml) config with the specified LLM config, e.g. "llama3" for [llm.llama3] section in config.toml',
    )
    parser.add_argument(
        '--agent-config',
        default=None,
        type=str,
        help='Replace default Agent ([agent] section in config.toml) config with the specified Agent config, e.g. "CodeAct" for [agent.CodeAct] section in config.toml',
    )
    parser.add_argument(
        '-v', '--version', action='store_true', help='Show version information'
    )


def add_evaluation_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments specific to evaluation mode."""
    # Evaluation-specific arguments
    parser.add_argument(
        '--eval-output-dir',
        default='evaluation/evaluation_outputs/outputs',
        type=str,
        help='The directory to save evaluation output',
    )
    parser.add_argument(
        '--eval-n-limit',
        default=None,
        type=int,
        help='The number of instances to evaluate',
    )
    parser.add_argument(
        '--eval-num-workers',
        default=4,
        type=int,
        help='The number of workers to use for evaluation',
    )
    parser.add_argument(
        '--eval-note',
        default=None,
        type=str,
        help='The note to add to the evaluation directory',
    )
    parser.add_argument(
        '--eval-ids',
        default=None,
        type=str,
        help='The comma-separated list (in quotes) of IDs of the instances to evaluate',
    )


def add_headless_specific_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments specific to headless mode (full evaluation suite)."""
    parser.add_argument(
        '-d',
        '--directory',
        type=str,
        help='The working directory for the agent',
    )
    parser.add_argument(
        '-c',
        '--agent-cls',
        default=None,
        type=str,
        help='Name of the default agent to use',
    )
    parser.add_argument(
        '-i',
        '--max-iterations',
        default=None,
        type=int,
        help='The maximum number of iterations to run the agent',
    )
    parser.add_argument(
        '-b',
        '--max-budget-per-task',
        type=float,
        help='The maximum budget allowed per task, beyond which the agent will stop.',
    )
    # Additional headless-specific arguments
    parser.add_argument(
        '--no-auto-continue',
        help='Disable auto-continue responses in headless mode (i.e. headless will read from stdin instead of auto-continuing)',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--selected-repo',
        help='GitHub repository to clone (format: owner/repo)',
        type=str,
        default=None,
    )


def get_cli_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI mode with simplified argument set."""
    # Create a description with welcome message explaining available commands
    description = (
        'Welcome to OpenHands: Code Less, Make More\n\n'
        'OpenHands supports two main commands:\n'
        '  serve - Launch the OpenHands GUI server (web interface)\n'
        '  cli   - Run OpenHands in CLI mode (terminal interface)\n\n'
        'Running "openhands" without a command is the same as "openhands cli"'
    )

    parser = argparse.ArgumentParser(
        description=description,
        prog='openhands',
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserve formatting in description
        epilog='For more information about a command, run: openhands COMMAND --help',
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='OpenHands supports these main commands:',
        metavar='COMMAND',
    )

    # Add 'serve' subcommand
    serve_parser = subparsers.add_parser(
        'serve', help='Launch the OpenHands GUI server using Docker (web interface)'
    )
    serve_parser.add_argument(
        '--mount-cwd',
        help='Mount the current working directory into the GUI server container',
        action='store_true',
        default=False,
    )
    serve_parser.add_argument(
        '--gpu',
        help='Enable GPU support by mounting all GPUs into the Docker container via nvidia-docker',
        action='store_true',
        default=False,
    )

    # Add 'cli' subcommand - import all the existing CLI arguments
    cli_parser = subparsers.add_parser(
        'cli', help='Run OpenHands in CLI mode (terminal interface)'
    )
    add_common_arguments(cli_parser)

    cli_parser.add_argument(
        '--override-cli-mode',
        help='Override the default settings for CLI mode',
        type=bool,
        default=False,
    )
    parser.add_argument(
        '--conversation',
        help='The conversation id to continue',
        type=str,
        default=None,
    )

    # Add 'config' subcommand
    config_parser = subparsers.add_parser(
        'config', help='Manage OpenHands configuration'
    )
    config_subparsers = config_parser.add_subparsers(
        dest='config_command',
        title='config commands',
        description='Configuration management commands:',
        metavar='CONFIG_COMMAND',
    )

    # config show
    show_parser = config_subparsers.add_parser(
        'show', help='Show current configuration'
    )
    show_parser.add_argument(
        '--sources', action='store_true', help='Show configuration sources'
    )
    show_parser.add_argument(
        '--format', choices=['json', 'yaml', 'toml'], default='yaml',
        help='Output format (default: yaml)'
    )

    # config get
    get_parser = config_subparsers.add_parser(
        'get', help='Get a specific configuration value'
    )
    get_parser.add_argument('key', help='Configuration key (e.g., runtime, llm.model)')

    # config set
    set_parser = config_subparsers.add_parser(
        'set', help='Set a configuration value'
    )
    set_parser.add_argument('key', help='Configuration key')
    set_parser.add_argument('value', help='Configuration value')
    set_parser.add_argument(
        '--source', choices=['user', 'env'], default='user',
        help='Configuration source to update (default: user)'
    )

    # config validate
    validate_parser = config_subparsers.add_parser(
        'validate', help='Validate configuration'
    )
    validate_parser.add_argument(
        '--file', help='Validate a specific config file'
    )

    # config diagnostics
    diagnostics_parser = config_subparsers.add_parser(
        'diagnostics', help='Show configuration diagnostics'
    )

    # config reset
    reset_parser = config_subparsers.add_parser(
        'reset', help='Reset configuration to defaults'
    )
    reset_parser.add_argument(
        '--confirm', action='store_true',
        help='Confirm the reset operation'
    )

    return parser


def get_headless_parser() -> argparse.ArgumentParser:
    """Create argument parser for headless mode with full argument set."""
    parser = argparse.ArgumentParser(description='Run the agent via CLI')
    add_common_arguments(parser)
    add_headless_specific_arguments(parser)
    return parser


def get_evaluation_parser() -> argparse.ArgumentParser:
    """Create argument parser for evaluation mode."""
    parser = argparse.ArgumentParser(description='Run OpenHands in evaluation mode')
    add_common_arguments(parser)
    add_headless_specific_arguments(parser)
    add_evaluation_arguments(parser)
    return parser
