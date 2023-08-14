import os
import time
import webbrowser

import boto3
import botocore
import click
from botocore.config import Config

from vault import auth

config = Config(connect_timeout=5, retries={'max_attempts': 2})
# boto3.set_stream_logger(name='botocore')


class AuthResponse(auth.Credentials):
    def __init__(self,
                 aws_access_key_id,
                 aws_secret_access_key,
                 aws_session_token,
                 expiration):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.expiration = expiration

    def to_dict(self):
        return {
            "Version": 1,
            "AccessKeyId": self.aws_access_key_id,
            "SecretAccessKey": self.aws_secret_access_key,
            "SessionToken": self.aws_session_token
        }


class authProvider:

    def __init__(self):
        if os.environ.get('AWS_PROFILE') is not None:
            os.environ.pop("AWS_PROFILE")


class AssumeRoleProvider(authProvider):
    def __init__(self, profile):
        authProvider.__init__(self)
        self.profile = profile
        default_credentials = self.profile.default_credentials()
        self.session = boto3.session.Session(
            aws_access_key_id=default_credentials['aws_access_key_id'],
            region_name=self.profile['region'],
            aws_secret_access_key=default_credentials['aws_secret_access_key'])
        self.sts_client = self.client_init()

    def client_init(self):
        return self.session.client('sts')

    def do_auth(self):
        return self.sts_client.assume_role(
            RoleSessionName='AssumeRoleSession',
            RoleArn=self.profile['role_arn'])

    def auth(self):
        response = self.do_auth()
        role_credentials = response['Credentials']
        return AuthResponse(
            role_credentials['AccessKeyId'],
            role_credentials['SecretAccessKey'],
            role_credentials['SessionToken'],
            role_credentials['Expiration'].timestamp())


class MfaAssumeRoleProvider(AssumeRoleProvider):
    def __init__(self, profile, mfa_stdin=False):
        AssumeRoleProvider.__init__(self, profile)
        self.value = None
        self.mfa_stdin = mfa_stdin

    def do_auth(self):
        if not self.mfa_stdin:
            value = click.prompt(
                f">>> Enter MFA for {self.profile['mfa_serial']}",
                err=True
            )
        else:
            value = input()
        value = value.strip()
        if len(value) != 6:
            raise ValueError("MFA token should be 6 digits width")
        return self.sts_client.assume_role(
            RoleSessionName='AssumeRoleSession',
            RoleArn=self.profile['role_arn'],
            SerialNumber=self.profile['mfa_serial'],
            TokenCode=value,
            ExternalId=self.profile['mfa_serial']
        )


class SSORoleProvider(authProvider):
    def __init__(self, profile):
        authProvider.__init__(self)
        self.profile = profile
        self.region = self.profile['region']
        self.sso_oidc_client = boto3.client('sso-oidc', self.region, config=config)
        self.sso_client = boto3.client('sso', self.region, config=config)

    def get_oidc_token(self):
        client_creds = self.sso_oidc_client.register_client(
            clientName='vault',
            clientType='public')

        device_creds = self.sso_oidc_client.start_device_authorization(
            clientId=client_creds['clientId'],
            clientSecret=client_creds['clientSecret'],
            startUrl=self.profile['sso_start_url'])
        verification_uri_complete = device_creds['verificationUriComplete']
        webbrowser.open_new(verification_uri_complete)

        slow_down_delay = 5
        retry_interval = 5
        if 'interval' in device_creds:
            retry_interval = device_creds['interval']

        while True:
            try:
                token = self.sso_oidc_client.create_token(
                    clientId=client_creds['clientId'],
                    clientSecret=client_creds['clientSecret'],
                    deviceCode=device_creds['deviceCode'],
                    grantType='urn:ietf:params:oauth:grant-type:device_code')
                return token
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'SlowDownException':
                    retry_interval += slow_down_delay
                elif e.response['Error']['Code'] == 'AuthorizationPendingException':
                    pass
                else:
                    raise e
            time.sleep(retry_interval)

    def get_token(self):
        token = self.get_oidc_token()

        return self.sso_client.get_role_credentials(
            roleName=self.profile['sso_role_name'],
            accountId=self.profile['sso_account_id'],
            accessToken=token['accessToken'])

    def generate_login_url_prefix(self):
        login_url_prefix = "https://signin.aws.amazon.com/federation"
        destination_domain = "console.aws.amazon.com"
        if self.region.startswith('us-gov-'):
            login_url_prefix = "https://signin.amazonaws-us-gov.com/federation"
            destination_domain = "console.amazonaws-us-gov.com"
        elif self.region.startswith('cn-'):
            login_url_prefix = "https://signin.amazonaws.cn/federation"
            destination_domain = "console.amazonaws.cn"

        return f"{login_url_prefix}", f"https://{self.region}.{destination_domain}/console/home?region={self.region}"

    def auth(self):
        role_credentials = self.get_token()
        return AuthResponse(
            role_credentials['roleCredentials']['accessKeyId'],
            role_credentials['roleCredentials']['secretAccessKey'],
            role_credentials['roleCredentials']['sessionToken'],
            role_credentials['roleCredentials']['expiration'] / 1000)


class Auth(auth.Auth):
    def __init__(self, profile, mfa_stdin=False):
        self.profile = profile
        self.mfa_stdin = mfa_stdin

    def auth(self) -> AuthResponse:
        for y in yield_first([self.profile.current, self.do_auth]):
            return y

    def do_auth(self):
        def get_auth():
            if 'role_arn' in self.profile:
                if 'mfa_serial' in self.profile:
                    return MfaAssumeRoleProvider(self.profile, mfa_stdin=self.mfa_stdin).auth()
                return AssumeRoleProvider(self.profile).auth()
            return SSORoleProvider(self.profile).auth()

        auth = get_auth()
        self.profile.set_current(auth)
        return auth


def yield_first(iterable):
    for item in iterable or []:
        res = item()
        if res is not None:
            yield res
            return
