from typing import Any
import requests


class HttpClient:
    """Simple Http Client wrapper for requests library (on progress)"""

    def post(self, url: str, msg: Any, token: str = None):
        """Post json message into url, only Bearer token security

        Args:
            url (str): target url
            msg (Any): message content

        Returns:
            Response: requests Response
        """
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return requests.post(url, data=msg, headers=headers)
