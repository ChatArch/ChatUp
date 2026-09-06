from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

import click
from chatenv import get_paths

from chatup.interaction import abort_if_force_without_tty, resolve_interactive_mode
from chatup.utils.platforming import chmod_executable, executable_name, require_systemd

DEFAULT_NGINX_HOME = get_paths().home_dir / "nginx"
DEFAULT_NGINX_BIND_ADDRESS = "127.0.0.1"
DEFAULT_NGINX_PORT = 8080
DEFAULT_NGINX_SERVICE = "chatup-nginx.service"


@dataclass(frozen=True)
class NginxLayout:
    home: Path
    bin_dir: Path
    binary: Path
    conf: Path
    nginx_conf: Path
    sites_available: Path
    sites_enabled: Path
    logs: Path
    run: Path
    temp: Path
    service_copy: Path
    user_service: Path


@dataclass(frozen=True)
class TemplateField:
    key: str
    label: str
    default: str = ""


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    category: str
    title: str
    description: str
    content: str
    fields: tuple[TemplateField, ...]
    prompt_fields: tuple[str, ...]


CATEGORY_LABELS = {
    "proxy": "Proxy / forward",
    "site": "Site / static",
}

TEMPLATE_SPECS = {
    "proxy-pass": TemplateSpec(
        name="proxy-pass",
        category="proxy",
        title="Basic reverse proxy",
        description="Single server block with a standard proxy_pass upstream.",
        content="""server {
    listen __LISTEN__;
    server_name __SERVER_NAME__;

    location __LOCATION__ {
        proxy_pass __PROXY_PASS__;

        proxy_set_header Host __HOST_HEADER__;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
""",
        fields=(
            TemplateField("LISTEN", "listen", "80"),
            TemplateField("SERVER_NAME", "server_name", "app.example.com"),
            TemplateField("LOCATION", "location", "/"),
            TemplateField("PROXY_PASS", "proxy_pass", "http://127.0.0.1:8080"),
            TemplateField("HOST_HEADER", "Host header", "$host"),
        ),
        prompt_fields=("SERVER_NAME", "PROXY_PASS"),
    ),
    "proxy-pass-https": TemplateSpec(
        name="proxy-pass-https",
        category="proxy",
        title="HTTPS reverse proxy",
        description="Port 80 redirects to 443, then 443 proxies to an upstream.",
        content="""server {
    listen __REDIRECT_LISTEN__;
    server_name __SERVER_NAME__;
    return __REDIRECT_CODE__ https://$host$request_uri;
}

server {
    listen __LISTEN__;
    server_name __SERVER_NAME__;
    ssl_certificate __SSL_CERTIFICATE__;
    ssl_certificate_key __SSL_CERTIFICATE_KEY__;
    client_max_body_size __CLIENT_MAX_BODY_SIZE__;

    location __LOCATION__ {
        proxy_pass __PROXY_PASS__;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host __HOST_HEADER__;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
""",
        fields=(
            TemplateField("REDIRECT_LISTEN", "redirect listen", "80"),
            TemplateField("LISTEN", "https listen", "443 ssl"),
            TemplateField("SERVER_NAME", "server_name", "app.example.com"),
            TemplateField("REDIRECT_CODE", "redirect code", "301"),
            TemplateField(
                "SSL_CERTIFICATE",
                "ssl_certificate",
                "/etc/letsencrypt/live/example/fullchain.pem",
            ),
            TemplateField(
                "SSL_CERTIFICATE_KEY",
                "ssl_certificate_key",
                "/etc/letsencrypt/live/example/privkey.pem",
            ),
            TemplateField("CLIENT_MAX_BODY_SIZE", "client_max_body_size", "100M"),
            TemplateField("LOCATION", "location", "/"),
            TemplateField("PROXY_PASS", "proxy_pass", "http://127.0.0.1:8080"),
            TemplateField("HOST_HEADER", "Host header", "$host"),
        ),
        prompt_fields=(
            "SERVER_NAME",
            "PROXY_PASS",
            "SSL_CERTIFICATE",
            "SSL_CERTIFICATE_KEY",
        ),
    ),
    "websocket-proxy": TemplateSpec(
        name="websocket-proxy",
        category="proxy",
        title="WebSocket proxy",
        description="Reverse proxy with Upgrade/Connection headers for WebSocket upstreams.",
        content="""server {
    listen __LISTEN__;
    server_name __SERVER_NAME__;

    location __LOCATION__ {
        proxy_pass __PROXY_PASS__;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host __HOST_HEADER__;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout __PROXY_READ_TIMEOUT__;
    }
}
""",
        fields=(
            TemplateField("LISTEN", "listen", "80"),
            TemplateField("SERVER_NAME", "server_name", "ws.example.com"),
            TemplateField("LOCATION", "location", "/"),
            TemplateField("PROXY_PASS", "proxy_pass", "http://127.0.0.1:3000"),
            TemplateField("HOST_HEADER", "Host header", "$host"),
            TemplateField("PROXY_READ_TIMEOUT", "proxy_read_timeout", "86400s"),
        ),
        prompt_fields=("SERVER_NAME", "PROXY_PASS"),
    ),
    "static-root": TemplateSpec(
        name="static-root",
        category="site",
        title="Static root / directory",
        description="Serve a local directory or static site root.",
        content="""server {
    listen __LISTEN__;
    server_name __SERVER_NAME__;

    ssl_certificate __SSL_CERTIFICATE__;
    ssl_certificate_key __SSL_CERTIFICATE_KEY__;

    location __LOCATION__ {
        root __ROOT_DIR__;
        autoindex on;
        charset utf-8;
    }
}
""",
        fields=(
            TemplateField("LISTEN", "listen", "443 ssl"),
            TemplateField("SERVER_NAME", "server_name", "share.example.com"),
            TemplateField(
                "SSL_CERTIFICATE",
                "ssl_certificate",
                "/etc/letsencrypt/live/example/fullchain.pem",
            ),
            TemplateField(
                "SSL_CERTIFICATE_KEY",
                "ssl_certificate_key",
                "/etc/letsencrypt/live/example/privkey.pem",
            ),
            TemplateField("LOCATION", "location", "/"),
            TemplateField("ROOT_DIR", "root directory", "/var/www/example-site"),
        ),
        prompt_fields=(
            "SERVER_NAME",
            "ROOT_DIR",
            "SSL_CERTIFICATE",
            "SSL_CERTIFICATE_KEY",
        ),
    ),
    "redirect": TemplateSpec(
        name="redirect",
        category="site",
        title="HTTP redirect",
        description="Redirect one or more hostnames to another URL pattern.",
        content="""server {
    listen __LISTEN__;
    server_name __SERVER_NAME__;
    return __REDIRECT_CODE__ __TARGET__;
}
""",
        fields=(
            TemplateField("LISTEN", "listen", "80"),
            TemplateField("SERVER_NAME", "server_name", "example.com www.example.com"),
            TemplateField("REDIRECT_CODE", "redirect code", "301"),
            TemplateField("TARGET", "redirect target", "https://$host$request_uri"),
        ),
        prompt_fields=("SERVER_NAME", "TARGET"),
    ),
}

