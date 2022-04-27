from typing import List
from google.cloud import pubsub_v1
from concurrent import futures


class PubSubClient:
    """PubSub client wrapper based on Google's `pubsub_v1` publisher client, to send simple string messages

    Args:
        project_id (str): Google Cloud project id name
        topic_name (str): PubSub topic name
    """

    def __init__(self, project_id: str, topic_name: str):
        self.project_id: str = project_id
        self.topic_name: str = topic_name

    def _callback(self, future: pubsub_v1.publisher.futures.Future) -> None:
        future.result()

    def send_message(self, msg: str):
        """Sends a message to PubSub queue

        Args:
            msg (str): message content
        """
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(self.project_id, self.topic_name)
        future = publisher.publish(topic_path, msg.encode("utf-8"))
        future.result()

    def send_messages(self, msgs: List[str]):
        """Sends a message to PubSub queue

        Args:
            msgs (List[str]): messages content
        """
        batch_settings = pubsub_v1.types.BatchSettings(
            max_latency=0.2,  # 200ms
        )
        publisher = pubsub_v1.PublisherClient(batch_settings)
        topic_path = publisher.topic_path(self.project_id, self.topic_name)
        publish_futures = []

        for msg in msgs:
            data = msg.encode("utf-8")
            publish_future = publisher.publish(topic_path, data)
            publish_future.add_done_callback(self._callback)
            publish_futures.append(publish_future)

        futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)
