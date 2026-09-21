import os
import shlex
import shutil
import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from chatup.cli import main
from chatup.setup import uv as setup
from chatup.utils import platforming

BEGIN = "# >>> chatuv activate >>>"
END = "# <<< chatuv activate <<<"


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / ".chatarch"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(platforming, "WINDOWS", False)
    monkeypatch.setattr(setup, "ensure_uv_installed", lambda: "uv")
    monkeypatch.setattr(setup, "is_chatarch_python_ready", lambda *args: True)


@pytest.mark.parametrize("names", [(), (".bashrc",), (".zshrc",), (".bashrc", ".zshrc")])
def test_ready_env_updates_only_existing_rc_files(tmp_path, names):
    for name in names:
        (tmp_path / name).write_text("# user config\n", encoding="utf-8")
    target = tmp_path / "venv"
    result = setup.setup_uv(venv=str(target))
    assert result["status"] == "ready"
    for name in (".bashrc", ".zshrc"):
        rc = tmp_path / name
        if name in names:
            text = rc.read_text(encoding="utf-8")
            assert text.startswith("# user config\n")
            assert BEGIN in text and END in text
            assert "source " + shlex.quote(str(target / "bin" / "activate")) in text
        else:
            assert not rc.exists()
    assert sorted(result["activation"]["updated"]) == sorted(str(tmp_path / name) for name in names)


@pytest.mark.parametrize("force", [False, True])
def test_created_env_also_updates_rc(tmp_path, monkeypatch, force):
    rc = tmp_path / ".bashrc"
    rc.write_text("# keep", encoding="utf-8")
    readiness = iter([False, True])
    monkeypatch.setattr(setup, "is_chatarch_python_ready", lambda *args: next(readiness))
    monkeypatch.setattr(setup, "create_chatarch_python_env", lambda *args, **kwargs: None)
    result = setup.setup_uv(venv=str(tmp_path / "venv"), force=force)
    assert result["status"] == "created"
    assert rc.read_text(encoding="utf-8").startswith("# keep\n")
    assert BEGIN in rc.read_text(encoding="utf-8")


def test_existing_chatuv_block_is_retargeted_without_touching_surroundings(tmp_path):
    rc = tmp_path / ".zshrc"
    prefix = "# user prefix\n\n\n"
    suffix = "\n\n# user suffix\n\n"
    old_block = BEGIN + "\nsource /old/venv/bin/activate\n" + END + "\n"
    rc.write_bytes((prefix + old_block + suffix).encode("utf-8"))
    target = tmp_path / "new venv"
    setup.setup_uv(venv=str(target))
    first = rc.read_bytes()
    first_mtime = rc.stat().st_mtime_ns
    result = setup.setup_uv(venv=str(target))
    assert rc.read_bytes() == first
    assert rc.stat().st_mtime_ns == first_mtime
    text = first.decode()
    assert text.startswith(prefix) and text.endswith(suffix)
    assert text.count(BEGIN) == text.count(END) == 1
    assert "/old/venv" not in text
    assert str(target / "bin" / "activate") in text
    assert result["activation"]["updated"] == []
    assert result["activation"]["unchanged"] == [str(rc)]


