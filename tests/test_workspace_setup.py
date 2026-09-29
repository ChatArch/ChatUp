from pathlib import Path
import os

import click
import pytest
from click.testing import CliRunner

from chatup.cli import main


def _assert_link_points_to(link: Path, target: Path) -> None:
    assert link.exists()
    try:
        assert link.resolve() == target.resolve() or link.samefile(target)
    except OSError:
        assert False, f"{link} does not point to {target}"


def test_workspace_template_includes_chatarch_lifecycle_dirs(tmp_path):
    workspace_dir = tmp_path / "workspace"

    result = CliRunner().invoke(main, ["workspace", str(workspace_dir), "-I"])

    assert result.exit_code == 0, result.output
    for relative in ["projects", "discussion", "archive", "discard", ".trash"]:
        assert (workspace_dir / relative).is_dir()
    agents = (workspace_dir / "AGENTS.md").read_text(encoding="utf-8")
    projects_readme = (workspace_dir / "projects" / "README.md").read_text(encoding="utf-8")
    discussion_readme = (workspace_dir / "discussion" / "README.md").read_text(encoding="utf-8")
    skill = (workspace_dir / "skills" / "local" / "workspace-maintenance" / "SKILL.md").read_text(encoding="utf-8")
    assert "discussion/MM-DD-<topic>/" in agents
    assert "card.md" not in agents
    assert "worktree" in agents
    assert "`discard/`" in agents
    assert "## Discard" in projects_readme
    assert "discussion" not in projects_readme.lower()
    assert "card.md" not in projects_readme
    assert "card.md" in discussion_readme
    assert "Review 流程" in discussion_readme
    assert "version: 0.2.2" in skill
    assert "card.md" not in skill


