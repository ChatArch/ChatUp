"""Select any registered ChatUp action supported on the current host."""
from __future__ import annotations

import platform

import click

from chatup.interaction import (
    abort_if_force_without_tty,
    add_interactive_option,
    ask_checkbox,
    create_choice,
    resolve_interactive_mode,
)


def _registered_leaves() -> dict[str, click.Command]:
    # Import lazily: the CLI registers this command after constructing the root.
    from chatup.cli import main

    leaves = {}

    def visit(group: click.Group, prefix: str = "") -> None:
        for name, command in group.commands.items():
            path = f"{prefix} {name}".strip()
            if path == "all":
                continue
            if isinstance(command, click.Group):
                visit(command, path)
            else:
                leaves[path] = command

    visit(main)
    return leaves


def _computer_use_supported(system: str, machine: str) -> bool:
    if system != "Linux" or machine not in {"amd64", "x86_64"}:
        return False
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        return False
    return release.get("ID", "").lower() in {"debian", "ubuntu"}


def _supported(path: str, system: str, machine: str) -> bool:
    """Match read-only platform selectors used by the original commands."""
    if system not in {"Darwin", "Linux", "Windows"}:
        return False
    name = path.split()[0]
    if name in {"zsh", "crs"}:
        return system in {"Darwin", "Linux"}
    if name == "computer-use":
        return _computer_use_supported(system, machine)
    if name == "macos":
        return system == "Darwin" and machine in {"arm64", "aarch64", "x86_64", "amd64"}
    if name == "nodejs" and system == "Windows":
        return machine in {"amd64", "x86_64", "x64", "arm64", "aarch64"}
    try:
        if name in {"chrome", "snipaste", "iterm", "wetype", "doubao", "uuremote"}:
            from chatup.setup.desktop import plan_desktop_install
            plan_desktop_install(name)
        elif name == "chatgpt":
            from chatup.setup.chatgpt import plan_chatgpt_install
            plan_chatgpt_install()
        elif name == "glance":
            from chatup.setup.glance import _require_supported_platform
            _require_supported_platform()
        elif name == "gitea":
            from chatup.setup.gitea import select_gitea_asset_name
            select_gitea_asset_name("0.0.0")
        elif name == "mysql":
            from chatup.setup.mysql import detect_mysql_platform
            detect_mysql_platform()
        elif name == "twikoo":
            from chatup.setup.twikoo import select_twikoo_asset_name
            select_twikoo_asset_name()
        elif name == "chrome-for-testing":
            from chatup.runtime.chrome_for_testing import normalize_cft_platform
            normalize_cft_platform()
        elif name == "chromedriver":
            from chatup.runtime.chromedriver import normalize_chromedriver_platform
            normalize_chromedriver_platform()
    except (RuntimeError, ValueError, click.ClickException):
        return False
    return True


def supported_items() -> dict[str, str]:
    """Enumerate registered leaf commands, not a separate handpicked list."""
    system, machine = platform.system(), platform.machine().lower()
    return {
        path: f"{path} - {command.get_short_help_str(limit=90)}"
        for path, command in _registered_leaves().items()
        if _supported(path, system, machine)
    }


def _selected_args(path: str, *, sudo: bool, yes: bool, interactive: bool | None) -> list[str]:
    parts = path.split()
    name = parts[0]
    # Never forward --yes to remove/gc, and never elevate an unselected action.
    if sudo and name in {"chrome", "uuremote", "computer-use", "docker"}:
        parts.append("--sudo")
    if yes and name in {"chrome", "snipaste", "chatgpt"}:
        parts.append("--yes")
    if platform.system() != "Linux" and name in {"nginx", "mysql", "twikoo"}:
        parts.append("--no-service")
    if interactive is False and any(
        param.name == "interactive" for param in _registered_leaves()[path].params
    ):
        parts.append("-I")
    return parts


@click.command(name="all")
@click.option("--only", "items", multiple=True, help="Select a registered command path; repeat for several.")
@click.option("--list", "list_items", is_flag=True, help="List every supported action without running it.")
@click.option("--dry-run", is_flag=True, help="Preview selected actions; never run them.")
@click.option("--sudo", is_flag=True, help="Allow selected Chrome, UU Remote, Docker or Computer Use actions to use sudo.")
@click.option("--yes", "-y", is_flag=True, help="Accept selected desktop package-manager agreements; never approve deletion.")
@add_interactive_option
def all_cli(items, list_items, dry_run, sudo, yes, interactive) -> None:
    """Select all host-supported ChatUp actions using checkboxes."""
    available = supported_items()
    if not available:
        raise click.ClickException(f"No supported ChatUp actions on {platform.system()}.")
    if list_items:
        for label in available.values():
            click.echo(label)
        return
    selected = list(dict.fromkeys(items))
    unsupported = [name for name in selected if name not in available]
    if unsupported:
        raise click.ClickException("Unknown or unsupported on this host: " + ", ".join(unsupported))
    _, can_prompt, force, _, need_prompt = resolve_interactive_mode(
        interactive, auto_prompt_condition=not selected,
    )
    abort_if_force_without_tty(force, can_prompt, "Usage: chatup all [--only 'COMMAND PATH']... [-i|-I]")
    if not selected and not need_prompt:
        raise click.UsageError("Select actions with --only 'COMMAND PATH' or run in an interactive terminal.")
    if need_prompt:
        selected = ask_checkbox(
            "Select ChatUp actions to run",
            choices=[create_choice(label, name) for name, label in available.items()],
            default_values=selected,
            instruction="(Space: toggle, Enter: run selected, Ctrl-C: cancel)",
        )
    if not selected:
        click.echo("No actions selected; nothing changed.")
        return
    unsupported = [name for name in selected if name not in available]
    if unsupported:
        raise click.ClickException("Unknown or unsupported on this host: " + ", ".join(unsupported))
    if dry_run:
        for name in selected:
            click.echo(f"Would run: chatup {name}")
        click.echo("Dry run: nothing installed or configured.")
        return
    root = click.get_current_context().parent
    failures = []
    for name in selected:
        click.echo(f"Running: chatup {name}")
        try:
            root.command.main(
                args=_selected_args(name, sudo=sudo, yes=yes, interactive=interactive),
                prog_name="chatup", standalone_mode=False,
            )
        except (click.ClickException, RuntimeError, OSError) as exc:
            failures.append(name)
            click.echo(f"Failed: {name}: {exc}", err=True)
    if failures:
        raise click.ClickException("Actions failed: " + ", ".join(failures))
    click.echo("Selected ChatUp actions completed.")