@pytest.mark.parametrize("args,enabled", [([], True), (["--activate"], True), (["--no-activate"], False)])
def test_cli_activation_switch_defaults_on(tmp_path, args, enabled):
    rc = tmp_path / ".bashrc"
    rc.write_text("# original\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["uv", "--venv", str(tmp_path / "venv"), *args])
    assert result.exit_code == 0, result.output
    assert (BEGIN in rc.read_text(encoding="utf-8")) is enabled


def test_help_documents_activation_switch():
    result = CliRunner().invoke(main, ["uv", "--help"])
    assert result.exit_code == 0
    assert "--activate / --no-activate" in result.output
    assert "[default: activate]" in " ".join(result.output.split())


def test_opt_out_leaves_existing_activation_unchanged(tmp_path):
    rc = tmp_path / ".bashrc"
    original = BEGIN + "\nsource /old/bin/activate\n" + END + "\n"
    rc.write_text(original, encoding="utf-8")
    result = setup.setup_uv(venv=str(tmp_path / "new"), shell_activate=False)
    assert rc.read_text(encoding="utf-8") == original
    assert result["activation"] is None


def test_windows_skips_rc_updates(tmp_path, monkeypatch):
    rc = tmp_path / ".bashrc"
    rc.write_text("# unchanged\n", encoding="utf-8")
    monkeypatch.setattr(platforming, "WINDOWS", True)
    result = setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.read_text(encoding="utf-8") == "# unchanged\n"
    assert not (tmp_path / ".zshrc").exists()
    assert result["activation"]["skipped"] is True


def test_failed_venv_verification_does_not_modify_rc(tmp_path, monkeypatch):
    rc = tmp_path / ".bashrc"
    rc.write_text("# unchanged\n", encoding="utf-8")
    monkeypatch.setattr(setup, "is_chatarch_python_ready", lambda *args: False)
    monkeypatch.setattr(setup, "create_chatarch_python_env", lambda *args, **kwargs: None)
    with pytest.raises(click.ClickException, match="not verified"):
        setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.read_text(encoding="utf-8") == "# unchanged\n"


def test_relative_venv_is_persisted_as_absolute_path(tmp_path, monkeypatch):
    rc = tmp_path / ".bashrc"
    rc.touch()
    monkeypatch.chdir(tmp_path)
    setup.setup_uv(venv="relative venv")
    assert shlex.quote(str(tmp_path / "relative venv" / "bin" / "activate")) in rc.read_text()


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_written_block_can_be_sourced_with_quoted_paths(tmp_path, shell):
    executable = shutil.which(shell)
    if os.name == "nt" or not executable:
        pytest.skip("native POSIX shell required")
    target = tmp_path / "space ' $literal; venv"
    (target / "bin").mkdir(parents=True)
    (target / "bin" / "activate").write_text("export CHATUP_ACTIVATED=yes\n")
    rc = tmp_path / ("." + shell + "rc")
    rc.touch()
    setup.setup_uv(venv=str(target))
    command = 'source "$1"; test "$CHATUP_ACTIVATED" = yes'
    result = subprocess.run([executable, "-c", command, "shell-test", str(rc)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_rc_newlines_are_preserved(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_bytes(b"# keep CRLF\r\n")
    setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.read_bytes().startswith(b"# keep CRLF\r\n")
    assert BEGIN.encode() in rc.read_bytes()


def test_malformed_managed_block_is_not_overwritten(tmp_path):
    rc = tmp_path / ".bashrc"
    original = BEGIN + "\n# user content without closing marker\n"
    rc.write_text(original)
    with pytest.raises(click.ClickException, match="activation block"):
        setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.read_text() == original


@pytest.mark.parametrize("failure", ["write", "flush", "fsync", "replace"])
def test_failed_rc_write_preserves_original_bytes(tmp_path, monkeypatch, failure):
    import errno

    rc = tmp_path / ".bashrc"
    original = b"# retained settings\nexport KEEP=yes\n"
    rc.write_bytes(original)
    original_open = Path.open
    original_fdopen = os.fdopen

    def fail(*args, **kwargs):
        raise OSError(errno.ENOSPC, "simulated full disk")

    class FailingWriter:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            try:
                if failure == "flush":
                    fail()
            finally:
                self.stream.close()

        def write(self, data):
            if failure == "write":
                fail()
            return self.stream.write(data)

        def flush(self):
            if failure == "flush":
                fail()
            return self.stream.flush()

        def fileno(self):
            return self.stream.fileno()

    def failing_open(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        return FailingWriter(stream) if "w" in mode else stream

    def failing_fdopen(fd, mode="r", *args, **kwargs):
        stream = original_fdopen(fd, mode, *args, **kwargs)
        return FailingWriter(stream) if "w" in mode else stream

    monkeypatch.setattr(Path, "open", failing_open)
    monkeypatch.setattr(os, "fdopen", failing_fdopen)
    if failure in ("fsync", "replace"):
        monkeypatch.setattr(os, failure, fail)
    with pytest.raises(click.ClickException, match="activation block"):
        setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.read_bytes() == original
    assert sorted(path.name for path in tmp_path.iterdir()) == [".bashrc"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlinks and permissions")
def test_rc_symlink_and_target_permissions_are_preserved(tmp_path):
    import stat

    target = tmp_path / "dotfiles" / "bashrc"
    target.parent.mkdir()
    target.write_bytes(b"# dotfiles content\n")
    target.chmod(0o640)
    rc = tmp_path / ".bashrc"
    rc.symlink_to(target)
    setup.setup_uv(venv=str(tmp_path / "venv"))
    assert rc.is_symlink() and rc.resolve() == target
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert target.read_text().startswith("# dotfiles content\n")
    assert BEGIN in target.read_text()
    assert list(target.parent.iterdir()) == [target]


def test_same_version_missing_pip_repair_updates_rc(tmp_path, monkeypatch):
    target = tmp_path / "venv"
    target.mkdir()
    rc = tmp_path / ".bashrc"
    rc.touch()
    readiness = iter([False, True])
    calls = []
    monkeypatch.setattr(setup, "is_chatarch_python_ready", lambda *args: next(readiness))
    monkeypatch.setattr(setup, "_python_minor_version", lambda path: "3.12")
    monkeypatch.setattr(setup, "create_chatarch_python_env", lambda *args, **kwargs: calls.append((args, kwargs)))
    result = setup.setup_uv(venv=str(target))
    assert result["status"] == "created"
    assert calls == [(("uv", target, "3.12"), {"force": False})]
    assert BEGIN in rc.read_text()
