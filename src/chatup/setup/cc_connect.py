import click

from chatup.interaction import (
    abort_if_force_without_tty,
    resolve_interactive_mode,
)
from chatup.setup.nodejs import (
    ensure_nodejs_requirement,
    run_npm_command,
    should_install_global_npm_package,
)
from chatup.utils.custom_logger import setup_logger

logger = setup_logger("setup_cc_connect")
CC_CONNECT_BINARY = "cc-connect"
CC_CONNECT_NPM_PACKAGE = "@chatarch/cc-connect"


def _configure_logger(log_level="INFO"):
    global logger
    logger = setup_logger("setup_cc_connect", log_level=str(log_level).upper())
    return logger


def setup_cc_connect(interactive=None, log_level="INFO"):
    _configure_logger(log_level)
    logger.info("Start cc-connect setup")
    usage = "Usage: chatup cc-connect [-i|-I]"
    interactive, can_prompt, force_interactive, _, _ = resolve_interactive_mode(
        interactive=interactive,
        auto_prompt_condition=False,
    )
    abort_if_force_without_tty(force_interactive, can_prompt, usage)

    ensure_nodejs_requirement(
        interactive=interactive,
        can_prompt=can_prompt,
        log_level=log_level,
    )

    logger.info("Checking cc-connect installation")
    if not should_install_global_npm_package(
        CC_CONNECT_NPM_PACKAGE,
        CC_CONNECT_BINARY,
        interactive=interactive,
        can_prompt=can_prompt,
    ):
        return

    click.echo(
        f"未检测到 {CC_CONNECT_BINARY}，正在安装 (npm install -g {CC_CONNECT_NPM_PACKAGE})..."
    )
    logger.info("Installing ChatArch cc-connect cli with npm")
    result = run_npm_command(["install", "-g", CC_CONNECT_NPM_PACKAGE])
    if result.returncode != 0:
        logger.error("Failed to install cc-connect")
        click.echo("cc-connect 安装失败。", err=True)
        if result.stderr:
            click.echo(result.stderr.strip(), err=True)
        raise click.Abort()

    click.echo("cc-connect 安装完成。")
    logger.info("cc-connect setup completed")
