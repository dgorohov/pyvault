from functools import update_wrapper

import click

from vault.aws import auth
from vault.aws.cfg import AwsConfigReader
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
        @click.option("--ui/--no-ui", help="Use UI prompt for entering the MFA tokens", default=False)
        @click.option("--config", help="AWS config file", default="~/.aws/config")
        def _fn(ctx, profile, ui, config, *args, **kwargs):
            with AwsConfigReader(profile, config_path=config) as config_parser:
                credentials = auth.Auth(config_parser[profile], use_ui_prompt=ui).auth()
                env = AwsEnv(config_parser[profile], credentials)
                obj = ExecConfig(profile, credentials, env)
            return ctx.invoke(fn, obj, *args, **kwargs)

        return update_wrapper(_fn, fn)

    return _decorator()


@cli.command("exec")
@click.argument('arguments', nargs=-1, type=click.Path())
@pass_exec_config
def execute(exec_cfg: ExecConfig, arguments):
    executor = Executor(exec_cfg.env, exec_cfg.credentials)
    executor.invoke(*arguments)


@cli.command()
def version():
    click.echo(f"pyvault {ver}")

