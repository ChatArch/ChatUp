from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_publish_workflow_matches_active_any_environment_publisher():
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )

    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "environment: pypi" not in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "refs/remotes/origin/main" in workflow
    assert "workflow_dispatch" not in workflow
    assert "Release workflow must run from a tag ref" in workflow
    assert "GITHUB_REF_TYPE" in workflow
    assert "GITHUB_REF_NAME" in workflow
    for secret_name in (
        "PYPI_API_TOKEN",
        "PYPI_TOKEN",
        "TWINE_USERNAME",
        "TWINE_PASSWORD",
        "secrets.PYPI_",
    ):
        assert secret_name not in workflow
