"""Shell rc helpers shared by ChatUp commands.

This module intentionally does not register an `alias` command or carry
ChatTool command aliases. It only helps ChatUp flows choose shell rc files.
"""

import os
import shutil
from pathlib import Path

from chatup.interaction import (
    BACK_VALUE,
    ask_checkbox_with_controls,
    create_choice,
)

SUPPORTED_SHELLS = ("zsh", "bash")


def resolve_shell(shell=None):
    if shell in SUPPORTED_SHELLS:
        return shell
    shell_env = os.path.basename(os.environ.get("SHELL", "")).lower()
    if "zsh" in shell_env:
        return "zsh"
    if "bash" in shell_env:
        return "bash"
    return "bash"


def resolve_target_shells(shell=None):
    if shell in SUPPORTED_SHELLS:
        return [shell]

    detected = []
    if shutil.which("zsh"):
        detected.append("zsh")
    if shutil.which("bash"):
        detected.append("bash")
    if detected:
        return detected

    return [resolve_shell(None)]


def select_target_shells_interactively(default_selected):
    choices = [
        create_choice(
            title=shell_name,
            value=shell_name,
            checked=shell_name in default_selected,
        )
        for shell_name in SUPPORTED_SHELLS
        if shell_name in default_selected
    ]
    selected = ask_checkbox_with_controls(
        "Select shells",
        choices=choices,
        default_values=default_selected,
        instruction="(Use arrow keys to move, <space> to toggle, <a> to toggle all, <enter> to confirm)",
        select_all_label="Select all shells",
    )
    if selected == BACK_VALUE:
        return BACK_VALUE
    return selected or []


def resolve_shell_rc(shell, home=None):
    home_path = Path(home) if home else Path.home()
    if shell == "zsh":
        return home_path / ".zshrc"
    if shell == "bash":
        return home_path / ".bashrc"
    raise ValueError(f"Unsupported shell: {shell}")
