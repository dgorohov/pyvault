import configparser
import os
import time
from os.path import expanduser
from pathlib import Path

import click

from vault.aws.auth import AuthResponse
from vault.list import ProfilesListing
from vault.shell import ShellInit


class iniIO(object):
    def __init__(self, path, section):
        self.path = expanduser(path)
        self.section = section
        self.parser = configparser.ConfigParser()
        Path(self.path).touch()
        self.parser.read(self.path)

    def __contains__(self, name):
        return name in self.parser

    def __getitem__(self, name):
        if name in self.parser:
            return self.parser[name]
        return None

    def flush(self):
        with open(self.path, "w+") as f:
            self.parser.write(f)

    def __setitem__(self, key, value):
        if not self.parser.has_section(self.section):
            self.parser.add_section(self.section)
        self.parser.set(self.section, key, value)


class AwsTokens(iniIO):

    def __init__(self, name, path="~/.aws/tokens"):
        self.name = name
        self.path = expanduser(path)
        with open(self.path, "a+") as _:
            pass
        iniIO.__init__(self, self.path, self.name)
        if self.parser.has_section(name):
            self.token = self.parser[name]
        else:
            self.token = None

    def current(self):
        if self.token is None:
            return None
        now = time.time()
        if now > float(self.token['expiration']):
            return None
        return AuthResponse(
            self.token['access_key_id'],
            self.token['secret_access_key_id'],
            self.token['session_token'],
            self.token['expiration'])


class AwsCredentials(iniIO):

    def __init__(self, profile_name, path="~/.aws/credentials"):
        self.profile_name = profile_name
        iniIO.__init__(self, path, profile_name)

    def __getitem__(self, item):
        if self.parser.has_section(self.profile_name):
            return self.parser.get(self.profile_name, item)
        return None

    def exists(self):
        return self.parser.has_section(self.profile_name)


class AwsProfile(object):

    def __init__(self, name, reader: configparser.ConfigParser, creds, token, section_key='profile '):
        self.name = name
        self.creds = creds
        self.section = reader[section_key + str(name)]
        self.token = token
        self.nested = None
        nested_profile = None
        sso_session = None
        if 'include_profile' in self.section:
            nested_profile = self.section['include_profile']
        elif 'source_profile' in self.section:
            nested_profile = self.section['source_profile']
        elif 'sso_session' in self.section:
            sso_session = self.section['sso_session']
        if sso_session is not None:
            self.nested = AwsProfile(sso_session, reader, AwsCredentials(sso_session), token, section_key='sso-session ')
        elif nested_profile is not None:
            self.nested = AwsProfile(nested_profile, reader, AwsCredentials(nested_profile), token)
        elif reader.has_section('default') and name != 'default':
            self.nested = AwsProfile('default', reader, AwsCredentials(nested_profile), token, section_key='')

    def default_credentials(self):
        if self.creds is not None and self.creds.exists():
            return self.creds
        elif self.nested is not None and self.nested.creds is not None and self.nested.creds.exists():
            return self.nested.creds
        return None

    def __contains__(self, name):
        return name in self.section or (self.nested is not None and name in self.nested)

    def __getitem__(self, name):
        if name in self.section:
            return self.section[name]
        elif self.nested is None:
            raise KeyError(f'No such field: {name}')
        return self.nested[name]

    def current(self):
        return self.token.current()

    def set_current(self, auth_response: AuthResponse):
        self.token['access_key_id'] = auth_response.aws_access_key_id
        self.token['secret_access_key_id'] = auth_response.aws_secret_access_key
        self.token['session_token'] = auth_response.aws_session_token
        self.token['expiration'] = str(auth_response.expiration)
        self.token.flush()


class AwsConfigReader(ProfilesListing):

    def __init__(self, config_path='~/.aws/config'):
        self.path = expanduser(config_path)
        self.config_reader = configparser.ConfigParser()
        self.config_reader.read(self.path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __getitem__(self, profile):
        return AwsProfile(profile, self.config_reader, AwsCredentials(profile), AwsTokens(profile))

    def list_profiles(self, fn):
        profiles = map(lambda item: item[item.startswith("profile ") and len("profile "):],
                       self.config_reader.sections())
        fn("AWS", list(filter(lambda item: item != "default", profiles)))


class AWSShellInit(ShellInit, iniIO):
    section = "selected_profile"

    def __init__(self, config="~/.aws/pyvault"):
        iniIO.__init__(self, config, self.section)

    def shell_init(self):
        print("# Please add this string into your shell")
        print("# eval \"$(pyvault init)\"")
        print("export AWS_PROFILE=`pyvault get --raw`")

    def shell_set(self, profile_name=None):
        self["profile"] = profile_name
        self.flush()

    def shell_get(self):
        if not self.parser.has_section(self.section):
            return None
        return self.parser.get(self.section, "profile")

    def shell_exec(self, tool, arguments):
        env = os.environ.copy()
        selected = self.shell_get()

        env['AWS_PROFILE'] = selected
        args = [tool] + arguments
        click.secho(click.style(f">>> Invoking ", fg="white", bold=True) +
                    click.style(f"{tool} {' '.join(arguments)}", fg="green", bold=True) +
                    click.style(" with selected profile: ", fg="white", bold=True) +
                    click.style(selected, fg="white", bold=True))
        os.execvpe(tool, args=args, env=env)
