from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence
import click

from chatstyle import INTERACTIVE_OPTION_HELP

from chatup.setup.claude import setup_claude
from chatup.setup.codex import setup_codex
from chatup.setup.cursor_agent import CREDENTIAL_STORE_CHOICES, setup_cursor_agent
from chatup.setup.cc_connect import setup_cc_connect
import chatup.setup.crs as crs_module
from chatup.setup.crs import (
    DEFAULT_CRS_PACKAGE,
    DEFAULT_CRS_PORT,
    DEFAULT_INSTALL_DIR as DEFAULT_CRS_INSTALL_DIR,
    DEFAULT_REDIS_PORT,
)
from chatup.setup.docker import setup_docker
from chatup.setup.discourse import (
    DEFAULT_HOME as DEFAULT_DISCOURSE_HOME,
    DEFAULT_HOSTNAME as DEFAULT_DISCOURSE_HOSTNAME,
    DEFAULT_PORT as DEFAULT_DISCOURSE_PORT,
    DEFAULT_REPO as DEFAULT_DISCOURSE_REPO,
    setup_discourse,
)
from chatup.setup.frp import setup_frp
from chatup.setup.gitea import (
    DEFAULT_BASE_URL as DEFAULT_GITEA_BASE_URL,
    DEFAULT_DATABASE_BACKEND as DEFAULT_GITEA_DATABASE_BACKEND,
    DEFAULT_DATABASE_NAME as DEFAULT_GITEA_DATABASE_NAME,
    DEFAULT_GITEA_REPO,
    DEFAULT_GITEA_VERSION,
    DEFAULT_HTTP_PORT as DEFAULT_GITEA_HTTP_PORT,
    DEFAULT_INSTALL_DIR,
    DEFAULT_LISTEN_ADDR as DEFAULT_GITEA_LISTEN_ADDR,
    DEFAULT_WORK_DIR as DEFAULT_GITEA_WORK_DIR,
    setup_gitea,
)
from chatup.setup.hermes import setup_hermes
from chatup.setup.lark_cli import setup_lark_cli
from chatup.setup.mysql import (
    DEFAULT_MYSQL_BIND_ADDRESS,
    DEFAULT_MYSQL_INSTANCE,
    DEFAULT_MYSQL_PORT,
    DEFAULT_MYSQL_VERSION,
    setup_mysql,
)
from chatup.setup.nginx import (
    DEFAULT_NGINX_BIND_ADDRESS,
    DEFAULT_NGINX_HOME,
    DEFAULT_NGINX_PORT,
    setup_nginx,
)
from chatup.setup.opencode import setup_opencode
from chatup.setup.nodejs import setup_nodejs
from chatup.setup.twikoo import (
    DEFAULT_TWIKOO_BIND_ADDRESS,
    DEFAULT_TWIKOO_INSTANCE,
    DEFAULT_TWIKOO_PORT,
    DEFAULT_TWIKOO_REPO,
    DEFAULT_TWIKOO_VERSION,
    setup_twikoo,
)
from chatup.setup.uv import DEFAULT_PYTHON_VERSION, setup_uv
from chatup.setup.workspace import setup_workspace
from chatup.setup.zsh import setup_zsh
from chatup.setup.zulip import (
    DEFAULT_BIND_ADDRESS as DEFAULT_ZULIP_BIND_ADDRESS,
    DEFAULT_EXTERNAL_HOST as DEFAULT_ZULIP_EXTERNAL_HOST,
    DEFAULT_HOME as DEFAULT_ZULIP_HOME,
    DEFAULT_IMAGE as DEFAULT_ZULIP_IMAGE,
    DEFAULT_PORT as DEFAULT_ZULIP_PORT,
    DEFAULT_POSTGRES_IMAGE as DEFAULT_ZULIP_POSTGRES_IMAGE,
    setup_zulip,
)


@dataclass(frozen=True)
class SetupOptionElement:
    param_decls: Sequence[str]
    kwargs: dict = field(default_factory=dict)

    @property
    def is_argument(self) -> bool:
        return all(not str(decl).startswith("-") for decl in self.param_decls)


@dataclass(frozen=True)
class SetupCommandElement:
    name: str
    help: str
    callback: Callable
    options: Sequence[SetupOptionElement] = field(default_factory=tuple)


def frp_setup(interactive):
    setup_frp(interactive=interactive)


def nodejs_setup(interactive, log_level):
    setup_nodejs(interactive=interactive, log_level=log_level)


def uv_setup(venv, python_version, force, log_level):
    setup_uv(venv=venv, python_version=python_version, force=force, log_level=log_level)


def docker_setup(sudo, interactive, log_level):
    setup_docker(interactive=interactive, use_sudo=sudo, log_level=log_level)


def zsh_setup(omz, aliases, login_shell, interactive, log_level):
    setup_zsh(
        interactive=interactive,
        install_omz=omz,
        aliases=aliases,
        login_shell=login_shell,
        log_level=log_level,
    )


def codex_setup(api_key, base_url, model, env, interactive, install_only, log_level):
    setup_codex(
        api_key=api_key,
        base_url=base_url,
        model=model,
        env_ref=env,
        interactive=interactive,
        install_only=install_only,
        log_level=log_level,
    )


