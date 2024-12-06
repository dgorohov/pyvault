from vault.aws.auth import AuthResponse
from vault.executor import ExecutorEnv


class AwsEnv(ExecutorEnv):

    def __init__(self, profile_details, credentials: AuthResponse, region=None):
        self.profile_details = profile_details
        self.region = self.profile_details['region'] if region is None else region
        self.credentials = credentials

    def setup(self) -> dict:
        environments = {}
        if self.region is not None:
            environments["AWS_DEFAULT_REGION"] = self.region
            environments["AWS_REGION"] = self.region
        return {
                   "AWS_ACCESS_KEY_ID": self.credentials.aws_access_key_id,
                   "AWS_SECRET_ACCESS_KEY": self.credentials.aws_secret_access_key,
                   "AWS_SECURITY_TOKEN": self.credentials.aws_session_token,
                   "AWS_SESSION_TOKEN": self.credentials.aws_session_token
               } | environments

    def cleanup(self) -> list:
        return [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_SECURITY_TOKEN",
            "AWS_CREDENTIAL_FILE",
            "AWS_DEFAULT_PROFILE",
            "AWS_PROFILE",
            "AWS_SDK_LOAD_CONFIG"
        ]
