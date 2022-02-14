from ..comm.pubsub import PubSubClient
from .base import BaseCallback
from typing import Any
import json


class PubSubCallback(BaseCallback):
    """A Callback for sending a message to the PubSub Queue Service

    Args:
        project_id (str): Google Cloud project id
        topic_name (str): PubSub topic name
    """

    def __init__(self, project_id: str, topic_name: str):
        self.project = project_id
        self.topic = topic_name

    def callback_function(self, data: Any) -> bool:
        pubsub = PubSubClient(self.project, self.topic)
        try:
            pubsub.send_message(json.dumps(data))
        except Exception:
            return False
        return True
