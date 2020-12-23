import click


class Config(object):
    __debug = False

    def __init__(self, d):
        self.__debug = d

    @property
    def debug(self):
        return self.__debug


pass_config = click.make_pass_decorator(Config, ensure=True)
