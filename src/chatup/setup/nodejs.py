from __future__ import annotations

from collections import deque
import hashlib
from importlib import resources
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile
import click

from chatup.interaction import (
    BACK_VALUE,
    abort_if_force_without_tty,
    ask_confirm,
    ask_text,
    resolve_interactive_mode,
)
from chatup.const import CHATARCH_HOME
from chatup.utils.custom_logger import setup_logger
from chatup.utils.platforming import is_windows

BUNDLED_NVM_VERSION = "v0.40.3"
MIN_NODEJS_MAJOR = 20
NVM_INIT_BEGIN = "# >>> chatup nvm >>>"
NVM_INIT_END = "# <<< chatup nvm <<<"
WINDOWS_NODE_RELEASE_INDEX = "https://nodejs.org/dist/index.json"
WINDOWS_NODE_DOWNLOAD_TIMEOUT = 60
WINDOWS_NODE_MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
WINDOWS_NODE_MAX_ARCHIVE_MEMBERS = 20_000
WINDOWS_NODE_MAX_UNCOMPRESSED_BYTES = 768 * 1024 * 1024
logger = setup_logger("setup_nodejs")


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_nodejs", log_level=str(log_level).upper())
    return logger


def _run_bash(command, *, env=None):
    return subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        env=env,
    )


