from abc import ABC, abstractmethod


class ShellInit(ABC):

    @abstractmethod
    def shell_init(self):
        pass

    @abstractmethod
    def shell_set(self, profile_name=None):
        pass
