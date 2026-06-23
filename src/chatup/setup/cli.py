import click

from chatup.setup.elements import SETUP_COMMAND_ELEMENTS


def _build_setup_command(command_element):
    callback = command_element.callback
    for option_element in reversed(command_element.options):
        decorator = click.argument if option_element.is_argument else click.option
        callback = decorator(*option_element.param_decls, **option_element.kwargs)(callback)
    return click.command(name=command_element.name, help=command_element.help)(callback)


def register_setup_commands(command_group):
    for command_element in SETUP_COMMAND_ELEMENTS:
        command_group.add_command(_build_setup_command(command_element))
    return command_group
