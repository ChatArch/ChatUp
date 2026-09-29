"""Select and install the supported macOS desktop applications."""
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

from .desktop import _install

MACOS_APPS = {"snipaste": "Snipaste", "iterm": "iTerm2", "chrome": "Google Chrome", "blender": "Blender"}


@click.command(name="macos")
@click.option("--app", "apps", type=click.Choice(list(MACOS_APPS)), multiple=True,
              help="Install only this app; repeat to select several. Defaults to all supported apps.")
@click.option("--dry-run", is_flag=True, help="Preview selected apps without downloading or installing.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
@add_interactive_option
def macos_cli(apps, dry_run, log_level, interactive) -> None:
    """Install macOS apps; Blender is available on Apple Silicon."""
    if platform.system() != "Darwin":
        raise click.ClickException("chatup macos is supported on macOS only.")
    available = dict(MACOS_APPS)
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        available.pop("blender")
    if "blender" in apps and "blender" not in available:
        raise click.ClickException("Blender installation supports Apple Silicon macOS only.")
    selected = list(dict.fromkeys(apps)) if apps else list(available)
    _, can_prompt, force, _, need_prompt = resolve_interactive_mode(
        interactive, auto_prompt_condition=not apps and not dry_run,
    )
    abort_if_force_without_tty(force, can_prompt, "Usage: chatup macos [--app NAME] [-i|-I]")
    if need_prompt:
        selected = ask_checkbox(
            "Select macOS apps to install",
            choices=[create_choice(label, name) for name, label in available.items()],
            default_values=selected,
            instruction="(Space: toggle, Enter: install selected, Ctrl-C: cancel)",
        )
    if not selected:
        click.echo("No apps selected; nothing installed.")
        return
    click.echo("Selected apps: " + ", ".join(MACOS_APPS[name] for name in selected))
    for app in selected:
        _install(app, dry_run=dry_run, log_level=log_level)
