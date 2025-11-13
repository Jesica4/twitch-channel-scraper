import logging
import time
from typing import Any, Dict, Optional

import requests

class RequestHandler:
    """
    Thin wrapper around requests to call the Twitch Helix API with retries and logging.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        access_token: str,
        max_retries: int = 3,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.access_token = access_token
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }
        if extra:
            headers.update(extra)
        return headers

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        attempt = 0
        backoff = 1.0

        while True:
            attempt += 1
            try:
                self.logger.debug("GET %s params=%s attempt=%d", url, params, attempt)
                resp = requests.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    # Rate limited; respect Retry-After if provided
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else backoff
                    self.logger.warning("Rate limited by Twitch, sleeping for %.2fs", delay)
                    time.sleep(delay)
                    backoff *= 2
                    continue

                if 200 <= resp.status_code < 300:
                    try:
                        return resp.json()
                    except ValueError:
                        self.logger.error("Failed to decode JSON from %s", url)
                        return {}

                self.logger.warning(
                    "Unexpected status from %s: %d %s",
                    url,
                    resp.status_code,
                    resp.text[:200],
                )
            except requests.RequestException as exc:
                self.logger.warning("Request error calling %s: %s", url, exc)

            if attempt >= self.max_retries:
                self.logger.error(
                    "Exceeded max retries (%d) for %s. Returning empty result.",
                    self.max_retries,
                    url,
                )
                return {}

            sleep_for = backoff
            self.logger.info("Retrying %s in %.2fs...", url, sleep_for)
            time.sleep(sleep_for)
            backoff *= 2