import os

from infisical_sdk import InfisicalSDKClient


class SecretManager:
    def __init__(self):
        self.client = InfisicalSDKClient(host="http://if.giomartins.dev")
        self.client.auth.universal_auth.login(
            client_id=os.environ["if_id"],
            client_secret=os.environ["if_secret"]
        )
        self._project_id = os.environ["if_project_id"]
        self._env = os.environ["if_env"]

    def get_secret(self, secret_name: str) -> str:
        secret = self.client.getSecret(
            secret_name=secret_name,
            project_id=self._project_id,
            environment_slug=self._env
        )
        return secret.secretValue