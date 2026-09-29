from __future__ import annotations

from pathlib import Path
import os
import shutil
import stat
import subprocess

import click

from chatup.interaction import (
    BACK_VALUE,
    ask_checkbox_with_controls,
    ask_confirm,
    create_choice,
)


CHATTOOL_REPO_URL = "https://github.com/cubenlp/ChatTool.git"
CHATBLOG_REPO_URL = "https://github.com/ChatArch/ChatBlog.git"
CHATMEMORY_REPO_URL = "https://github.com/ChatArch/ChatMemory.git"
DEFAULT_MEMORY_SKILL_GROUPS = ("chatarch", "common", "agents")
LOCAL_SKILL_GROUP_README = """# Local Skills

Use this directory for machine-specific, workspace-specific, or private skills that should not be shared through ChatMemory.

Shared skills should live in one of the linked ChatMemory groups: `chatarch`, `common`, or `agents`.

Topic directories such as `chatarch/package-development` and `chatarch/package-review` are available under `skills/chatarch/`.
"""


def _resolve_git_command() -> str | None:
    git = shutil.which("git")
    if git:
        return git
    if os.name != "nt":
        return None

    candidates: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "Programs" / "Git" / "cmd" / "git.exe",
                Path(local_app_data) / "Programs" / "Git" / "bin" / "git.exe",
            ]
        )
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.extend(
                [
                    Path(root) / "Git" / "cmd" / "git.exe",
                    Path(root) / "Git" / "bin" / "git.exe",
                ]
            )

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


_GIT_NOT_FOUND_MESSAGE = (
    "Git executable not found. Install Git and make sure `git` is available on PATH. "
    "On Windows, standard Git for Windows locations are also supported. "
    "Then rerun this command."
)


