"""Interactive batch setup of ordinary tools supported by this host."""
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
from chatup.setup.desktop import plan_desktop_install

# Exclude services, account-bound tools and configuration-changing installers.
COMMON = {"uv": "uv + ChatArch Python", "nodejs": "Node.js LTS"}
DESKTOP = {
    "chrome": "Google Chrome", "snipaste": "Snipaste", "iterm": "iTerm2",
    "blender": "Blender", "wetype": "WeType", "doubao": "Doubao",
    "uuremote": "UU Remote",
}
CHOICES = {**COMMON, **DESKTOP}


def supported_items() -> dict[str, str]:
    """Use the same read-only platform plan that the individual commands use."""
    system = platform.system()
    if system not in {"Darwin", "Linux", "Windows"}:
        return {}
    available = dict(COMMON)
    for name, label in DESKTOP.items():
        try:
            plan_desktop_install(name)
        except RuntimeError:
            continue
        available[name] = label
    return available


@click.command(name="all")
@click.option("--only", "items", type=click.Choice(list(CHOICES)), multiple=True,
              help="Select a specific item; repeat for several (required without a TTY).")
@click.option("--dry-run", is_flag=True, help="Preview selection; never install or configure anything.")
@click.option("--sudo", is_flag=True, help="Allow sudo for UU Remote or Linux Chrome installations.")
@click.option("--yes", "-y", is_flag=True, help="Accept Windows agreements or Linux package-manager prompts.")
@add_interactive_option
def all_cli(items, dry_run, sudo, yes, interactive) -> None:
    """Select ordinary tools with host-filtered checkboxes."""
    available = supported_items()
    if not available:
        raise click.ClickException(f"No supported setup items on {platform.system()}.")
    selected = list(dict.fromkeys(items))
    unsupported = [name for name in selected if name not in available]
    if unsupported:
        raise click.ClickException("Unsupported on this host: " + ", ".join(unsupported))
    _, can_prompt, force, _, need_prompt = resolve_interactive_mode(
        interactive, auto_prompt_condition=not selected,
    )
    abort_if_force_without_tty(force, can_prompt, "Usage: chatup all [--only NAME]... [-i|-I]")
    if not selected and not need_prompt:
        raise click.UsageError("Select items with --only NAME or run in an interactive terminal.")
    if need_prompt:
        selected = ask_checkbox(
            "Select tools to set up",
            choices=[create_choice(label, name) for name, label in available.items()],
            default_values=selected,
            instruction="(Space: toggle, Enter: run selected, Ctrl-C: cancel)",
        )
    if not selected:
        click.echo("No tools selected; nothing changed.")
        return
    unsupported = [name for name in selected if name not in available]
    if unsupported:
        raise click.ClickException("Unsupported on this host: " + ", ".join(unsupported))
    if dry_run:
        for name in selected:
            if name in DESKTOP:
                plan = plan_desktop_install(name, sudo=sudo, yes=yes)
                click.echo(f"{name}: {plan['method']} -> {plan.get('path', plan.get('command', ''))}")
            else:
                click.echo(f"{name}: chatup {name} (default options)")
        click.echo("Dry run: nothing installed or configured.")
        return
    ctx = click.get_current_context()
    root = ctx.parent
    failures = []
    for name in selected:
        command = root.command.get_command(root, name)
        try:
            kwargs = {"interactive": False} if name == "nodejs" else {}
            if name in DESKTOP:
                kwargs = {"dry_run": False}
            if name in {"chrome", "uuremote"}:
                kwargs["sudo"] = sudo
            if name in {"chrome", "snipaste"}:
                kwargs["yes"] = yes
            click.echo(f"Setting up {name}...")
            root.invoke(command, **kwargs)
        except (click.ClickException, RuntimeError, OSError) as exc:
            failures.append(name)
            click.echo(f"Failed: {name}: {exc}", err=True)
    if failures:
        raise click.ClickException("Setup failed for: " + ", ".join(failures))
    click.echo("Selected setup tasks completed.")