ALIASES = {
    "proxy": "proxy-pass",
    "https-proxy": "proxy-pass-https",
    "tls-proxy": "proxy-pass-https",
    "ws": "websocket-proxy",
    "static": "static-root",
    "site": "static-root",
    "redirect-https": "redirect",
}

USAGE = "chatup nginx [TEMPLATE] [OUTPUT_FILE] [--set KEY=VALUE] [-i|-I]"


def nginx_layout(home: str | Path | None = None) -> NginxLayout:
    root = Path(home).expanduser() if home else DEFAULT_NGINX_HOME
    return NginxLayout(
        home=root,
        bin_dir=root / "bin",
        binary=root / "bin" / executable_name("nginx"),
        conf=root / "conf",
        nginx_conf=root / "conf" / "nginx.conf",
        sites_available=root / "conf" / "sites-available",
        sites_enabled=root / "conf" / "sites-enabled",
        logs=root / "logs",
        run=root / "run",
        temp=root / "temp",
        service_copy=root / "services" / DEFAULT_NGINX_SERVICE,
        user_service=Path("~/.config/systemd/user").expanduser() / DEFAULT_NGINX_SERVICE,
    )


def find_nginx_binary(binary: str | Path | None = None) -> Path:
    if binary:
        candidate = Path(binary).expanduser()
        if candidate.exists():
            return candidate
        raise click.ClickException(f"NGINX binary does not exist: {candidate}")
    found = shutil.which("nginx")
    if found:
        return Path(found)
    raise click.ClickException(
        "NGINX binary not found. Install nginx first or pass --binary PATH; ChatUp will copy it into ~/.chatarch/nginx/bin."
    )


def install_nginx_binary(
    layout: NginxLayout,
    *,
    binary: str | Path | None = None,
    force: bool = False,
) -> dict[str, object]:
    if layout.binary.exists() and not force:
        return {"binary": str(layout.binary), "reused": True}
    source = find_nginx_binary(binary)
    layout.bin_dir.mkdir(parents=True, exist_ok=True)
    if source.resolve() != layout.binary.resolve():
        shutil.copy2(source, layout.binary)
    chmod_executable(layout.binary)
    return {"binary": str(layout.binary), "source": str(source), "reused": False}


