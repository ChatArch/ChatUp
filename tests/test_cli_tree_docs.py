import re
from pathlib import Path

from chatup.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _documented_top_level_commands(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    tree = re.search(r"```text\nchatup\n(?P<body>.*?)```", text, flags=re.DOTALL)
    assert tree is not None, f"{path} has no top-level chatup tree"
    return set(
        re.findall(
            r"^[├└]──\s+([a-z][a-z0-9-]*)\s",
            tree.group("body"),
            flags=re.MULTILINE,
        )
    )


def _documented_reference_commands(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^[|`]--\s+([a-z][a-z0-9-]*)\s", text, flags=re.MULTILINE))


def test_bilingual_cli_tree_matches_registered_click_commands():
    actual = set(main.commands)

    assert _documented_top_level_commands(ROOT / "docs" / "cli-tree.md") == actual
    assert _documented_top_level_commands(ROOT / "docs" / "cli-tree.en.md") == actual
    assert _documented_reference_commands(ROOT / "docs" / "commands.md") == actual
    assert _documented_reference_commands(ROOT / "docs" / "commands.en.md") == actual


def test_mkdocs_material_theme_has_material_icon_renderer():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "name: material" in mkdocs
    assert "pymdownx.emoji" in mkdocs
    assert "material.extensions.emoji.twemoji" in mkdocs
    assert "material.extensions.emoji.to_svg" in mkdocs


def test_cli_tree_is_in_mkdocs_nav_and_backend_contracts_are_complete():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "CLI 树: cli-tree.md" in mkdocs

    required = {
        "chatup chrome-for-testing",
        "chatup chromedriver",
        "chatup playwright",
        "install",
        "list",
        "show",
        "path",
        "doctor",
        "remove",
        "gc",
        "--version",
        "--channel",
        "--home",
        "--platform",
        "--sha256",
        "--force",
        "--doctor / --no-doctor",
        "--match-browser",
        "--match-cft-version",
        "--dry-run|--apply",
        "--yes",
        "CHATARCH_AUTO_PROMPT",
        "chatup.chrome_for_testing",
        "chatup.chromedriver",
        "chatup.playwright",
        "-i / -I",
    }
    for name in ("cli-tree.md", "cli-tree.en.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        missing = sorted(item for item in required if item not in text)
        assert not missing, f"{name} is missing backend contract terms: {missing}"
        assert "\nchatup chrome\n" not in text
        assert "from chatup.chrome import" not in text