def _run_git(
    args: list[str], workdir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    git = _resolve_git_command()
    if git is None:
        raise click.ClickException(_GIT_NOT_FOUND_MESSAGE)

    command = [git]
    if workdir is not None:
        command.extend(["-C", str(workdir)])
    command.extend(args)
    try:
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise click.ClickException(_GIT_NOT_FOUND_MESSAGE) from exc


def _clone_or_update_repo(
    repo_source: str, repo_dir: Path, interactive, can_prompt: bool
) -> str:
    if not repo_dir.exists():
        result = _run_git(["clone", repo_source, str(repo_dir)])
        if result.returncode != 0:
            raise click.ClickException(
                result.stderr.strip() or f"Failed to clone {repo_source}"
            )
        return "cloned"

    if not (repo_dir / ".git").exists():
        raise click.ClickException(f"Existing path is not a git repo: {repo_dir}")

    dirty = _run_git(["status", "--porcelain"], workdir=repo_dir)
    if dirty.returncode == 0 and dirty.stdout.strip():
        if interactive is not False and can_prompt:
            keep = ask_confirm(
                f"{repo_dir} has local changes. Skip update?", default=True
            )
            if keep == BACK_VALUE:
                raise click.Abort()
            if keep:
                return "skipped"
        else:
            return "skipped"

    fetch = _run_git(["fetch", "--prune", repo_source], workdir=repo_dir)
    if fetch.returncode != 0:
        raise click.ClickException(
            fetch.stderr.strip() or f"Failed to fetch {repo_source}"
        )
    merge = _run_git(["merge", "--ff-only", "FETCH_HEAD"], workdir=repo_dir)
    if merge.returncode != 0:
        raise click.ClickException(
            merge.stderr.strip() or f"Failed to fast-forward {repo_dir}"
        )
    return "updated"


def apply_chattool_option(
    workspace_dir: Path,
    source: str,
    interactive,
    can_prompt: bool,
) -> dict:
    repo_dir = workspace_dir / "core" / "ChatTool"
    repo_action = _clone_or_update_repo(source, repo_dir, interactive, can_prompt)
    return {
        "name": "chattool",
        "repo_dir": repo_dir,
        "repo_action": repo_action,
    }


def _paths_point_to_same_entry(source: Path, target: Path) -> bool:
    try:
        return source.exists() and target.exists() and source.samefile(target)
    except OSError:
        return False


def _is_windows_reparse_point(path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        info = path.stat(follow_symlinks=False)
    except (AttributeError, OSError, ValueError):
        return False
    return info.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT


def _remove_link_path(path: Path) -> None:
    if os.name == "nt" and path.is_dir():
        path.rmdir()
    else:
        path.unlink()


def _create_windows_junction(source: Path, target: Path) -> None:
    comspec = os.environ.get("ComSpec", "cmd")
    # Pass paths through quoted environment expansion, not cmd command syntax.
    env = {**os.environ, "CHATUP_LINK_SOURCE": str(source), "CHATUP_LINK_TARGET": str(target)}
    command = (
        f'{subprocess.list2cmdline([comspec])} /d /v:off /c '
        'mklink /J "%CHATUP_LINK_TARGET%" "%CHATUP_LINK_SOURCE%"'
    )
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise click.ClickException(message or f"Failed to create junction: {target}")


def _create_windows_link_fallback(source: Path, target: Path, original: OSError) -> None:
    if os.name != "nt":
        raise click.ClickException(
            f"Failed to create symlink {target} -> {source}: {original}"
        ) from original
    try:
        if source.is_dir():
            _create_windows_junction(source.resolve(), target)
        else:
            os.link(source, target)
    except (OSError, click.ClickException) as exc:
        raise click.ClickException(
            "Failed to create a workspace link on Windows. Enable Developer Mode "
            "or run with symlink privileges; directory junction/file hard-link "
            f"fallback also failed for {target} -> {source}: {exc}"
        ) from exc


def _ensure_symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or _is_windows_reparse_point(target):
        if _paths_point_to_same_entry(source, target):
            return
        _remove_link_path(target)
    elif target.exists():
        if _paths_point_to_same_entry(source, target):
            return
        raise click.ClickException(
            f"Refusing to replace existing non-link path: {target}"
        )

    try:
        target.symlink_to(source, target_is_directory=source.is_dir())
    except OSError as exc:
        _create_windows_link_fallback(source, target, exc)


def _ensure_local_skill_group(workspace_dir: Path) -> Path:
    local_dir = workspace_dir / "skills" / "local"
    if local_dir.is_symlink():
        raise click.ClickException(
            f"Refusing to use symlink for local-only skill group: {local_dir}"
        )
    local_dir.mkdir(parents=True, exist_ok=True)
    readme = local_dir / "README.md"
    if not readme.exists():
        readme.write_text(LOCAL_SKILL_GROUP_README, encoding="utf-8")
    return local_dir


def _resolve_chatblog_public_source(repo_dir: Path) -> tuple[Path, str]:
    docs_dir = repo_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    readme = docs_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# ChatBlog\n\nPlaceholder docs directory created by ChatUp workspace setup.\n",
            encoding="utf-8",
        )
    return docs_dir, "docs"


def apply_chatblog_option(
    workspace_dir: Path,
    source: str,
    interactive,
    can_prompt: bool,
) -> dict:
    repo_dir = workspace_dir / "core" / "ChatBlog"
    repo_action = _clone_or_update_repo(source, repo_dir, interactive, can_prompt)
    public_source, public_source_label = _resolve_chatblog_public_source(repo_dir)
    public_link = workspace_dir / "public" / "chatblog"
    _ensure_symlink(public_source, public_link)
    return {
        "name": "chatblog",
        "repo_dir": repo_dir,
        "repo_action": repo_action,
        "public_link": public_link,
        "public_source": public_source,
        "public_source_label": public_source_label,
    }


def apply_memory_option(
    workspace_dir: Path,
    source: str,
    interactive,
    can_prompt: bool,
) -> dict:
    repo_dir = workspace_dir / "core" / "ChatMemory"
    repo_action = _clone_or_update_repo(source, repo_dir, interactive, can_prompt)
    skills_root = repo_dir / "Skills"
    if not skills_root.exists():
        raise click.ClickException(
            f"ChatMemory repo does not contain Skills/: {skills_root}"
        )

    readme_link: Path | None = None
    skills_readme = skills_root / "README.md"
    if skills_readme.exists():
        readme_link = workspace_dir / "skills" / "README.md"
        _ensure_symlink(skills_readme, readme_link)

    linked_groups: list[str] = []
    skipped_groups: list[str] = []
    for group in DEFAULT_MEMORY_SKILL_GROUPS:
        group_source = skills_root / group
        if not group_source.exists():
            skipped_groups.append(group)
            continue
        _ensure_symlink(group_source, workspace_dir / "skills" / group)
        linked_groups.append(group)

    local_group = _ensure_local_skill_group(workspace_dir)

    return {
        "name": "memory",
        "repo_dir": repo_dir,
        "repo_action": repo_action,
        "linked_groups": linked_groups,
        "skipped_groups": skipped_groups,
        "local_group": local_group,
        "readme_link": readme_link,
    }


def prompt_optional_modules(language: str) -> dict[str, dict]:
    results = {
        "chattool": {
            "enabled": False,
            "source": CHATTOOL_REPO_URL,
        },
        "chatblog": {
            "enabled": False,
            "source": CHATBLOG_REPO_URL,
        },
        "memory": {
            "enabled": False,
            "source": CHATMEMORY_REPO_URL,
        },
    }

    enable_extras = ask_confirm(
        "Configure extra workspace modules?"
        if language == "en"
        else "是否配置额外的 workspace 模块？",
        default=False,
    )
    if enable_extras == BACK_VALUE:
        raise click.Abort()
    if not enable_extras:
        return results

    selected = ask_checkbox_with_controls(
        "Select extra workspace modules"
        if language == "en"
        else "选择额外的 workspace 模块",
        choices=[
            create_choice("ChatTool -> core/ChatTool", "chattool"),
            create_choice("ChatBlog -> core/ChatBlog + public/chatblog", "chatblog"),
            create_choice("ChatMemory -> core/ChatMemory + shared skill groups (chatarch/common/agents) + local", "memory"),
        ],
        default_values=[],
        instruction="",
        select_all_label="Select all" if language == "en" else "全选",
    )
    if selected == BACK_VALUE:
        raise click.Abort()

    for key in selected:
        if key in results:
            results[key]["enabled"] = True
    return results
