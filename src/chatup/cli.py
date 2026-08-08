from __future__ import annotations

import inspect

import click

from chatup import __version__
from chatup.commands.chrome_for_testing import cli as chrome_for_testing_cli
from chatup.commands.chromedriver import cli as chromedriver_cli
from chatup.commands.playwright import cli as playwright_cli
from chatup.setup.cli import register_setup_commands


def _purpose(command: click.Command) -> str:
    text = command.short_help or inspect.getdoc(command.callback) or ""
    return " ".join(text.strip().split()).rstrip(".")


def _parameter_piece(parameter: click.Parameter) -> str | None:
    if getattr(parameter, "hidden", False) or parameter.name == "help":
        return None
    if isinstance(parameter, click.Argument):
        piece = parameter.name.upper().replace("_", "-")
        if not parameter.required:
            piece = f"[{piece}]"
        if parameter.nargs == -1:
            piece = f"{piece}..."
        return piece
    if not isinstance(parameter, click.Option):
        return None
    option_names = [name for name in (*parameter.opts, *parameter.secondary_opts) if name.startswith("--")]
    if not option_names:
        option_names = [name for name in (*parameter.opts, *parameter.secondary_opts) if name.startswith("-")]
    if not option_names:
        return None
    if parameter.is_flag or parameter.flag_value is not None:
        piece = "/".join(option_names)
    else:
        metavar = parameter.metavar or parameter.name.upper().replace("_", "-")
        piece = f"{'/'.join(option_names)} {metavar}"
    if not parameter.required:
        piece = f"[{piece}]"
    return piece


def _command_signature(name: str, command: click.Command) -> str:
    pieces = [piece for piece in (_parameter_piece(parameter) for parameter in command.params) if piece]
    return " ".join([name, *pieces])


def _render_command_tree(command: click.Command, name: str, prefix: str, is_last: bool, lines: list[str]) -> None:
    connector = "└── " if is_last else "├── "
    line = f"{prefix}{connector}{_command_signature(name, command)}"
    purpose = _purpose(command)
    if purpose:
        line = f"{line}  # {purpose}"
    lines.append(line)
    if not isinstance(command, click.Group):
        return
    children = [(child_name, child) for child_name, child in command.commands.items() if not child.hidden]
    child_prefix = prefix + ("    " if is_last else "│   ")
    for index, (child_name, child) in enumerate(children):
        _render_command_tree(child, child_name, child_prefix, index == len(children) - 1, lines)


def _render_cli_tree(root: click.Group) -> str:
    children = [(name, command) for name, command in root.commands.items() if not command.hidden]
    lines = [f"chatup  # {_purpose(root)}"]
    root_options = [
        ("--help", "Show help for the current command."),
        ("--version", "Show package version."),
        ("--tree", "Print the registered CLI tree."),
    ]
    for index, (option, purpose) in enumerate(root_options):
        is_last = not children and index == len(root_options) - 1
        lines.append(f"{'└──' if is_last else '├──'} {option}  # {purpose}")
    for index, (child_name, child) in enumerate(children):
        _render_command_tree(child, child_name, "", index == len(children) - 1, lines)
    return "\n".join(lines)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
    no_args_is_help=True,
)
@click.version_option(__version__, prog_name="chatup")
@click.option("--tree", "show_tree", is_flag=True, is_eager=True, help="Print the registered CLI tree.")
@click.pass_context
def main(ctx: click.Context, show_tree: bool) -> None:
    """ChatUp CLI for ChatArch bootstrap workflows."""

    if show_tree:
        click.echo(_render_cli_tree(ctx.command))
        ctx.exit()


@main.command(name="doctor")
def doctor() -> None:
    """Check that ChatUp is installed and callable."""
    click.echo(f"chatup {__version__} ok")


register_setup_commands(main)
main.add_command(chrome_for_testing_cli)
main.add_command(chromedriver_cli)
main.add_command(playwright_cli)


if __name__ == "__main__":
    main()