def render_nginx_conf(layout: NginxLayout) -> str:
    return f"""worker_processes  1;
error_log  {layout.logs}/error.log info;
pid        {layout.run}/nginx.pid;

events {{
    worker_connections  1024;
}}

http {{
    default_type  application/octet-stream;
    access_log    {layout.logs}/access.log;
    sendfile      on;
    keepalive_timeout  65;

    client_body_temp_path {layout.temp}/client_body;
    proxy_temp_path       {layout.temp}/proxy;
    fastcgi_temp_path     {layout.temp}/fastcgi;
    uwsgi_temp_path       {layout.temp}/uwsgi;
    scgi_temp_path        {layout.temp}/scgi;

    include {layout.sites_enabled}/*.conf;
}}
"""


def render_default_site(
    *,
    bind_address: str = DEFAULT_NGINX_BIND_ADDRESS,
    port: int = DEFAULT_NGINX_PORT,
) -> str:
    return f"""server {{
    listen {bind_address}:{port};
    server_name localhost;

    location / {{
        default_type text/plain;
        return 200 "ChatUp NGINX is ready\\n";
    }}
}}
"""


def _safe_symlink(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        target.symlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def init_nginx_runtime(
    layout: NginxLayout,
    *,
    bind_address: str = DEFAULT_NGINX_BIND_ADDRESS,
    port: int = DEFAULT_NGINX_PORT,
    force: bool = False,
) -> dict[str, str]:
    for path in [
        layout.bin_dir,
        layout.conf,
        layout.sites_available,
        layout.sites_enabled,
        layout.logs,
        layout.run,
        layout.temp / "client_body",
        layout.temp / "proxy",
        layout.temp / "fastcgi",
        layout.temp / "uwsgi",
        layout.temp / "scgi",
        layout.service_copy.parent,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    if force or not layout.nginx_conf.exists():
        layout.nginx_conf.write_text(render_nginx_conf(layout), encoding="utf-8")
    default_site = layout.sites_available / "default.conf"
    if force or not default_site.exists():
        default_site.write_text(
            render_default_site(bind_address=bind_address, port=port), encoding="utf-8"
        )
    enabled_site = layout.sites_enabled / "default.conf"
    if force or not enabled_site.exists():
        _safe_symlink(default_site, enabled_site)
    return {
        "home": str(layout.home),
        "config": str(layout.nginx_conf),
        "default_site": str(default_site),
        "enabled_site": str(enabled_site),
    }


def render_service(layout: NginxLayout) -> str:
    prefix = str(layout.home) + "/"
    return f"""[Unit]
Description=ChatUp user-level NGINX
After=network.target

[Service]
Type=forking
PIDFile={layout.run}/nginx.pid
ExecStart={layout.binary} -p {prefix} -c {layout.nginx_conf}
ExecReload={layout.binary} -p {prefix} -c {layout.nginx_conf} -s reload
ExecStop={layout.binary} -p {prefix} -c {layout.nginx_conf} -s quit
Restart=on-failure
RestartSec=5s
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""


def install_user_service(layout: NginxLayout) -> dict[str, str]:
    content = render_service(layout)
    layout.service_copy.parent.mkdir(parents=True, exist_ok=True)
    layout.service_copy.write_text(content, encoding="utf-8")
    layout.user_service.parent.mkdir(parents=True, exist_ok=True)
    layout.user_service.write_text(content, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True)
    subprocess.run(
        ["systemctl", "--user", "enable", DEFAULT_NGINX_SERVICE],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "service": DEFAULT_NGINX_SERVICE,
        "service_copy": str(layout.service_copy),
        "user_service": str(layout.user_service),
    }


def _run_nginx(layout: NginxLayout, *args: str) -> subprocess.CompletedProcess[str]:
    prefix = str(layout.home) + "/"
    return subprocess.run(
        [str(layout.binary), "-p", prefix, "-c", str(layout.nginx_conf), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_nginx_config(layout: NginxLayout) -> str:
    result = _run_nginx(layout, "-t")
    if result.returncode != 0:
        raise click.ClickException((result.stderr or result.stdout).strip())
    return (result.stderr or result.stdout).strip()


def start_nginx(layout: NginxLayout) -> None:
    result = _run_nginx(layout)
    if result.returncode != 0:
        raise click.ClickException((result.stderr or result.stdout).strip())


def smoke_nginx(url: str, *, timeout: int = 20) -> str:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = response.read().decode("utf-8", "replace")
            if response.status == 200:
                return body.strip()
        except Exception as exc:  # pragma: no cover - timing-dependent retry path.
            last_error = str(exc)
            time.sleep(1)
    raise click.ClickException(f"NGINX smoke failed for {url}: {last_error}")


def resolve_template(name: str | None) -> str | None:
    normalized = (name or "").strip().lower()
    mapped = ALIASES.get(normalized, normalized)
    if mapped in TEMPLATE_SPECS:
        return mapped
    return None


def parse_set_values(items: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise click.ClickException(f"Invalid --set format: {item}, expected KEY=VALUE")
        key, value = item.split("=", 1)
        values[key.strip().upper()] = value
    return values


def build_template_values(template_name: str, overrides: dict[str, str]) -> dict[str, str]:
    spec = TEMPLATE_SPECS[template_name]
    values = {field.key: field.default for field in spec.fields}
    values.update(overrides)
    return values


def render_template(template_name: str, values: dict[str, str]) -> str:
    spec = TEMPLATE_SPECS[template_name]
    content = spec.content
    for field in spec.fields:
        content = content.replace(f"__{field.key}__", values.get(field.key, field.default))
    return content


def list_templates() -> list[tuple[str, list[TemplateSpec]]]:
    grouped: dict[str, list[TemplateSpec]] = {}
    for spec in TEMPLATE_SPECS.values():
        grouped.setdefault(spec.category, []).append(spec)
    return [(category, grouped[category]) for category in sorted(grouped)]


def write_output(content: str, output_file: str | None, force: bool) -> Path | None:
    if not output_file:
        click.echo(content, nl=False)
        return None
    target = Path(output_file).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        raise click.ClickException(f"Output file already exists: {target}. Pass --force to overwrite.")
    target.write_text(content, encoding="utf-8")
    click.echo(f"Generated NGINX config: {target}")
    return target


def _render_template_mode(
    template: str | None,
    output_file: str | None,
    set_values: tuple[str, ...],
    force: bool,
    interactive: bool | None,
) -> dict[str, object] | None:
    selected_template = resolve_template(template)
    missing_required = not selected_template
    _, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=missing_required,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, USAGE)
    if not selected_template:
        raise click.ClickException(f"Missing or unknown template. Usage: {USAGE}")

    values = build_template_values(selected_template, parse_set_values(set_values))
    rendered = render_template(selected_template, values)
    target = write_output(rendered, output_file, force)
    return {"template": selected_template, "output_file": str(target) if target else None}


def _smoke_url(bind_address: str, port: int) -> str:
    host = "127.0.0.1" if bind_address in {"0.0.0.0", "::"} else bind_address
    return f"http://{host}:{port}/"


def setup_nginx(
    template: str | None = None,
    output_file: str | None = None,
    set_values: tuple[str, ...] = (),
    list_templates_flag: bool = False,
    force: bool = False,
    interactive: bool | None = None,
    home: str | Path | None = None,
    binary: str | Path | None = None,
    install: bool = True,
    init: bool = True,
    service: bool = True,
    start: bool = False,
    smoke: bool = False,
    port: int = DEFAULT_NGINX_PORT,
    bind_address: str = DEFAULT_NGINX_BIND_ADDRESS,
) -> dict[str, object] | None:
    if list_templates_flag:
        for category, specs in list_templates():
            click.echo(f"[{CATEGORY_LABELS[category]}]")
            for spec in specs:
                click.echo(f"- {spec.name}: {spec.description}")
        return {"templates": list(TEMPLATE_SPECS)}

    if template or output_file or set_values:
        return _render_template_mode(template, output_file, set_values, force, interactive)

    if smoke and not start:
        raise click.ClickException("--smoke requires --start; pass --no-smoke when using --no-start.")

    layout = nginx_layout(home)
    result: dict[str, object] = {"layout": {key: str(value) for key, value in asdict(layout).items()}}
    if install:
        result["install"] = install_nginx_binary(layout, binary=binary, force=force)
    elif binary:
        source = Path(binary).expanduser()
        layout.bin_dir.mkdir(parents=True, exist_ok=True)
        if not layout.binary.exists():
            shutil.copy2(source, layout.binary)
            chmod_executable(layout.binary)
    if init:
        result["init"] = init_nginx_runtime(
            layout, bind_address=bind_address, port=port, force=force
        )
    if service:
        require_systemd("chatup nginx --service")
        if not layout.nginx_conf.exists():
            raise click.ClickException("--service requires --init or an existing nginx.conf.")
        result["service"] = install_user_service(layout)
    if start or smoke:
        if not layout.binary.exists():
            raise click.ClickException("NGINX binary is missing; run chatup nginx with --install first.")
        result["config_test"] = test_nginx_config(layout)
    if start:
        start_nginx(layout)
        result["start"] = {"started": True, "url": _smoke_url(bind_address, port)}
    if smoke:
        result["smoke"] = smoke_nginx(_smoke_url(bind_address, port))

    click.echo(f"NGINX home: {layout.home}")
    click.echo(f"NGINX config: {layout.nginx_conf}")
    if "install" in result:
        click.echo(f"NGINX binary: {layout.binary}")
    if "service" in result:
        click.echo(f"NGINX service: {DEFAULT_NGINX_SERVICE}")
    if "start" in result:
        click.echo(f"NGINX URL: {result['start']['url']}")
    return result
