"""Top-level Linux Computer Use planner and opt-in installer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import click

from chatup.computer_use import apply_computer_use, plan_computer_use


@click.command(name="computer-use")
@click.option("--sudo", is_flag=True, help="Apply the completed plan; sudo is used only for OS packages.")
@click.option("--dry-run", is_flag=True, help="Show the read-only plan, including when --sudo is present.")
@click.option("--display", help="Attach to an explicitly selected local X11 display, e.g. :20.")
@click.option("--xauthority", type=click.Path(path_type=Path), help="Same-user Xauthority for --display.")
@click.option("--state", type=click.Path(path_type=Path), help="Select existing same-user desktop metadata JSON.")
@click.option("--home", type=click.Path(path_type=Path), help="Override the effective ChatArch home for this runtime.")
def cli(sudo: bool, dry_run: bool, display: str | None, xauthority: Path | None,
        state: Path | None, home: Path | None) -> None:
    """Plan Linux X11 Computer Use; apply only with --sudo."""
    try:
        plan = plan_computer_use(home=home, display=display, xauthority=xauthority, state=state)
        result = apply_computer_use(plan) if sudo and not dry_run else plan.to_dict()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
