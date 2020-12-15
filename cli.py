from functools import update_wrapper

import click

from aws import auth
from aws.cfg import AwsConfigReader
from aws.env import AwsEnv
from config import Config
from executor import Executor, ExecConfig
from version import version as ver


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
        def _fn(ctx, profile, config, *args, **kwargs):
            with AwsConfigReader(profile, config_path=config) as config_parser:
                credentials = auth.Auth(config_parser[profile]).auth()
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
    click.echo(f"pyvault v{ver}")


if __name__ == '__main__':
    cli()
