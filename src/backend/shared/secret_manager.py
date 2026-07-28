import logging
import os
import time

from infisical_sdk import InfisicalSDKClient

logger = logging.getLogger(__name__)

# On a full host reboot, containers race to start (no real dependency
# ordering in this stack), so a service can come up before infisical/postgres
# are actually accepting connections. Without a retry here, that transient
# unavailability becomes a permanent failure: the service's one-shot _init
# sets an error and stays unhealthy until someone notices and manually
# restarts it — this is the exact pattern behind every "X can't reach
# infisical/postgres after reboot" incident. Retrying with backoff lets the
# service self-heal once its dependencies finish starting, instead.
_CONNECT_MAX_ATTEMPTS = 8
_CONNECT_BACKOFF_BASE_SECONDS = 2
_CONNECT_BACKOFF_MAX_SECONDS = 20


class SecretManager:
    def __init__(self):
        self._client = None
        self._project_id = None
        self._env = None

    def _connect(self):
        if self._client is not None:
            return
        host = os.environ.get("INFISICAL_HOST", "http://infisical:8080")

        last_exc: Exception | None = None
        for attempt in range(1, _CONNECT_MAX_ATTEMPTS + 1):
            try:
                client = InfisicalSDKClient(host=host)
                client.auth.universal_auth.login(
                    client_id=os.environ["if_id"],
                    client_secret=os.environ["if_secret"]
                )
                self._client = client
                self._project_id = os.environ["if_project_id"]
                self._env = os.environ["if_env"]
                return
            except Exception as exc:
                last_exc = exc
                if attempt == _CONNECT_MAX_ATTEMPTS:
                    break
                delay = min(_CONNECT_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), _CONNECT_BACKOFF_MAX_SECONDS)
                logger.warning(
                    f"infisical connect attempt {attempt}/{_CONNECT_MAX_ATTEMPTS} failed: {exc} "
                    f"— retrying in {delay}s"
                )
                time.sleep(delay)
        raise last_exc

    def get_secret(self, secret_name: str) -> str:
        self._connect()
        secret = self._client.secrets.get_secret_by_name(
            secret_name=secret_name,
            project_id=self._project_id,
            environment_slug=self._env,
            secret_path="/",
        )
        return secret.secretValue