def cursor_agent_setup(
    auth_json,
    auth_env,
    env,
    env_profile,
    save_profile,
    cli_config,
    agent_state,
    api_key_env,
    credential_store,
    install_only,
    verify,
    interactive,
    log_level,
):
    setup_cursor_agent(
        auth_json=auth_json,
        auth_env=auth_env,
        env_ref=env,
        env_profile=env_profile,
        save_profile=save_profile,
        cli_config=cli_config,
        agent_state=agent_state,
        api_key_env=api_key_env,
        credential_store=credential_store,
        install_only=install_only,
        verify=verify,
        interactive=interactive,
        log_level=log_level,
    )


def cc_connect_setup(sudo=None, interactive=None, log_level="INFO"):
    setup_cc_connect(interactive=interactive, log_level=log_level)


def gitea_setup(
    version,
    repo,
    install_dir,
    init,
    service,
    work_dir,
    config_path,
    base_url,
    listen_addr,
    port,
    database_backend,
    database_host,
    database_name,
    database_user,
    database_password_env,
    force,
    interactive,
    log_level,
):
    setup_gitea(
        version=version,
        repo=repo,
        install_dir=install_dir,
        init=init,
        service=service,
        work_dir=work_dir,
        config_path=config_path,
        base_url=base_url,
        listen_addr=listen_addr,
        port=port,
        database_backend=database_backend,
        database_host=database_host,
        database_name=database_name,
        database_user=database_user,
        database_password_env=database_password_env,
        force=force,
        interactive=interactive,
        log_level=log_level,
    )


def discourse_setup(
    home,
    hostname,
    port,
    env,
    env_profile,
    write_admin_env,
    write_app_yml,
    clone,
    repo,
    with_ai,
    force,
    interactive,
    log_level,
):
    setup_discourse(
        home=home,
        hostname=hostname,
        port=port,
        env_ref=env,
        env_profile=env_profile,
        write_admin_env=write_admin_env,
        write_app_yml=write_app_yml,
        clone=clone,
        repo=repo,
        with_ai=with_ai,
        force=force,
        interactive=interactive,
        log_level=log_level,
    )


def zulip_setup(
    home,
    image,
    postgres_image,
    external_host,
    bind_address,
    port,
    env,
    env_profile,
    write_admin_env,
    write_compose,
    pull,
    start,
    force,
    interactive,
    log_level,
):
    setup_zulip(
        home=home,
        image=image,
        postgres_image=postgres_image,
        external_host=external_host,
        bind_address=bind_address,
        port=port,
        env_ref=env,
        env_profile=env_profile,
        write_admin_env=write_admin_env,
        write_compose=write_compose,
        pull=pull,
        start=start,
        force=force,
        interactive=interactive,
        log_level=log_level,
    )


def mysql_setup(
    version,
    home,
    name,
    port,
    bind_address,
    install,
    init,
    initialize,
    service,
    start,
    smoke,
    database,
    force,
    log_level,
):
    setup_mysql(
        version=version,
        home=home,
        name=name,
        port=port,
        bind_address=bind_address,
        install=install,
        init=init,
        initialize=initialize,
        service=service,
        start=start,
        smoke=smoke,
        database=database,
        force=force,
        log_level=log_level,
    )


def twikoo_setup(
    version,
    repo,
    home,
    name,
    port,
    bind_address,
    install,
    init,
    service,
    start,
    smoke,
    force,
    log_level,
):
    result = setup_twikoo(
        name=name,
        version=version,
        repo=repo,
        home=home,
        port=port,
        bind_address=bind_address,
        install=install,
        init=init,
        service=service,
        start=start,
        smoke=smoke,
        force=force,
        log_level=log_level,
    )
    service_info = result.get("service") if isinstance(result, dict) else None
    if isinstance(service_info, dict) and service_info.get("unit"):
        click.echo(service_info["unit"])


def nginx_setup(
    template,
    output_file,
    set_values,
    list_templates,
    home,
    binary,
    install,
    init,
    service,
    start,
    smoke,
    port,
    bind_address,
    force,
    interactive,
):
    setup_nginx(
        template=template,
        output_file=output_file,
        set_values=set_values,
        list_templates_flag=list_templates,
        home=home,
        binary=binary,
        install=install,
        init=init,
        service=service,
        start=start,
        smoke=smoke,
        port=port,
        bind_address=bind_address,
        force=force,
        interactive=interactive,
    )


def crs_setup(package, install_dir, redis_port, port, start, smoke, interactive, log_level):
    result = crs_module.setup_crs(
        package=package,
        install_dir=install_dir,
        redis_port=redis_port,
        port=port,
        start=start,
        smoke=smoke,
        interactive=interactive,
        log_level=log_level,
    )
    if isinstance(result, dict) and result.get("crs_url"):
        click.echo(f"CRS URL: {result['crs_url']}")


def claude_setup(auth_token, base_url, small_fast_model, interactive, install_only, log_level):
    setup_claude(
        auth_token=auth_token,
        base_url=base_url,
        small_fast_model=small_fast_model,
        interactive=interactive,
        install_only=install_only,
        log_level=log_level,
    )


