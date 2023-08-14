import os
from functools import update_wrapper

import click
from pyfzf import FzfPrompt

from vault.aws import auth
from vault.aws.cfg import AwsConfigReader, AWSShellInit
from vault.aws.env import AwsEnv
from vault.config import Config
from vault.executor import ExecConfig, Executor
from vault.version import version as ver


@click.group(invoke_without_command=True)
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.obj = Config(debug)


def pass_exec_config(fn):
    def _decorator():
        @click.pass_context
        @click.option("--profile", help="AWS profile", default="local")
        @click.option("--config", help="AWS config file", default="~/.aws/config")
        @click.option("--mfa-stdin", help="Read MFA code from stdin", default=False, is_flag=True)
        def _fn(ctx, profile, config, mfa_stdin, *args, **kwargs):
            with AwsConfigReader(config_path=config) as config_parser:
                credentials = auth.Auth(config_parser[profile], mfa_stdin=mfa_stdin).auth()
                env = AwsEnv(config_parser[profile], credentials)
                obj = ExecConfig(profile, credentials, env, mfa_stdin)
            return ctx.invoke(fn, obj, *args, **kwargs)

        return update_wrapper(_fn, fn)

    return _decorator()


@cli.command("list")
@click.option("--config", help="AWS config file", default="~/.aws/config")
def profiles_list(config):
    def _dump_prov_profiles(prov, profiles):
        click.echo("Provider: " + click.style(prov, fg="white", bold=True))
        for _profile in profiles:
            click.secho(f" {_profile}", fg="green")

    with AwsConfigReader(config_path=config) as config_parser:
        config_parser.list_profiles(_dump_prov_profiles)


@cli.command("exec")
@click.argument('arguments', nargs=-1, type=click.Path())
@pass_exec_config
def execute(exec_cfg: ExecConfig, arguments):
    executor = Executor(exec_cfg.env, exec_cfg.credentials)
    executor.invoke(*arguments)


@cli.command("init")
@click.option("--pyvault-config", help="pyvault config file", default="~/.aws/pyvault")
def execute(pyvault_config):
    AWSShellInit(pyvault_config).shell_init()


@cli.command("set")
@click.option("--config", help="AWS config file", default="~/.aws/config")
@click.option("--pyvault-config", help="pyvault config file", default="~/.aws/pyvault")
def set_profile(config, pyvault_config):
    profiles = []

    def _collect_prov_profiles(input, prov, ps):
        for _p in ps:
            input.append(_p)

    with AwsConfigReader(config_path=config) as config_parser:
        config_parser.list_profiles(lambda p1, p2: _collect_prov_profiles(profiles, p1, p2))

    fzf = FzfPrompt()
    try:
        selection = fzf.prompt(profiles)
        AWSShellInit(pyvault_config).shell_set(selection[0])
        click.echo("Profile selected: " + click.style(selection[0], fg="white", bold=True))
    except Exception as e:
        print(f"Cancelled. {e}")


@cli.command("get")
@click.option("--pyvault-config", help="pyvault config file", default="~/.aws/pyvault")
@click.option('--raw', default=False, is_flag=True)
def get_profile(pyvault_config, raw):
    selected = AWSShellInit(pyvault_config).shell_get()

    if selected is None:
        if raw:
            print("default")
        else:
            click.secho("AWS profile has not been not selected yet", fg="white", bold=True)
    else:
        if raw:
            print(selected)
        else:
            click.echo("Current profile: " + click.style(selected, fg="white", bold=True))


@cli.command("tool")
@click.option("--pyvault-config", help="pyvault config file", default="~/.aws/pyvault")
@click.option('--tool', help="Tool to execute with selected profile")
@click.argument('arguments', nargs=-1, type=click.Path())
def tool(pyvault_config, tool, arguments):
    AWSShellInit(pyvault_config).shell_exec(tool, list(arguments))


@cli.command()
def version():
    click.echo(f"pyvault {ver}")


if __name__ == "__main__":
    cli()