def _run_bash_with_output_tail(command, tail_lines=80, *, env=None):
    process = subprocess.Popen(
        ["bash", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    tail = deque(maxlen=tail_lines)
    assert process.stdout is not None
    for line in process.stdout:
        tail.append(line.rstrip("\n"))
    return subprocess.CompletedProcess(
        process.args,
        process.wait(),
        "\n".join(tail).strip(),
        "",
    )


def _get_cmd_output(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def _get_bash_output(command):
    result = _run_bash(command)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def _parse_node_major(version_text):
    if not version_text:
        return None
    text = str(version_text).strip()
    if text.startswith("v"):
        text = text[1:]
    major = text.split(".", 1)[0]
    if not major.isdigit():
        return None
    return int(major)


def _build_runtime(
    node_bin,
    npm_bin,
    node_version,
    npm_version,
    source,
    *,
    npm_cli=None,
):
    return {
        "node_bin": node_bin,
        "npm_bin": npm_bin,
        "npm_cli": npm_cli,
        "node_version": node_version,
        "npm_version": npm_version,
        "node_major": _parse_node_major(node_version),
        "source": source,
    }


def _npm_cli_candidates(node_bin) -> tuple[Path, ...]:
    if not node_bin:
        return ()
    node_path = Path(str(node_bin)).expanduser()
    return (
        node_path.parent / "node_modules" / "npm" / "bin" / "npm-cli.js",
        node_path.parent.parent / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js",
    )


def _find_npm_cli(node_bin) -> str | None:
    for candidate in _npm_cli_candidates(node_bin):
        if candidate.is_file():
            return str(candidate)

    if not node_bin:
        return None
    resolved = _get_cmd_output(
        [str(node_bin), "-p", "require.resolve('npm/bin/npm-cli.js')"]
    )
    candidate = Path(resolved).expanduser() if resolved else None
    if candidate is not None and candidate.is_file():
        return str(candidate)
    return None


def _detect_nodejs_runtime_from_path():
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    node_version = _get_cmd_output([node_bin, "-v"]) if node_bin else ""
    npm_cli = _find_npm_cli(node_bin) if is_windows() and node_bin else None
    if is_windows() and node_bin and npm_cli:
        npm_version = _get_cmd_output([node_bin, npm_cli, "--version"])
    else:
        npm_version = _get_cmd_output([npm_bin, "-v"]) if npm_bin else ""
    return _build_runtime(
        node_bin,
        npm_bin,
        node_version,
        npm_version,
        "path",
        npm_cli=npm_cli,
    )


def _detect_nodejs_runtime_from_nvm():
    if is_windows():
        return _build_runtime("", "", "", "", "nvm")
    nvm_sh = Path.home() / ".nvm" / "nvm.sh"
    if not nvm_sh.exists():
        return _build_runtime("", "", "", "", "nvm")

    prefix = 'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    node_bin = _get_bash_output(prefix + "command -v node")
    npm_bin = _get_bash_output(prefix + "command -v npm")
    node_version = _get_bash_output(prefix + "node -v") if node_bin else ""
    npm_version = _get_bash_output(prefix + "npm -v") if npm_bin else ""
    return _build_runtime(node_bin, npm_bin, node_version, npm_version, "nvm")


def _windows_node_home() -> Path:
    return Path(CHATARCH_HOME).expanduser() / "nodejs"


def _windows_node_runtime_dir(name: str) -> Path:
    if not re.fullmatch(r"node-v\d+\.\d+\.\d+-win-(?:x64|arm64)", name):
        raise click.ClickException(f"Unsupported managed Node.js runtime name: {name}")
    return _windows_node_home() / "runtimes" / name


def _windows_node_platform() -> str:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64", "x64"}:
        return "win-x64"
    if machine in {"arm64", "aarch64"}:
        return "win-arm64"
    raise click.ClickException(
        f"Unsupported Windows architecture for portable Node.js: {platform.machine()}"
    )


def _read_url_bytes(url: str, *, max_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp Node bootstrap"})
    with urllib.request.urlopen(request, timeout=WINDOWS_NODE_DOWNLOAD_TIMEOUT) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > max_bytes:
            raise click.ClickException(f"Official Node.js response exceeds {max_bytes} bytes.")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise click.ClickException(f"Official Node.js response exceeds {max_bytes} bytes.")
            chunks.append(chunk)
    return b"".join(chunks)


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ChatUp Node bootstrap"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=WINDOWS_NODE_DOWNLOAD_TIMEOUT) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > WINDOWS_NODE_MAX_DOWNLOAD_BYTES:
            raise click.ClickException(
                f"Official Node.js archive exceeds {WINDOWS_NODE_MAX_DOWNLOAD_BYTES} bytes."
            )
        total = 0
        with destination.open("xb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > WINDOWS_NODE_MAX_DOWNLOAD_BYTES:
                    raise click.ClickException(
                        f"Official Node.js archive exceeds {WINDOWS_NODE_MAX_DOWNLOAD_BYTES} bytes."
                    )
                handle.write(chunk)


def _official_node_sha256(shasums: str, archive_name: str) -> str | None:
    for line in shasums.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, candidate = parts
        if candidate.lstrip("*") != archive_name:
            continue
        if re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return digest.lower()
    return None


def _resolve_windows_node_release(*, min_major: int) -> dict[str, str]:
    platform_name = _windows_node_platform()
    try:
        payload = json.loads(
            _read_url_bytes(WINDOWS_NODE_RELEASE_INDEX, max_bytes=8 * 1024 * 1024)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise click.ClickException(
            f"Could not read the official Node.js release index: {exc}"
        ) from exc

    if not isinstance(payload, list):
        raise click.ClickException("Official Node.js release index has an unexpected format.")

    asset_suffix = f"{platform_name}-zip"
    for release in payload:
        if not isinstance(release, dict) or not release.get("lts"):
            continue
        version = release.get("version")
        if not isinstance(version, str) or not re.fullmatch(r"v\d+\.\d+\.\d+", version):
            continue
        major = _parse_node_major(version)
        if major is None or major < min_major:
            continue
        files = release.get("files")
        if isinstance(files, list) and asset_suffix not in files:
            continue
        archive_name = f"node-{version}-{platform_name}.zip"
        base_url = f"https://nodejs.org/dist/{version}"
        try:
            shasums = _read_url_bytes(
                f"{base_url}/SHASUMS256.txt", max_bytes=2 * 1024 * 1024
            ).decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise click.ClickException(
                f"Could not read the official Node.js SHA-256 manifest: {exc}"
            ) from exc
        checksum = _official_node_sha256(shasums, archive_name)
        if checksum:
            return {
                "version": version,
                "archive_name": archive_name,
                "archive_url": f"{base_url}/{archive_name}",
                "sha256": checksum,
            }

    raise click.ClickException(
        f"No official Windows Node.js LTS ZIP satisfying Node.js >= {min_major} was found."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract_node_zip(archive: Path, destination: Path, archive_root: str) -> None:
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > WINDOWS_NODE_MAX_ARCHIVE_MEMBERS:
            raise click.ClickException("Official Node.js archive contains too many entries.")
        total_size = sum(member.file_size for member in members)
        if total_size > WINDOWS_NODE_MAX_UNCOMPRESSED_BYTES:
            raise click.ClickException("Official Node.js archive expands beyond the safe size limit.")
        for member in members:
            name = member.filename
            if "\\" in name:
                raise click.ClickException(f"unsafe archive path: {name}")
            member_path = PurePosixPath(name)
            parts = member_path.parts
            if (
                not parts
                or member_path.is_absolute()
                or ".." in parts
                or "." in parts
                or ":" in parts[0]
                or parts[0] != archive_root
            ):
                raise click.ClickException(f"unsafe archive path: {name}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise click.ClickException(f"unsafe archive path: symbolic link {name}")
            target = destination.joinpath(*parts)
            target_resolved = target.resolve()
            if not target_resolved.is_relative_to(destination_root):
                raise click.ClickException(f"unsafe archive path: {name}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def _managed_windows_runtime_from_dir(runtime_dir: Path) -> dict:
    if runtime_dir.is_symlink():
        return _build_runtime("", "", "", "", "chatarch")
    node_bin = runtime_dir / "node.exe"
    npm_cli = runtime_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
    if not node_bin.is_file() or not npm_cli.is_file():
        return _build_runtime("", "", "", "", "chatarch")
    node_version = _get_cmd_output([str(node_bin), "-v"])
    npm_version = _get_cmd_output([str(node_bin), str(npm_cli), "--version"])
    return _build_runtime(
        str(node_bin),
        str(node_bin.parent / "npm.cmd"),
        node_version,
        npm_version,
        "chatarch",
        npm_cli=str(npm_cli),
    )


def _current_windows_runtime_name() -> str | None:
    current_path = _windows_node_home() / "current.json"
    if current_path.is_symlink() or not current_path.is_file():
        return None
    try:
        payload = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    name = payload.get("runtime") if isinstance(payload, dict) else None
    return name if isinstance(name, str) else None


def _write_current_windows_runtime(runtime_dir: Path, version: str) -> None:
    root = _windows_node_home()
    root.mkdir(parents=True, exist_ok=True)
    payload = {"version": version, "runtime": runtime_dir.name}
    current_path = root / "current.json"
    fd, temp_name = tempfile.mkstemp(prefix=".current-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, current_path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _detect_nodejs_runtime_from_managed_windows_home():
    if not is_windows():
        return _build_runtime("", "", "", "", "chatarch")
    runtimes_dir = _windows_node_home() / "runtimes"
    candidates: list[Path] = []
    current_name = _current_windows_runtime_name()
    if current_name:
        try:
            candidates.append(_windows_node_runtime_dir(current_name))
        except click.ClickException:
            pass
    if runtimes_dir.is_dir() and not runtimes_dir.is_symlink():
        candidates.extend(
            sorted(
                (
                    path
                    for path in runtimes_dir.iterdir()
                    if path.is_dir() and not path.is_symlink()
                ),
                reverse=True,
            )
        )
    seen: set[Path] = set()
    for runtime_dir in candidates:
        resolved = runtime_dir.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        runtime = _managed_windows_runtime_from_dir(runtime_dir)
        if has_required_nodejs(runtime=runtime):
            return runtime
    return _build_runtime("", "", "", "", "chatarch")


def _bootstrap_windows_node_lts(*, min_major: int) -> dict:
    if not is_windows():
        raise click.ClickException("The Windows Node.js bootstrap is only available on Windows.")
    release = _resolve_windows_node_release(min_major=min_major)
    version = release.get("version", "")
    archive_name = release.get("archive_name", "")
    archive_url = release.get("archive_url", "")
    expected_sha256 = release.get("sha256", "").lower()
    archive_root = archive_name.removesuffix(".zip")
    release_major = _parse_node_major(version)
    if release_major is None or release_major < min_major:
        raise click.ClickException(
            f"Official Node.js LTS release {version or 'unknown'} does not satisfy Node.js >= {min_major}."
        )
    if (
        not re.fullmatch(r"node-v\d+\.\d+\.\d+-win-(?:x64|arm64)\.zip", archive_name)
        or not archive_url.startswith("https://nodejs.org/dist/")
        or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
    ):
        raise click.ClickException("Official Node.js release metadata is invalid.")

    runtime_dir = _windows_node_runtime_dir(archive_root)
    existing = _managed_windows_runtime_from_dir(runtime_dir)
    if has_required_nodejs(min_major=min_major, runtime=existing):
        _write_current_windows_runtime(runtime_dir, version)
        return existing
    if runtime_dir.exists() or runtime_dir.is_symlink():
        raise click.ClickException(
            f"Managed Node.js runtime is incomplete and will not be overwritten: {runtime_dir}"
        )

    runtimes_dir = runtime_dir.parent
    runtimes_dir.mkdir(parents=True, exist_ok=True)
    if runtimes_dir.is_symlink():
        raise click.ClickException(f"Refusing symlinked managed runtime directory: {runtimes_dir}")
    staging = Path(tempfile.mkdtemp(prefix=".node-bootstrap-", dir=runtimes_dir))
    try:
        archive = staging / archive_name
        _download_file(archive_url, archive)
        observed_sha256 = _sha256_file(archive)
        if observed_sha256 != expected_sha256:
            raise click.ClickException("Node.js archive SHA-256 mismatch; refusing extraction.")
        _safe_extract_node_zip(archive, staging, archive_root)
        extracted_runtime = staging / archive_root
        if not extracted_runtime.is_dir() or extracted_runtime.is_symlink():
            raise click.ClickException("Official Node.js archive did not contain the expected runtime root.")
        os.replace(extracted_runtime, runtime_dir)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    runtime = _managed_windows_runtime_from_dir(runtime_dir)
    if not has_required_nodejs(min_major=min_major, runtime=runtime):
        raise click.ClickException(
            f"Managed Node.js runtime does not satisfy Node.js >= {min_major} after extraction."
        )
    _write_current_windows_runtime(runtime_dir, version)
    return runtime


def _runtime_score(runtime):
    score = 0
    if runtime.get("node_bin"):
        score += 1
    if runtime.get("npm_bin"):
        score += 1
    node_major = runtime.get("node_major")
    if node_major is not None:
        score += 2 + node_major
    return score


def _detect_nodejs_runtime():
    path_runtime = _detect_nodejs_runtime_from_path()
    managed_runtime = _detect_nodejs_runtime_from_managed_windows_home()
    nvm_runtime = _detect_nodejs_runtime_from_nvm()
    best = path_runtime
    if (
        is_windows()
        and managed_runtime.get("node_bin")
        and path_runtime.get("node_bin")
        and os.path.normcase(str(Path(managed_runtime["node_bin"]).resolve()))
        == os.path.normcase(str(Path(path_runtime["node_bin"]).resolve()))
    ):
        # PATH exposure must not strip the identity/prefix of our own runtime.
        best = managed_runtime
    for runtime in (managed_runtime, nvm_runtime):
        if _runtime_score(runtime) > _runtime_score(best):
            best = runtime
    return best


def _nodejs_requirement_message(runtime, min_major):
    node_version = runtime.get("node_version") or "not found"
    npm_version = runtime.get("npm_version") or "not found"
    install_hint = (
        "Run `chatup nodejs` to bootstrap an official portable Node.js LTS runtime under ChatArch home."
        if is_windows()
        else "Please run: chatup nodejs"
    )
    if not runtime.get("node_bin") or not runtime.get("npm_bin"):
        return (
            f"Node.js >= {min_major} and npm are required, but node/npm were not found. "
            f"{install_hint}"
        )
    node_major = runtime.get("node_major")
    if node_major is None:
        return f"Node.js >= {min_major} is required, but the current Node.js version could not be parsed: {node_version}"
    if node_major < min_major:
        return (
            f"Node.js >= {min_major} is required, but the current runtime is "
            f"{node_version} with npm {npm_version}."
        )
    return ""


def has_required_nodejs(min_major=MIN_NODEJS_MAJOR, runtime=None):
    runtime = runtime or _detect_nodejs_runtime()
    node_major = runtime.get("node_major")
    return bool(
        runtime.get("node_bin")
        and runtime.get("npm_bin")
        and (not is_windows() or runtime.get("npm_cli"))
        and node_major is not None
        and node_major >= min_major
    )


def ensure_nodejs_requirement(
    min_major=MIN_NODEJS_MAJOR, interactive=None, can_prompt=False, log_level="INFO"
):
    _configure_logger(log_level)
    runtime = _detect_nodejs_runtime()
    logger.info(f"Checking Node.js runtime requirement (>= {min_major})")
    if has_required_nodejs(min_major=min_major, runtime=runtime):
        return runtime

    message = _nodejs_requirement_message(runtime, min_major=min_major)
    logger.warning(message)

    if is_windows():
        runtime = _bootstrap_windows_node_lts(min_major=min_major)
        if has_required_nodejs(min_major=min_major, runtime=runtime):
            return runtime
        raise click.ClickException(
            f"Managed Node.js runtime does not satisfy Node.js >= {min_major}."
        )

    if interactive is not False and can_prompt:
        install_now = ask_confirm(
            f"{message} Install or upgrade Node.js now via `chatup nodejs`?",
            default=True,
        )
        if install_now == BACK_VALUE:
            raise click.Abort()
        if install_now:
            setup_nodejs(interactive=True, log_level=log_level)
            runtime = _detect_nodejs_runtime()
            if has_required_nodejs(min_major=min_major, runtime=runtime):
                return runtime
            logger.error("Node.js requirement still not satisfied after setup")
            click.echo(
                f"Node.js >= {min_major} is still not available after setup. Please verify your shell environment.",
                err=True,
            )
            raise click.Abort()

    click.echo(message, err=True)
    click.echo("Please run: chatup nodejs", err=True)
    raise click.Abort()


def npm_command_for_runtime(runtime, args) -> list[str]:
    normalized_args = [str(arg) for arg in args]
    if is_windows():
        node_bin = runtime.get("node_bin")
        npm_cli = runtime.get("npm_cli") or _find_npm_cli(node_bin)
        if not node_bin or not npm_cli:
            raise click.ClickException(
                "A Node.js runtime with npm-cli.js is required. Run: chatup nodejs"
            )
        return [str(node_bin), str(npm_cli), *normalized_args]

    npm_bin = runtime.get("npm_bin")
    if not npm_bin:
        raise click.ClickException("npm is required. Please run: chatup nodejs")
    return [str(npm_bin), *normalized_args]


def node_runtime_env(runtime, env=None) -> dict[str, str]:
    merged = os.environ.copy() if env is None else dict(env)
    node_bin = runtime.get("node_bin")
    if not node_bin:
        return merged
    node_dir = str(Path(str(node_bin)).expanduser().resolve().parent)
    if is_windows() and ";" in node_dir:
        raise click.ClickException(
            "Node.js runtime directory contains the Windows PATH separator ';'. "
            "Choose a ChatArch home/runtime path without semicolons."
        )
    managed_npm_prefix = None
    if is_windows() and runtime.get("source") == "chatarch":
        managed_npm_prefix = str(_windows_node_home() / "npm")
        merged["NPM_CONFIG_PREFIX"] = managed_npm_prefix
    current_path = merged.get("PATH", "")
    current_items = [item for item in current_path.split(os.pathsep) if item]
    path_prefixes = [node_dir]
    if managed_npm_prefix:
        path_prefixes.append(managed_npm_prefix)
    normalized_prefixes = {
        os.path.normcase(os.path.normpath(path)) for path in path_prefixes
    }
    filtered_items = [
        item
        for item in current_items
        if os.path.normcase(os.path.normpath(item)) not in normalized_prefixes
    ]
    merged["PATH"] = os.pathsep.join([*path_prefixes, *filtered_items])
    return merged


def run_npm_command(args, cwd=None, env=None):
    quoted_args = " ".join(shlex.quote(str(arg)) for arg in args)
    click.echo(f"Running: npm {quoted_args}")
    runtime = _detect_nodejs_runtime()
    command_parts = npm_command_for_runtime(runtime, args)
    child_env = node_runtime_env(runtime, env)
    if runtime.get("source") == "nvm":
        cwd_prefix = (
            f"cd {shlex.quote(str(cwd))} && " if cwd is not None else ""
        )
        npm_command = command_parts[0]
        command = (
            'export NVM_DIR="$HOME/.nvm" && '
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
            f"{cwd_prefix}"
            f"{shlex.quote(npm_command)} {quoted_args}"
        )
        return _run_bash(command, env=child_env)
    return subprocess.run(
        command_parts,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=child_env,
    )


def get_global_npm_package_version(package_name):
    result = run_npm_command(["list", "-g", package_name, "--depth=0", "--json"])
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        return None
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        return None
    package = dependencies.get(package_name)
    if not isinstance(package, dict):
        return None
    version = package.get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    return version.strip()


def should_install_global_npm_package(
    package_name, display_name, interactive=None, can_prompt=False, default_update=False
):
    version = get_global_npm_package_version(package_name)
    if not version:
        return True

    click.echo(f"{display_name} already installed: {version}")
    if interactive is not False and can_prompt:
        update_now = ask_confirm(
            f"Update {display_name} now via npm install -g?",
            default=default_update,
        )
        if update_now == BACK_VALUE:
            raise click.Abort()
        if update_now:
            return True
        click.echo(f"Skip updating {display_name}.")
        return False

    click.echo(f"Skip npm install for {display_name}. Use -i to confirm an update.")
    return False


def _replace_managed_block(path, begin_marker, end_marker, block):
    content = ""
    if path.exists():
        content = path.read_text(encoding="utf-8")

    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)
    if begin_idx != -1 and end_idx != -1 and end_idx >= begin_idx:
        end_idx += len(end_marker)
        if end_idx < len(content) and content[end_idx : end_idx + 1] == "\n":
            end_idx += 1
        content = content[:begin_idx] + content[end_idx:]

    content = content.rstrip("\n")
    if block:
        if content:
            content = content + "\n\n" + block.rstrip("\n")
        else:
            content = block.rstrip("\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + ("\n" if content else ""), encoding="utf-8")


def _read_bundled_nvm_script():
    return (
        resources.files("chatup.setup")
        .joinpath("assets/nvm.sh")
        .read_text(encoding="utf-8")
    )


def _render_nvm_init_block():
    lines = [
        NVM_INIT_BEGIN,
        'export NVM_DIR="$HOME/.nvm"',
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
        NVM_INIT_END,
    ]
    return "\n".join(lines) + "\n"


def _resolve_shell_rc_targets(interactive=False):
    from chatup.setup.shell_rc import (
        resolve_shell_rc,
        resolve_target_shells,
        select_target_shells_interactively,
    )

    shell_names = resolve_target_shells(None)
    if interactive:
        shell_names = select_target_shells_interactively(shell_names)
        if shell_names == BACK_VALUE:
            raise click.Abort()

    if not shell_names:
        click.echo("No shells selected for nvm init update.", err=True)
        raise click.Abort()

    return [(shell_name, resolve_shell_rc(shell_name)) for shell_name in shell_names]


def _install_bundled_nvm(nvm_sh, shell_targets):
    logger.info(f"Writing bundled nvm.sh ({BUNDLED_NVM_VERSION}) to {nvm_sh}")
    nvm_sh.parent.mkdir(parents=True, exist_ok=True)
    nvm_sh.write_text(_read_bundled_nvm_script(), encoding="utf-8")
    nvm_sh.chmod(0o755)
    block = _render_nvm_init_block()
    for _, shell_rc in shell_targets:
        _replace_managed_block(shell_rc, NVM_INIT_BEGIN, NVM_INIT_END, block)


def _echo_recent_output(result, heading):
    output = (result.stdout or "").strip()
    if not output:
        return
    click.echo(heading, err=True)
    click.echo(output, err=True)


def setup_nodejs(interactive=None, log_level="INFO"):
    _configure_logger(log_level)
    logger.info("Start nodejs setup")
    usage = "Usage: chatup nodejs [-i|-I]"
    interactive, can_prompt, force_interactive, _, need_prompt = (
        resolve_interactive_mode(
            interactive=interactive,
            auto_prompt_condition=False,
        )
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    runtime = _detect_nodejs_runtime()
    if is_windows():
        if has_required_nodejs(runtime=runtime):
            click.echo(f"Node.js already installed: {runtime['node_version']}")
            click.echo(f"npm already installed: {runtime['npm_version']}")
            if runtime.get("source") == "chatarch":
                click.echo("ChatUp reuses ChatArch-managed node/npm on Windows.")
            else:
                click.echo("ChatUp reuses node/npm from PATH on Windows.")
            return runtime
        click.echo(
            "No suitable Windows Node.js runtime was found; bootstrapping an official portable LTS ZIP under ChatArch home."
        )
        runtime = _bootstrap_windows_node_lts(min_major=MIN_NODEJS_MAJOR)
        if not has_required_nodejs(runtime=runtime):
            raise click.ClickException(
                f"Managed Node.js runtime does not satisfy Node.js >= {MIN_NODEJS_MAJOR}."
            )
        click.echo(f"ChatArch-managed Node.js ready: {runtime['node_version']}")
        click.echo(f"npm ready: {runtime['npm_version']}")
        click.echo("ChatUp will use this runtime for npm-backed setup commands in this process.")
        return runtime
    if has_required_nodejs() and not need_prompt:
        node_version = runtime["node_version"]
        npm_version = runtime["npm_version"]
        click.echo(f"Node.js already installed: {node_version}")
        click.echo(f"npm already installed: {npm_version}")
        click.echo("Use -i to install/switch version with nvm.")
        return
    if (
        runtime.get("node_bin")
        and runtime.get("npm_bin")
        and runtime.get("node_major") is not None
        and runtime["node_major"] < MIN_NODEJS_MAJOR
    ):
        click.echo(
            f"Detected Node.js {runtime['node_version']} with npm {runtime['npm_version']}. "
            f"Upgrading to Node.js >= {MIN_NODEJS_MAJOR} via nvm..."
        )

    nvm_sh = Path.home() / ".nvm" / "nvm.sh"
    shell_targets = _resolve_shell_rc_targets(interactive=need_prompt)
    if not nvm_sh.exists():
        logger.info(f"nvm not found, installing bundled nvm ({BUNDLED_NVM_VERSION})")
        click.echo(f"nvm not found, writing bundled nvm.sh ({BUNDLED_NVM_VERSION})...")
        try:
            _install_bundled_nvm(nvm_sh, shell_targets)
        except Exception as exc:
            logger.error(f"Failed to install bundled nvm: {exc}")
            click.echo("Failed to install bundled nvm.", err=True)
            raise click.Abort() from exc
        click.echo(f"Bundled nvm installed: {nvm_sh}")
        for shell_name, shell_rc in shell_targets:
            click.echo(f"Updated {shell_name} init: {shell_rc}")
    else:
        click.echo(f"Found nvm: {nvm_sh}")
        block = _render_nvm_init_block()
        for shell_name, shell_rc in shell_targets:
            _replace_managed_block(shell_rc, NVM_INIT_BEGIN, NVM_INIT_END, block)
            logger.info(f"Ensured nvm init block in {shell_rc}")
            click.echo(f"Ensured nvm init in {shell_rc} ({shell_name})")

    version_spec = "lts/*"
    if need_prompt:
        version_spec = ask_text("Node.js version to install via nvm", default="lts/*")

    quoted_version = shlex.quote(version_spec)
    logger.info(f"Running nvm install for version target: {version_spec}")
    click.echo(f"Installing Node.js via nvm ({version_spec})...")
    nvm_cmd = (
        'export NVM_DIR="$HOME/.nvm" && '
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
        f"nvm install {quoted_version} && "
        f"nvm alias default {quoted_version} && "
        "nvm use default && "
        "node -v && npm -v"
    )
    result = _run_bash_with_output_tail(nvm_cmd)
    if result.returncode != 0:
        logger.error(
            f"Failed to install/use Node.js via nvm for version target: {version_spec}"
        )
        click.echo("Failed to install/use Node.js via nvm.", err=True)
        _echo_recent_output(result, "Recent nvm output:")
        raise click.Abort()

    node_version = _get_bash_output(
        'export NVM_DIR="$HOME/.nvm" && '
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
        "node -v"
    )
    npm_version = _get_bash_output(
        'export NVM_DIR="$HOME/.nvm" && '
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
        "npm -v"
    )
    if node_version:
        click.echo(f"Node.js version: {node_version}")
    if npm_version:
        click.echo(f"npm version: {npm_version}")
    if not node_version or not npm_version:
        click.echo("Node.js was installed but may not be available in current shell.")
        click.echo("Open a new terminal or run: source ~/.nvm/nvm.sh")

    logger.info(f"Node.js setup completed with version target: {version_spec}")
    click.echo(f"Node.js setup completed with version target: {version_spec}")