def opencode_setup(
    base_url=None,
    api_key=None,
    model=None,
    env=None,
    interactive=None,
    plugin=None,
    install_only=False,
    log_level="INFO",
):
    setup_opencode(
        base_url=base_url,
        api_key=api_key,
        model=model,
        env_ref=env,
        interactive=interactive,
        plugin=plugin,
        install_only=install_only,
        log_level=log_level,
    )


def lark_cli_setup(app_id, app_secret, brand, env, interactive, log_level):
    setup_lark_cli(
        app_id=app_id,
        app_secret=app_secret,
        brand=brand,
        env_ref=env,
        interactive=interactive,
        log_level=log_level,
    )


def hermes_setup(
    installer,
    update_installer,
    hermes_home,
    webui_dir,
    env,
    feishu_env,
    api_key,
    base_url,
    model,
    with_webui_env,
    start_webui,
    install_only,
    webui_host,
    webui_port,
    webui_state_dir,
    webui_workspace,
    webui_model,
    webui_password,
    interactive,
    log_level,
):
    setup_hermes(
        installer=installer,
        update_installer=update_installer,
        hermes_home=hermes_home,
        webui_dir=webui_dir,
        openai_env=env,
        feishu_env=feishu_env,
        api_key=api_key,
        base_url=base_url,
        model=model,
        with_webui_env=with_webui_env,
        start_webui=start_webui,
        install_only=install_only,
        webui_host=webui_host,
        webui_port=webui_port,
        webui_state_dir=webui_state_dir,
        webui_workspace=webui_workspace,
        webui_model=webui_model,
        webui_password=webui_password,
        interactive=interactive,
        log_level=log_level,
    )


