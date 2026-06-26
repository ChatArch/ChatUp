from pathlib import Path

from click.testing import CliRunner

from chatup.cli import main


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
    assert public_link.is_symlink()
    assert public_link.resolve() == docs_dir
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
    assert public_link.is_symlink()
    assert public_link.resolve() == workspace_dir / "core" / "ChatBlog" / "docs"
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
    assert (workspace_dir / "public" / "chatblog").is_symlink()
    assert not (workspace_dir / "skills" / "trae").exists()
    assert (workspace_dir / "skills" / "chatarch").is_symlink()
    assert (workspace_dir / "skills" / "common").is_symlink()
    assert (workspace_dir / "skills" / "agents").is_symlink()
    assert (workspace_dir / "skills" / "README.md").is_symlink()
    assert (workspace_dir / "skills" / "README.md").resolve() == workspace_dir / "core" / "ChatMemory" / "Skills" / "README.md"
    assert not (workspace_dir / "skills" / "package-development").exists()
    assert not (workspace_dir / "skills" / "package-review").exists()
    local_readme = (workspace_dir / "skills" / "local" / "README.md").read_text(encoding="utf-8")
    assert "chatarch/package-development" in local_readme
    assert "chatarch/package-review" in local_readme
    assert "available under `skills/chatarch/`" in local_readme
    assert "chatarch/package-review are available under skills/chatarch/" in result.output
    assert "Skills README:" in result.output
