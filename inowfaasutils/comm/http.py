from typing import Any
import requests


class HttpClient:
    """Simple Http Client wrapper for requests library (on progress)"""

    def post(self, url: str, msg: Any):
        """Post message into url (no security)

        Args:
            url (str): target url
            msg (Any): message content

        Returns:
            Response: requests Response
        """
        return requests.post(url, data=msg)
