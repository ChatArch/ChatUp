"""Interactive policy helpers shared across CLI commands."""

import os

import click
import chatstyle.core.interactive as interactive_module

from chatstyle import FORCE_INTERACTIVE_NO_TTY_MESSAGE


def is_interactive_available():
    return interactive_module.is_interactive_available()


def normalize_interactive(interactive):
    ctx = click.get_current_context(silent=True)
    if ctx:
        try:
            if (
                ctx.get_parameter_source("interactive")
                == click.core.ParameterSource.DEFAULT
            ):
                return None
        except Exception:
            pass
    return interactive


def _auto_prompt_enabled() -> bool:
    value = os.environ.get("CHATARCH_AUTO_PROMPT")
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}


def resolve_interactive_mode(interactive, auto_prompt_condition):
    interactive = normalize_interactive(interactive)
    can_prompt = is_interactive_available()
    force_interactive = interactive is True
    auto_interactive = (
        interactive is None
        and can_prompt
        and auto_prompt_condition
        and _auto_prompt_enabled()
    )
    need_prompt = force_interactive or auto_interactive
    return interactive, can_prompt, force_interactive, auto_interactive, need_prompt


def abort_if_force_without_tty(force_interactive, can_prompt, usage):
    if force_interactive and not can_prompt:
        click.echo(FORCE_INTERACTIVE_NO_TTY_MESSAGE, err=True)
        click.echo(usage, err=True)
        raise click.Abort()


def abort_if_missing_without_tty(
    missing_required, interactive, can_prompt, message, usage
):
    if missing_required and interactive is None and not can_prompt:
        click.echo(message, err=True)
        click.echo(usage, err=True)
        raise click.Abort()
