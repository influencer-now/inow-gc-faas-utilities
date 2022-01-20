from google.cloud import pubsub_v1


class PubSubClient:
    """PubSub client wrapper based on Google's `pubsub_v1` publisher client, to send simple string messages

    Args:
        project_id (str): Google Cloud project id name
        topic_name (str): PubSub topic name
    """

    def __init__(self, project_id: str, topic_name: str):
        self.project_id: str = project_id
        self.topic_name: str = topic_name

    def send_message(self, msg: str):
        """Sends a message to PubSub queue

        Args:
            msg (str): message content
        """
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(self.project_id, self.topic_name)
        future = publisher.publish(topic_path, msg.encode("utf-8"))
        future.result()
