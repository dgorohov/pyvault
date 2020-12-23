import configparser
import time
from os.path import expanduser

from vault.aws.auth import AuthResponse


class iniReader(object):
    def __init__(self, path):
        self.parser = configparser.ConfigParser()
        self.parser.read(expanduser(path))

    def __contains__(self, name):
        return name in self.parser

    def __getitem__(self, name):
        if name in self.parser:
            return self.parser[name]
        return None


class AwsTokens(iniReader):

    def __init__(self, name, path="~/.aws/tokens"):
        self.name = name
        self.path = expanduser(path)
        with open(self.path, "a+") as _:
            pass
        iniReader.__init__(self, self.path)
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

    def __setitem__(self, key, value):
        if not self.parser.has_section(self.name):
            self.parser.add_section(self.name)
        self.parser.set(self.name, key, value)

    def flush(self):
        with open(self.path, "w+") as f:
            self.parser.write(f)


class AwsCredentials(iniReader):

    def __init__(self, path="~/.aws/credentials"):
        iniReader.__init__(self, path)


class AwsProfile(object):

    def __init__(self, name, reader: configparser.ConfigParser, creds, token, section_key='profile '):
        self.name = name
        self.creds = creds[name]
        self.section = reader[section_key + str(name)]
        self.token = token
        self.nested = None
        nested_profile = None
        if 'include_profile' in self.section:
            nested_profile = self.section['include_profile']
        elif 'source_profile' in self.section:
            nested_profile = self.section['source_profile']
        if nested_profile is not None:
            self.nested = AwsProfile(nested_profile, reader, creds, token)
        elif reader.has_section('default') and name != 'default':
            self.nested = AwsProfile('default', reader, creds, token, section_key='')

    def default_credentials(self):
        if self.creds is not None:
            return self.creds
        elif self.nested is not None:
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


class AwsConfigReader(object):

    def __init__(self, profile, config_path='~/.aws/config'):
        self.profile = profile
        self.path = expanduser(config_path)
        self.config_reader = configparser.ConfigParser()
        self.config_reader.read(self.path)

    def __enter__(self):
        self.tokens = AwsTokens(self.profile)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tokens.flush()

    def __getitem__(self, profile):
        return AwsProfile(profile, self.config_reader, AwsCredentials(), self.tokens)