def test_workspace_chatblog_missing_docs_creates_placeholder_and_public_link(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "workspace"

    def fake_clone_or_update(source, repo_dir, interactive, can_prompt):
        return "updated"

    monkeypatch.setattr(
        "chatup.setup.workspace.options._clone_or_update_repo",
        fake_clone_or_update,
    )

    result = CliRunner().invoke(
        main,
        ["workspace", str(workspace_dir), "--with-chatblog", "-I"],
    )

    assert result.exit_code == 0, result.output
    public_link = workspace_dir / "public" / "chatblog"
    docs_dir = workspace_dir / "core" / "ChatBlog" / "docs"
    _assert_link_points_to(public_link, docs_dir)
    assert (docs_dir / "README.md").exists()
    assert "Public link source: docs" in result.output


def test_workspace_chatblog_uses_docs_even_when_source_posts_exists(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "workspace"

    def fake_clone_or_update(source, repo_dir, interactive, can_prompt):
        (repo_dir / "source" / "_posts").mkdir(parents=True)
        (repo_dir / "docs").mkdir(parents=True)
        return "updated"

    monkeypatch.setattr(
        "chatup.setup.workspace.options._clone_or_update_repo",
        fake_clone_or_update,
    )

    result = CliRunner().invoke(
        main,
        ["workspace", str(workspace_dir), "--with-chatblog", "-I"],
    )

    assert result.exit_code == 0, result.output
    public_link = workspace_dir / "public" / "chatblog"
    _assert_link_points_to(public_link, workspace_dir / "core" / "ChatBlog" / "docs")
    assert "Public link source: docs" in result.output


def test_workspace_all_extras_clone_chattool_chatblog_chatmemory(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "workspace"
    cloned: list[Path] = []

    def fake_clone_or_update(source, repo_dir, interactive, can_prompt):
        cloned.append(repo_dir.relative_to(workspace_dir))
        if repo_dir.name == "ChatTool":
            legacy_skill = repo_dir / "skills" / "trae" / "SKILL.md"
            legacy_skill.parent.mkdir(parents=True, exist_ok=True)
            legacy_skill.write_text("# stale trae\n", encoding="utf-8")
        elif repo_dir.name == "ChatBlog":
            (repo_dir / "docs").mkdir(parents=True, exist_ok=True)
        elif repo_dir.name == "ChatMemory":
            skills_readme = repo_dir / "Skills" / "README.md"
            skills_readme.parent.mkdir(parents=True, exist_ok=True)
            skills_readme.write_text("# ChatMemory Skills\n", encoding="utf-8")
            for group in ["chatarch", "common", "agents"]:
                skill = repo_dir / "Skills" / group / "demo" / "SKILL.md"
                skill.parent.mkdir(parents=True, exist_ok=True)
                skill.write_text(f"# {group}\n", encoding="utf-8")
        return "cloned"

    monkeypatch.setattr(
        "chatup.setup.workspace.options._clone_or_update_repo",
        fake_clone_or_update,
    )

    result = CliRunner().invoke(
        main,
        [
            "workspace",
            str(workspace_dir),
            "--with-chattool",
            "--with-chatblog",
            "--with-memory",
            "-I",
        ],
    )

    assert result.exit_code == 0, result.output
    assert Path("core/ChatTool") in cloned
    assert Path("core/ChatBlog") in cloned
    assert Path("core/ChatMemory") in cloned
    _assert_link_points_to(
        workspace_dir / "public" / "chatblog",
        workspace_dir / "core" / "ChatBlog" / "docs",
    )
    assert not (workspace_dir / "skills" / "trae").exists()
    for group in ["chatarch", "common", "agents"]:
        _assert_link_points_to(
            workspace_dir / "skills" / group,
            workspace_dir / "core" / "ChatMemory" / "Skills" / group,
        )
    _assert_link_points_to(
        workspace_dir / "skills" / "README.md",
        workspace_dir / "core" / "ChatMemory" / "Skills" / "README.md",
    )
    assert not (workspace_dir / "skills" / "package-development").exists()
    assert not (workspace_dir / "skills" / "package-review").exists()
    local_readme = (workspace_dir / "skills" / "local" / "README.md").read_text(encoding="utf-8")
    assert "chatarch/package-development" in local_readme
    assert "chatarch/package-review" in local_readme
    assert "available under `skills/chatarch/`" in local_readme
    assert "chatarch/package-review are available under skills/chatarch/" in result.output
    assert "Skills README:" in result.output


def test_workspace_extra_repo_reports_missing_git(tmp_path, monkeypatch):
    from chatup.setup.workspace import options

    monkeypatch.setattr(options, "_resolve_git_command", lambda: None)

    with pytest.raises(click.ClickException) as excinfo:
        options._clone_or_update_repo(
            "https://example.invalid/repo.git",
            tmp_path / "workspace" / "core" / "Repo",
            interactive=False,
            can_prompt=False,
        )

    assert "Git executable not found" in str(excinfo.value)


def test_workspace_resolves_windows_git_standard_location(tmp_path, monkeypatch):
    from chatup.setup.workspace import options

    git = tmp_path / "Programs" / "Git" / "cmd" / "git.exe"
    git.parent.mkdir(parents=True)
    git.write_text("fake git", encoding="utf-8")

    monkeypatch.setattr(options.shutil, "which", lambda name: None)
    monkeypatch.setattr(options.os, "name", "nt")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)

    assert options._resolve_git_command() == str(git)


def test_workspace_directory_link_uses_directory_symlink_flag(tmp_path, monkeypatch):
    from chatup.setup.workspace import options

    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    captured = {}

    def fake_symlink_to(self, source_path, target_is_directory=False):
        captured["source"] = source_path
        captured["target_is_directory"] = target_is_directory

    monkeypatch.setattr(Path, "symlink_to", fake_symlink_to)

    options._ensure_symlink(source, target)

    assert captured == {"source": source, "target_is_directory": True}


def test_workspace_directory_link_falls_back_to_windows_junction(tmp_path, monkeypatch):
    from chatup.setup.workspace import options

    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    created = []

    def fail_symlink_to(self, source_path, target_is_directory=False):
        raise OSError("symlink privilege missing")

    def fake_junction(source_path, target_path):
        created.append((source_path, target_path))
        target_path.mkdir()

    monkeypatch.setattr(Path, "symlink_to", fail_symlink_to)
    monkeypatch.setattr(options.os, "name", "nt")
    monkeypatch.setattr(options, "_create_windows_junction", fake_junction)

    options._ensure_symlink(source, target)

    assert created == [(source.resolve(), target)]
    assert target.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="native Windows junctions")
@pytest.mark.parametrize("name", ["space dir", "a&b", "literal%PATH%!name"])
def test_windows_junction_preserves_literal_paths_and_target_data(tmp_path, name):
    from chatup.setup.workspace import options

    source = tmp_path / name
    source.mkdir()
    sentinel = source / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    target = tmp_path / (name + "-link")
    options._create_windows_junction(source, target)
    try:
        assert options._is_windows_reparse_point(target)
        assert target.samefile(source)
        options._ensure_symlink(source, target)
        assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"
    finally:
        options._remove_link_path(target)
    assert sentinel.read_text(encoding="utf-8") == "keep"
