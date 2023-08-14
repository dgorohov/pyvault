import json
import os
import sys
from abc import ABC, abstractmethod

from vault.auth import Credentials


class ExecConfig(object):
    __profile = None
    __mfa_stdin = None
    __credentials = None
    __env = None

    def __init__(self, profile, c: Credentials, e, mfa_stdin):
        self.__profile = profile
        self.__credentials = c
        self.__env = e
        self.__mfa_stdin = mfa_stdin

    @property
    def profile(self):
        return self.__profile

    @property
    def credentials(self):
        return self.__credentials

    @property
    def env(self):
        return self.__env

    @property
    def mfa_stdin(self):
        return self.__mfa_stdin


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
            os.execvpe(arguments[0], args=arguments, env=self.env)
        else:
            json.dump(self.credentials.to_dict(), sys.stdout)
