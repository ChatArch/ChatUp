import re
from pathlib import Path

from chatup.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _documented_top_level_commands(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^[├└]──\s+([a-z][a-z0-9-]*)\s", text, flags=re.MULTILINE))


def _documented_reference_commands(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^[|`]--\s+([a-z][a-z0-9-]*)\s", text, flags=re.MULTILINE))


def test_bilingual_cli_tree_matches_registered_click_commands():
    actual = set(main.commands)

    assert _documented_top_level_commands(ROOT / "docs" / "cli-tree.md") == actual
    assert _documented_top_level_commands(ROOT / "docs" / "cli-tree.en.md") == actual
    assert _documented_reference_commands(ROOT / "docs" / "commands.md") == actual
    assert _documented_reference_commands(ROOT / "docs" / "commands.en.md") == actual


def test_cli_tree_is_in_mkdocs_nav_and_chrome_contract_is_complete():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "CLI 树: cli-tree.md" in mkdocs

    required = {
        "--version",
        "--home",
        "--platform",
        "--sha256",
        "--force",
        "--doctor / --no-doctor",
        "--output text|json",
        "-i / -I",
    }
    for name in ("cli-tree.md", "cli-tree.en.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        missing = sorted(item for item in required if item not in text)
        assert not missing, f"{name} is missing Chrome options: {missing}"
