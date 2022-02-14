from typing import Optional
from google.cloud.datastore.entity import Entity
from google.cloud import datastore

from ..misc.singleton import Singleton


class DataStoreClient(metaclass=Singleton):
    """DataStore client singleton based on datastore offical library

    Args:
        project_id (str): Google Cloud project id
    """

    _client: datastore.Client

    def __init__(self, project_id: str):
        self._client = datastore.Client(project=project_id)

    @property
    def client(self):
        return self._client

    def upsert(self, entity: str, id: str, data: dict) -> bool:
        """Update or insert entity to datastore

        Args:
            entity (str): entity name
            id (str): indexed id
            data (dict): data to insert (without id)

        Returns:
            bool: True if success
        """
        try:
            with self._client.transaction():
                key = self._client.key(entity, id)
                task = self._client.entity(key=key)
                task.update(data)
                self._client.put(task)
            return True
        except Exception as ex:
            print(ex.__traceback__)
            return False

    def get_entity(self, entity: str, id: str) -> Optional[Entity]:
        """Get entity from DataStore

        Args:
            entity (str): entity name
            id (str): indexed id

        Returns:
            Optional[Entity]: entity. None if not found
        """
        try:
            item: Entity
            key = self._client.key(entity, id)
            item = self._client.get(key)
            return item
        except Exception:
            return None

    def increment_cnt_with_id(
        self, entity: str, id: str, cnt_field: str, step: int
    ) -> Optional[Entity]:
        """Increment count of a datastore data field

        Args:
            entity (str): entity name
            id (str): indexed id
            cnt_field (str): field to increment count
            step (int): quantity to be incremented

        Returns:
            Optional[Entity]: entity with increment.
            None if not found
        """
        try:
            item = self.get_entity(entity, id)
            item[cnt_field] += step
            return item
        except Exception:
            return None

    def increment_cnt_with_entity(
        self, item: Entity, cnt_field: str, step: int
    ) -> Optional[Entity]:
        """Increment count of a datastore data field

        Args:
            item (Entity): entity to be changed
            cnt_field (str): field to increment count
            step (int): quantity to be incremented

        Returns:
            Optional[Entity]: entity with increment.
            None if not found
        """
        try:
            item[cnt_field] += step
            return item
        except Exception:
            return None
