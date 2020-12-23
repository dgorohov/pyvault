from abc import ABC, abstractmethod


class Credentials(ABC):
    @abstractmethod
    def to_dict(self):
        pass


class Auth(ABC):

    @abstractmethod
    def auth(self) -> Credentials:
        pass
