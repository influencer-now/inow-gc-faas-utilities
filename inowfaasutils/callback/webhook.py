from ..comm.http import HttpClient
from .base import BaseCallback
from typing import Any


class WebhookCallback(BaseCallback):
    """A Callback for sending an HTTP Post message

    Args:
        url (str): url for webhook callback
        token (str): security bearer token
    """

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

    def callback_function(self, data: Any) -> bool:
        http = HttpClient()
        try:
            http.post(self.url, data, self.token)
        except Exception:
            return False
        return True
