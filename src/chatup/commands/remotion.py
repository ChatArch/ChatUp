"""CLI for a local, reproducible Remotion video project."""
from pathlib import Path
import platform
import shlex
import subprocess

import click

from chatup.interaction import (
    abort_if_force_without_tty,
    add_interactive_option,
    ask_path,
    resolve_interactive_mode,
)


@click.command(name="remotion")
@click.argument("project_dir", required=False, type=click.Path(path_type=Path))
@click.option("--browser-executable", type=click.Path(dir_okay=False, path_type=Path),
              help="Existing Chrome/Chromium executable to use in the suggested render command.")
@click.option("--dry-run", is_flag=True, help="Preview without downloading, executing or writing files.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), default="INFO")
@add_interactive_option
def remotion_cli(project_dir, browser_executable, dry_run, log_level, interactive):
    """Initialize a local Remotion project with locked dependencies."""
    from chatup.setup.remotion import setup_remotion

    _, can_prompt, force, _, need_prompt = resolve_interactive_mode(
        interactive, auto_prompt_condition=project_dir is None,
    )
    usage = "Usage: chatup remotion PROJECT_DIR [-i|-I]"
    abort_if_force_without_tty(force, can_prompt, usage)
    if need_prompt:
        project_dir = ask_path("Remotion project directory", default=str(project_dir or Path.cwd() / "remotion-video"))
    if not project_dir:
        raise click.UsageError("PROJECT_DIR is required. Example: chatup remotion ./my-video -I")
    try:
        result = setup_remotion(project_dir, dry_run=dry_run, browser_executable=browser_executable, log_level=log_level)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    label = {"planned": "Install plan", "created": "Project ready", "already_initialized": "Already initialized"}[result["status"]]
    click.echo(f"{label}: Remotion {result['version']} at {result['path']}")
    if dry_run:
        click.echo("Requires Node.js >=18.12 and npm >=9; installs project-local locked dependencies.")
        click.echo("Dry run: no download, process execution or directory writes performed.")
    click.echo("From the project directory, start Studio with: npm run studio")
    if result["browser"]:
        command = ["npm", "run", "render", "--", f"--browser-executable={result['browser']}"]
        render = subprocess.list2cmdline(command) if platform.system() == "Windows" else shlex.join(command)
        click.echo(f"Render with the existing browser: {render}")
    else:
        click.echo("No local Chrome detected. Run chatup chrome, then rerun with --browser-executable PATH for render guidance.")
    click.echo("Browser downloads and Studio startup are not part of project initialization.")
