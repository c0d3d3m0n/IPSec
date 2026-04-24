import json
import logging
import time
from typing import Any

import requests


logger = logging.getLogger(__name__)


class MTLSClient:
    def __init__(self, cert_path: str, key_path: str, ca_cert_path: str):
        self.session = requests.Session()
        self.session.cert = (cert_path, key_path)
        # Use system CA bundle for server certificate verification (server uses Let's Encrypt)
        # The ca_cert_path is for client authentication only, not server verification
        self.session.verify = True
        logger.info(
            "MTLSClient initialized cert=%s key=%s ca=%s verify=%s",
            cert_path,
            key_path,
            ca_cert_path,
            self.session.verify,
        )

    def get(self, url: str, **kwargs):
        return self._request("GET", url, None, **kwargs)

    def post(self, url: str, json_payload: dict[str, Any], **kwargs):
        return self._request("POST", url, json_payload, **kwargs)

    def _request(self, method: str, url: str, payload: dict[str, Any] | None, **kwargs):
        delays = [1, 2, 4]
        for attempt, delay in enumerate(delays, start=1):
            try:
                has_token = "X-Enrollment-Token" in (kwargs.get("headers") or {})
                logger.info(
                    "mTLS request attempt=%s method=%s url=%s has_token_header=%s",
                    attempt,
                    method,
                    url,
                    has_token,
                )
                if method == "GET":
                    response = self.session.get(url, **kwargs)
                else:
                    response = self.session.post(url, json=payload, **kwargs)

                logger.info("mTLS response status=%s method=%s url=%s", response.status_code, method, url)

                if response.status_code == 403:
                    try:
                        body = response.json()
                    except Exception:
                        body = {}
                    if body.get("reason") == "zero_trust_deny":
                        logger.error(
                            "Zero Trust deny: score=%s reasons=%s",
                            body.get("score"),
                            body.get("reasons"),
                        )
                        return response
                return response
            except requests.exceptions.SSLError as exc:
                logger.error("mTLS handshake failed for url=%s: %s", url, exc)
                raise
            except requests.exceptions.ConnectionError as exc:
                logger.warning("Connection error on attempt %s: %s", attempt, exc)
                if attempt == len(delays):
                    raise
                time.sleep(delay)

        raise RuntimeError("Unexpected retry loop exit")
