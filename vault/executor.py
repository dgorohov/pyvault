import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod

import click

from vault.auth import Credentials


class ExecConfig(object):
    __profile = None
    __credentials = None
    __env = None

    def __init__(self, profile, c: Credentials, e):
        self.__profile = profile
        self.__credentials = c
        self.__env = e

    @property
    def profile(self):
        return self.__profile

    @property
    def credentials(self):
        return self.__credentials

    @property
    def env(self):
        return self.__env


class ExecutorEnv(ABC):

    def cleanup(self) -> list:
        return []

    @abstractmethod
    def setup(self) -> dict:
        pass


class Executor(object):

    def __init__(self, exec_env: ExecutorEnv, credentials: Credentials):
        self.env = os.environ.copy()
        self.credentials = credentials

        for env in exec_env.cleanup():
            if env in self.env:
                del self.env[env]
        new_env = exec_env.setup()
        for env in new_env:
            self.env[env] = new_env[env]

    def invoke(self, *arguments):
        if len(arguments) > 0:
            p = subprocess.Popen([*arguments],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 close_fds=True,
                                 env=self.env)
            while True:
                output = p.stdout.readline()
                if output == '' or p.poll() is not None:
                    break
                if output:
                    click.echo(output.rstrip(b'\n'))
        else:
            json.dump(self.credentials.to_dict(), sys.stdout, indent=4)
