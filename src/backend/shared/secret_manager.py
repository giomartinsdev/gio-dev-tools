import os

from infisical_sdk import InfisicalSDKClient


class SecretManager:
    def __init__(self):
        self._client = None
        self._project_id = None
        self._env = None

    def _connect(self):
        if self._client is not None:
            return
        client = InfisicalSDKClient(host="http://if.giomartins.dev")
        client.auth.universal_auth.login(
            client_id=os.environ["if_id"],
            client_secret=os.environ["if_secret"]
        )
        self._client = client
        self._project_id = os.environ["if_project_id"]
        self._env = os.environ["if_env"]

    def get_secret(self, secret_name: str) -> str:
        self._connect()
        secret = self._client.secrets.get_secret_by_name(
            secret_name=secret_name,
            project_id=self._project_id,
            environment_slug=self._env,
            secret_path="/",
        )
        return secret.secretValue