LOG_LEVEL_OPTION = SetupOptionElement(
    param_decls=("-l", "--log-level"),
    kwargs={
        "default": "INFO",
        "show_default": True,
        "type": click.Choice(
            ["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False
        ),
        "help": "Console log level for staged setup logs.",
    },
)


def workspace_setup(
    profile,
    workspace_dir,
    language,
    interactive,
    force,
    dry_run,
    with_chattool,
    chattool_source,
    with_chatblog,
    chatblog_source,
    with_memory,
    memory_source,
):
    setup_workspace(
        profile_name=profile,
        workspace_dir=workspace_dir,
        language=language,
        interactive=interactive,
        force=force,
        dry_run=dry_run,
        with_chattool=with_chattool,
        chattool_source=chattool_source,
        with_chatblog=with_chatblog,
        chatblog_source=chatblog_source,
        with_memory=with_memory,
        memory_source=memory_source,
    )


SETUP_COMMAND_ELEMENTS = (
    SetupCommandElement(
        name="zsh",
        help="Configure zsh, oh-my-zsh, plugins, theme, and shell aliases.",
        callback=zsh_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--omz/--no-omz",),
                kwargs={
                    "default": True,
                    "help": "Install/configure oh-my-zsh plugins and powerlevel10k theme.",
                },
            ),
            SetupOptionElement(
                param_decls=("--aliases/--no-aliases",),
                kwargs={
                    "default": True,
                    "help": "Write managed aliases to ~/.zsh_aliases and source it from ~/.zshrc.",
                },
            ),
            SetupOptionElement(
                param_decls=("--login-shell/--no-login-shell",),
                kwargs={
                    "default": True,
                    "help": "Manage ~/.bash_profile handoff that execs zsh -l.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": "-i opens optional setup choices, -I disables prompts.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="cc-connect",
        help="Install cc-connect CLI and runtime dependencies.",
        callback=cc_connect_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--sudo",),
                kwargs={
                    "is_flag": True,
                    "help": "Reserved for compatibility; cc-connect setup does not currently require sudo.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),

    SetupCommandElement(
        name="gitea",
        help="Install ChatArch Gitea and optionally write a local app.ini/user service.",
        callback=gitea_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--version",),
                kwargs={
                    "default": DEFAULT_GITEA_VERSION,
                    "show_default": True,
                    "help": "ChatArch Gitea release version to install; use latest for the newest release.",
                },
            ),
            SetupOptionElement(
                param_decls=("--repo",),
                kwargs={
                    "default": DEFAULT_GITEA_REPO,
                    "show_default": True,
                    "help": "GitHub repository that owns the Gitea release assets.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-dir",),
                kwargs={
                    "default": str(DEFAULT_INSTALL_DIR),
                    "show_default": True,
                    "type": click.Path(path_type=Path),
                    "help": "Directory where the gitea binary will be installed.",
                },
            ),
            SetupOptionElement(
                param_decls=("--init/--no-init",),
                kwargs={
                    "default": False,
                    "show_default": True,
                    "help": "Generate a ChatTea-compatible local Gitea app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--service/--no-service",),
                kwargs={
                    "default": False,
                    "show_default": True,
                    "help": "Write a user-level systemd service for the managed Gitea instance.",
                },
            ),
            SetupOptionElement(
                param_decls=("--work-dir",),
                kwargs={
                    "default": str(DEFAULT_GITEA_WORK_DIR),
                    "show_default": True,
                    "type": click.Path(path_type=Path),
                    "help": "ChatTea-compatible Gitea WORK_PATH.",
                },
            ),
            SetupOptionElement(
                param_decls=("--config-path",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Optional app.ini path. Defaults to WORK_PATH/custom/conf/app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--base-url",),
                kwargs={
                    "default": DEFAULT_GITEA_BASE_URL,
                    "show_default": True,
                    "help": "Gitea ROOT_URL used in generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--listen-addr",),
                kwargs={
                    "default": DEFAULT_GITEA_LISTEN_ADDR,
                    "show_default": True,
                    "help": "Loopback address for generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={
                    "default": DEFAULT_GITEA_HTTP_PORT,
                    "show_default": True,
                    "type": int,
                    "help": "Gitea HTTP port for generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--database-backend",),
                kwargs={
                    "default": DEFAULT_GITEA_DATABASE_BACKEND,
                    "show_default": True,
                    "type": click.Choice(["sqlite3", "mysql"]),
                    "help": "Database backend for generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--database-host",),
                kwargs={"default": None, "help": "MySQL host/socket for generated app.ini."},
            ),
            SetupOptionElement(
                param_decls=("--database-name",),
                kwargs={
                    "default": DEFAULT_GITEA_DATABASE_NAME,
                    "show_default": True,
                    "help": "Database name for generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--database-user",),
                kwargs={
                    "default": "root",
                    "show_default": True,
                    "help": "Database user for generated app.ini.",
                },
            ),
            SetupOptionElement(
                param_decls=("--database-password-env",),
                kwargs={"default": None, "help": "Env var name that contains the database password."},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={
                    "is_flag": True,
                    "help": "Replace an existing binary/config at the target path.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="discourse",
        help="Prepare ChatArch-contained Discourse docker config and ChatEnv-managed admin credentials.",
        callback=discourse_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--home",),
                kwargs={"default": str(DEFAULT_DISCOURSE_HOME), "show_default": True, "type": click.Path(path_type=Path)},
            ),
            SetupOptionElement(
                param_decls=("--hostname",),
                kwargs={"default": DEFAULT_DISCOURSE_HOSTNAME, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={"default": DEFAULT_DISCOURSE_PORT, "show_default": True, "type": int},
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={"default": None, "help": "ChatEnv profile name or env file with DISCOURSE_ADMIN_* values."},
            ),
            SetupOptionElement(
                param_decls=("--env-profile",),
                kwargs={"default": None, "help": "Explicit ChatEnv profile for Discourse admin values."},
            ),
            SetupOptionElement(
                param_decls=("--write-admin-env/--no-write-admin-env",),
                kwargs={"default": True, "show_default": True, "help": "Write secrets/admin.env from ChatEnv values."},
            ),
            SetupOptionElement(
                param_decls=("--write-app-yml/--no-write-app-yml",),
                kwargs={"default": True, "show_default": True, "help": "Write containers/app.yml using ChatArch-local paths."},
            ),
            SetupOptionElement(
                param_decls=("--clone/--no-clone",),
                kwargs={"default": False, "show_default": True, "help": "Clone/update discourse_docker into HOME/docker."},
            ),
            SetupOptionElement(
                param_decls=("--repo",),
                kwargs={"default": DEFAULT_DISCOURSE_REPO, "show_default": True, "help": "discourse_docker repository URL."},
            ),
            SetupOptionElement(
                param_decls=("--with-ai/--without-ai",),
                kwargs={"default": True, "show_default": True, "help": "Include discourse-ai plugin hook in generated app.yml."},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={"is_flag": True, "help": "Overwrite generated app.yml when it already exists."},
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={"default": None, "help": INTERACTIVE_OPTION_HELP},
            ),
        ),
    ),
    SetupCommandElement(
        name="zulip",
        help="Prepare ChatArch-contained Zulip Docker Compose config and ChatEnv-managed admin credentials.",
        callback=zulip_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--home",),
                kwargs={"default": str(DEFAULT_ZULIP_HOME), "show_default": True, "type": click.Path(path_type=Path)},
            ),
            SetupOptionElement(
                param_decls=("--image",),
                kwargs={"default": DEFAULT_ZULIP_IMAGE, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--postgres-image",),
                kwargs={"default": DEFAULT_ZULIP_POSTGRES_IMAGE, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--external-host",),
                kwargs={"default": DEFAULT_ZULIP_EXTERNAL_HOST, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--bind-address",),
                kwargs={"default": DEFAULT_ZULIP_BIND_ADDRESS, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={"default": DEFAULT_ZULIP_PORT, "show_default": True, "type": int},
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={"default": None, "help": "ChatEnv profile name or env file with ZULIP_ADMIN_* values."},
            ),
            SetupOptionElement(
                param_decls=("--env-profile",),
                kwargs={"default": None, "help": "Explicit ChatEnv profile for Zulip admin values."},
            ),
            SetupOptionElement(
                param_decls=("--write-admin-env/--no-write-admin-env",),
                kwargs={"default": True, "show_default": True, "help": "Write secrets/admin.env from ChatEnv values."},
            ),
            SetupOptionElement(
                param_decls=("--write-compose/--no-write-compose",),
                kwargs={"default": True, "show_default": True, "help": "Write ChatArch-contained compose.yaml."},
            ),
            SetupOptionElement(
                param_decls=("--pull/--no-pull",),
                kwargs={"default": False, "show_default": True, "help": "Run Docker Compose pull after writing config."},
            ),
            SetupOptionElement(
                param_decls=("--start/--no-start",),
                kwargs={"default": False, "show_default": True, "help": "Run Docker Compose up -d after writing config."},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={"is_flag": True, "help": "Overwrite generated compose.yaml when it already exists."},
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={"default": None, "help": INTERACTIVE_OPTION_HELP},
            ),
        ),
    ),
    SetupCommandElement(
        name="mysql",
        help="Install and prepare a ChatData-compatible user-level MySQL runtime.",
        callback=mysql_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--version",),
                kwargs={"default": DEFAULT_MYSQL_VERSION, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--home",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "ChatData home. Defaults to ~/.chatarch/chatdata.",
                },
            ),
            SetupOptionElement(
                param_decls=("--name",),
                kwargs={"default": DEFAULT_MYSQL_INSTANCE, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={"default": DEFAULT_MYSQL_PORT, "show_default": True, "type": int},
            ),
            SetupOptionElement(
                param_decls=("--bind-address",),
                kwargs={"default": DEFAULT_MYSQL_BIND_ADDRESS, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--install/--no-install",),
                kwargs={"default": True, "show_default": True, "help": "Download and verify the MySQL runtime."},
            ),
            SetupOptionElement(
                param_decls=("--init/--no-init",),
                kwargs={"default": True, "show_default": True, "help": "Create the instance directories and my.cnf."},
            ),
            SetupOptionElement(
                param_decls=("--initialize/--no-initialize",),
                kwargs={"default": True, "show_default": True, "help": "Run mysqld --initialize-insecure."},
            ),
            SetupOptionElement(
                param_decls=("--service/--no-service",),
                kwargs={"default": True, "show_default": True, "help": "Install a user-level systemd service."},
            ),
            SetupOptionElement(
                param_decls=("--start/--no-start",),
                kwargs={"default": False, "show_default": True, "help": "Start the user-level MySQL service."},
            ),
            SetupOptionElement(
                param_decls=("--smoke/--no-smoke",),
                kwargs={"default": False, "show_default": True, "help": "Ping and query MySQL after starting it."},
            ),
            SetupOptionElement(
                param_decls=("--database",),
                kwargs={"default": None, "help": "Create a database after starting MySQL."},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={"is_flag": True, "help": "Replace existing runtime/config/data where supported."},
            ),
        ),
    ),
    SetupCommandElement(
        name="twikoo",
        help="Install and prepare a multi-instance Twikoo comment service runtime.",
        callback=twikoo_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--version",),
                kwargs={"default": DEFAULT_TWIKOO_VERSION, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--repo",),
                kwargs={"default": DEFAULT_TWIKOO_REPO, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--home",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Twikoo home. Defaults to ~/.chatarch/twikoo.",
                },
            ),
            SetupOptionElement(
                param_decls=("--name",),
                kwargs={"default": DEFAULT_TWIKOO_INSTANCE, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={"default": DEFAULT_TWIKOO_PORT, "show_default": True, "type": int},
            ),
            SetupOptionElement(
                param_decls=("--bind-address",),
                kwargs={"default": DEFAULT_TWIKOO_BIND_ADDRESS, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--install/--no-install",),
                kwargs={"default": True, "show_default": True, "help": "Download the Twikoo release binary."},
            ),
            SetupOptionElement(
                param_decls=("--init/--no-init",),
                kwargs={"default": True, "show_default": True, "help": "Create instance directories, env file, and instance-local binary link."},
            ),
            SetupOptionElement(
                param_decls=("--service/--no-service",),
                kwargs={"default": True, "show_default": True, "help": "Install a user-level systemd service."},
            ),
            SetupOptionElement(
                param_decls=("--start/--no-start",),
                kwargs={"default": False, "show_default": True, "help": "Start the user-level Twikoo service."},
            ),
            SetupOptionElement(
                param_decls=("--smoke/--no-smoke",),
                kwargs={"default": False, "show_default": True, "help": "Run a local HTTP smoke test after starting."},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={"is_flag": True, "help": "Replace existing runtime/config/service where supported."},
            ),
        ),
    ),
    SetupCommandElement(
        name="nginx",
        help="Prepare user-level NGINX under ChatArch home and render config templates.",
        callback=nginx_setup,
        options=(
            SetupOptionElement(param_decls=("template",), kwargs={"required": False}),
            SetupOptionElement(param_decls=("output_file",), kwargs={"required": False}),
            SetupOptionElement(
                param_decls=("--set", "set_values"),
                kwargs={
                    "multiple": True,
                    "help": "Override template variable, e.g. --set SERVER_NAME=app.example.com.",
                },
            ),
            SetupOptionElement(
                param_decls=("--list", "list_templates"),
                kwargs={"is_flag": True, "help": "List available NGINX templates."},
            ),
            SetupOptionElement(
                param_decls=("--home",),
                kwargs={
                    "default": str(DEFAULT_NGINX_HOME),
                    "show_default": True,
                    "type": click.Path(path_type=Path),
                    "help": "ChatArch-managed NGINX home.",
                },
            ),
            SetupOptionElement(
                param_decls=("--binary",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Existing nginx binary to copy into HOME/bin/nginx.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install/--no-install",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Copy an existing nginx binary into ChatArch home.",
                },
            ),
            SetupOptionElement(
                param_decls=("--init/--no-init",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Create user-level config, logs, run, temp, and sites directories.",
                },
            ),
            SetupOptionElement(
                param_decls=("--service/--no-service",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Write a user-level systemd service for ChatUp NGINX.",
                },
            ),
            SetupOptionElement(
                param_decls=("--start/--no-start",),
                kwargs={
                    "default": False,
                    "show_default": True,
                    "help": "Start the user-level NGINX runtime after setup.",
                },
            ),
            SetupOptionElement(
                param_decls=("--smoke/--no-smoke",),
                kwargs={
                    "default": False,
                    "show_default": True,
                    "help": "HTTP smoke check after starting NGINX.",
                },
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={"default": DEFAULT_NGINX_PORT, "show_default": True, "type": int},
            ),
            SetupOptionElement(
                param_decls=("--bind-address",),
                kwargs={"default": DEFAULT_NGINX_BIND_ADDRESS, "show_default": True},
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={"is_flag": True, "help": "Overwrite existing binary/config/output file."},
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={"default": None, "help": INTERACTIVE_OPTION_HELP},
            ),
        ),
    ),
    SetupCommandElement(
        name="crs",
        help="Install and bootstrap local ChatArch Claude Relay Service.",
        callback=crs_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--package",),
                kwargs={
                    "default": DEFAULT_CRS_PACKAGE,
                    "show_default": True,
                    "help": f"Canonical CRS npm package to install. Default: {DEFAULT_CRS_PACKAGE}.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-dir",),
                kwargs={
                    "default": str(DEFAULT_CRS_INSTALL_DIR),
                    "show_default": True,
                    "type": click.Path(path_type=Path),
                    "help": "Install root for CRS app, Redis runtime/data, and local secrets.",
                },
            ),
            SetupOptionElement(
                param_decls=("--redis-port",),
                kwargs={
                    "default": DEFAULT_REDIS_PORT,
                    "show_default": True,
                    "type": int,
                    "help": "Local Redis port managed by ChatUp without registering a system service.",
                },
            ),
            SetupOptionElement(
                param_decls=("--port",),
                kwargs={
                    "default": DEFAULT_CRS_PORT,
                    "show_default": True,
                    "type": int,
                    "help": "Local CRS HTTP port.",
                },
            ),
            SetupOptionElement(
                param_decls=("--start/--no-start",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Start CRS after install.",
                },
            ),
            SetupOptionElement(
                param_decls=("--smoke/--no-smoke",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Run local health/admin route smoke after setup.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="claude",
        help="Configure Claude Code CLI and config files.",
        callback=claude_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--auth-token", "--token"),
                kwargs={"default": None, "help": "Value for ANTHROPIC_AUTH_TOKEN."},
            ),
            SetupOptionElement(
                param_decls=("--base-url", "--url"),
                kwargs={"default": None, "help": "Optional ANTHROPIC_BASE_URL value."},
            ),
            SetupOptionElement(
                param_decls=("--small-fast-model", "--sfm"),
                kwargs={
                    "default": None,
                    "help": "Optional ANTHROPIC_SMALL_FAST_MODEL value.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-only",),
                kwargs={
                    "is_flag": True,
                    "help": "Only install or upgrade the CLI without writing config files.",
                },
            ),
        ),
    ),

    SetupCommandElement(
        name="docker",
        help="Check Docker environment and optionally run suggested sudo commands.",
        callback=docker_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--sudo",),
                kwargs={
                    "is_flag": True,
                    "help": "Allow setup docker to execute suggested sudo commands after confirmation.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="frp",
        help="Install FRP Client/Server.",
        callback=frp_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="nodejs",
        help="Install nvm and Node.js (default LTS).",
        callback=nodejs_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="uv",
        help="Install uv and create the ChatArch Python 3.12 environment with pip.",
        callback=uv_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--venv", "--venv-path"),
                kwargs={
                    "default": "~/.chatarch/venv",
                    "show_default": True,
                    "help": "Target ChatArch Python virtual environment path.",
                },
            ),
            SetupOptionElement(
                param_decls=("--python", "--python-version", "python_version"),
                kwargs={
                    "default": DEFAULT_PYTHON_VERSION,
                    "show_default": True,
                    "help": "Python version to install through uv and use for the venv.",
                },
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={
                    "is_flag": True,
                    "help": "Clear and recreate the target environment if it already exists.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="codex",
        help="Configure Codex CLI and config files.",
        callback=codex_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--api-key", "--key"),
                kwargs={
                    "default": None,
                    "help": "OpenAI API key to write into Codex auth.json.",
                },
            ),
            SetupOptionElement(
                param_decls=("--base-url", "--url"),
                kwargs={
                    "default": None,
                    "help": "Optional base_url for model provider.",
                },
            ),
            SetupOptionElement(
                param_decls=("--model",),
                kwargs={"default": None, "help": "Optional default model name."},
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={
                    "default": None,
                    "help": "Load OpenAI config from a .env file path or saved OpenAI profile name.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-only",),
                kwargs={
                    "is_flag": True,
                    "help": "Only install or upgrade the CLI and skip provider/model prompts; plugin presets may still update OpenCode config.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="cursor-agent",
        help="Install/configure Cursor Agent CLI auth and config files.",
        callback=cursor_agent_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--auth-json",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Copy Cursor auth.json containing accessToken/refreshToken; values are never printed.",
                },
            ),
            SetupOptionElement(
                param_decls=("--auth-env",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Read CURSOR_ACCESS_TOKEN and CURSOR_REFRESH_TOKEN from an env file and write Cursor auth.json.",
                },
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={
                    "default": None,
                    "help": "Load Cursor credentials from an env file path or a ChatEnv Cursor Agent profile name.",
                },
            ),
            SetupOptionElement(
                param_decls=("--env-profile", "--profile"),
                kwargs={
                    "default": None,
                    "help": "Load Cursor tokens from a ChatEnv Cursor Agent profile.",
                },
            ),
            SetupOptionElement(
                param_decls=("--save-profile",),
                kwargs={
                    "default": None,
                    "help": "Save imported Cursor tokens to a ChatEnv Cursor Agent profile without printing values.",
                },
            ),
            SetupOptionElement(
                param_decls=("--cli-config",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Copy Cursor ~/.cursor/cli-config.json with restrictive permissions.",
                },
            ),
            SetupOptionElement(
                param_decls=("--agent-state",),
                kwargs={
                    "default": None,
                    "type": click.Path(path_type=Path),
                    "help": "Copy Cursor ~/.cursor/agent-cli-state.json with restrictive permissions.",
                },
            ),
            SetupOptionElement(
                param_decls=("--api-key-env",),
                kwargs={
                    "default": None,
                    "help": "Name of an environment variable containing a Cursor API key for verification only.",
                },
            ),
            SetupOptionElement(
                param_decls=("--credential-store",),
                kwargs={
                    "default": "native",
                    "show_default": True,
                    "type": click.Choice(CREDENTIAL_STORE_CHOICES),
                    "help": "Credential mode. file-wrapper writes a token-free wrapper that reads auth.json at runtime.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-only",),
                kwargs={
                    "is_flag": True,
                    "help": "Install/verify the standalone Cursor Agent CLI without writing auth/config files.",
                },
            ),
            SetupOptionElement(
                param_decls=("--verify/--no-verify",),
                kwargs={
                    "default": True,
                    "show_default": True,
                    "help": "Run a non-secret cursor-agent version check after setup.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="opencode",
        help="Configure OpenCode CLI and config files.",
        callback=opencode_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--base-url", "--url"),
                kwargs={"default": None, "help": "Required base URL for the provider."},
            ),
            SetupOptionElement(
                param_decls=("--api-key", "--key"),
                kwargs={"default": None, "help": "Required API key for the provider."},
            ),
            SetupOptionElement(
                param_decls=("--model",),
                kwargs={"default": None, "help": "Required default model name."},
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={
                    "default": None,
                    "help": "Load OpenAI config from a .env file path or saved OpenAI profile name.",
                },
            ),
            SetupOptionElement(
                param_decls=("--plugin",),
                kwargs={
                    "default": None,
                    "type": click.Choice(["auto-loop"]),
                    "help": "Optionally enable a supported OpenCode plugin preset such as opencode-auto-loop.",
                },
            ),
            SetupOptionElement(
                param_decls=("--install-only",),
                kwargs={
                    "is_flag": True,
                    "help": "Only install or upgrade the CLI without writing config files.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="lark-cli",
        help="Configure official lark-cli and reuse ChatEnv Feishu config.",
        callback=lark_cli_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--app-id",),
                kwargs={"default": None, "help": "Lark/Feishu app id."},
            ),
            SetupOptionElement(
                param_decls=("--app-secret",),
                kwargs={"default": None, "help": "Lark/Feishu app secret."},
            ),
            SetupOptionElement(
                param_decls=("--brand",),
                kwargs={
                    "default": None,
                    "type": click.Choice(["feishu", "lark"]),
                    "help": "Official brand value written to lark-cli config.",
                },
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={
                    "default": None,
                    "help": "Load Feishu config from a .env file path or saved Feishu profile name.",
                },
            ),
        ),
    ),
    SetupCommandElement(
        name="hermes",
        help="Install Hermes Agent and optional Hermes WebUI.",
        callback=hermes_setup,
        options=(
            LOG_LEVEL_OPTION,
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--installer",),
                kwargs={
                    "default": None,
                    "help": "Path to a local ChatArch Hermes install.sh.",
                },
            ),
            SetupOptionElement(
                param_decls=("--update-installer",),
                kwargs={
                    "is_flag": True,
                    "help": "Download the latest ChatArch Hermes install.sh into the ChatUp cache before setup.",
                },
            ),
            SetupOptionElement(
                param_decls=("--hermes-home",),
                kwargs={"default": None, "help": "Hermes home directory."},
            ),
            SetupOptionElement(
                param_decls=("--webui-dir",),
                kwargs={"default": None, "help": "Existing Hermes WebUI app directory."},
            ),
            SetupOptionElement(
                param_decls=("-e", "--env"),
                kwargs={
                    "default": None,
                    "help": "Load OpenAI config from a .env file path or saved OpenAI profile name.",
                },
            ),
            SetupOptionElement(
                param_decls=("--feishu-env",),
                kwargs={
                    "default": None,
                    "help": "Explicitly load Feishu config from a .env file path or saved Feishu profile name.",
                },
            ),
            SetupOptionElement(
                param_decls=("--api-key", "--key"),
                kwargs={"default": None, "help": "OpenAI-compatible API key."},
            ),
            SetupOptionElement(
                param_decls=("--base-url", "--url"),
                kwargs={"default": None, "help": "OpenAI-compatible base URL."},
            ),
            SetupOptionElement(
                param_decls=("--model",),
                kwargs={"default": None, "help": "Hermes default model."},
            ),
            SetupOptionElement(
                param_decls=("--with-webui-env",),
                kwargs={"is_flag": True, "help": "Write Hermes WebUI env/profile values."},
            ),
            SetupOptionElement(
                param_decls=("--webui-host",),
                kwargs={"default": "127.0.0.1", "show_default": True, "help": "Hermes WebUI host."},
            ),
            SetupOptionElement(
                param_decls=("--webui-port",),
                kwargs={"default": 8787, "show_default": True, "type": int, "help": "Hermes WebUI port."},
            ),
            SetupOptionElement(
                param_decls=("--webui-state-dir",),
                kwargs={"default": None, "help": "Hermes WebUI state directory."},
            ),
            SetupOptionElement(
                param_decls=("--webui-workspace",),
                kwargs={"default": None, "help": "Hermes WebUI default workspace."},
            ),
            SetupOptionElement(
                param_decls=("--webui-model",),
                kwargs={"default": None, "help": "Hermes WebUI default model."},
            ),
            SetupOptionElement(
                param_decls=("--webui-password",),
                kwargs={"default": None, "help": "Hermes WebUI password."},
            ),
            SetupOptionElement(
                param_decls=("--start-webui",),
                kwargs={"is_flag": True, "help": "Start an existing Hermes WebUI app directory after setup."},
            ),
            SetupOptionElement(
                param_decls=("--install-only",),
                kwargs={"is_flag": True, "help": "Only install or check Hermes Agent without writing config files."},
            ),
        ),
    ),
    SetupCommandElement(
        name="workspace",
        help="Initialize a human-AI collaboration workspace scaffold.",
        callback=workspace_setup,
        options=(
            SetupOptionElement(
                param_decls=("profile",),
                kwargs={"required": False},
            ),
            SetupOptionElement(
                param_decls=("workspace_dir",),
                kwargs={"required": False},
            ),
            SetupOptionElement(
                param_decls=("--language",),
                kwargs={
                    "default": "zh",
                    "type": click.Choice(["zh", "en"]),
                    "show_default": True,
                    "help": "Template language for generated workspace files.",
                },
            ),
            SetupOptionElement(
                param_decls=("--interactive/--no-interactive", "-i/-I"),
                kwargs={
                    "default": None,
                    "help": INTERACTIVE_OPTION_HELP,
                },
            ),
            SetupOptionElement(
                param_decls=("--force", "-f"),
                kwargs={
                    "is_flag": True,
                    "help": "Overwrite existing generated files.",
                },
            ),
            SetupOptionElement(
                param_decls=("--dry-run",),
                kwargs={
                    "is_flag": True,
                    "help": "Print planned workspace files and directories without writing anything.",
                },
            ),
            SetupOptionElement(
                param_decls=("--with-chattool/--no-chattool",),
                kwargs={
                    "default": False,
                    "help": "Optionally clone/update ChatTool into core/ChatTool without syncing its legacy skills.",
                },
            ),
            SetupOptionElement(
                param_decls=("--chattool-source", "--source"),
                kwargs={
                    "default": None,
                    "help": "Git URL or local ChatTool repo path used when --with-chattool is enabled.",
                },
            ),
            SetupOptionElement(
                param_decls=("--with-chatblog/--no-chatblog",),
                kwargs={
                    "default": False,
                    "help": "Optionally clone/update ChatBlog and link its posts into public/chatblog.",
                },
            ),
            SetupOptionElement(
                param_decls=("--chatblog-source",),
                kwargs={
                    "default": None,
                    "help": "Git URL or local ChatBlog repo path used when --with-chatblog is enabled.",
                },
            ),
            SetupOptionElement(
                param_decls=("--with-memory/--no-memory",),
                kwargs={
                    "default": False,
                    "help": "Optionally clone/update ChatMemory, link shared groups chatarch/common/agents, and create local skills.",
                },
            ),
            SetupOptionElement(
                param_decls=("--memory-source",),
                kwargs={
                    "default": None,
                    "help": "Git URL or local ChatMemory repo path used when --with-memory is enabled.",
                },
            ),
        ),
    ),
)
