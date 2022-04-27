from typing import List, Optional, Union
from google.cloud import firestore
from google.cloud.firestore import (
    DocumentSnapshot,
    DocumentReference,
    CollectionReference,
)

from ..misc.singleton import Singleton


class FireStoreClient(metaclass=Singleton):
    """Filestore client singleton based on Firestore offical library

    Args:
        project_id (str): Google Cloud project id
    """

    _client: firestore.Client

    def __init__(self, project_id: str = None):
        self._client = firestore.Client(project=project_id)

    @property
    def client(self):
        return self._client

    def upsert(
        self,
        collection_name: str,
        id: str,
        data: Union[dict, DocumentSnapshot],
        parent_document: Optional[DocumentReference] = None,
    ) -> bool:
        """Update or insert entity to Firestore

        Args:
            collection_name (str): collection name
            id (str): indexed id
            data (Union[dict,DocumentSnapshot]): data to insert (without id)
            parent_document (Optional[DocumentReference]): parent document for nested collections.
            Defaults to None.

        Returns:
            bool: True if success
        """
        try:
            root_ref: Union[firestore.Client, DocumentReference] = (
                self._client if parent_document is None else parent_document
            )
            doc_id = id if id is not None else "self"
            root_ref.collection(collection_name).document(doc_id).set(
                data.to_dict() if isinstance(data, DocumentSnapshot) else data,
                merge=True
            )
            return True
        except Exception as ex:
            print(ex.__traceback__)
            return False

    def get_document_ref(
        self,
        collection_name: str,
        id: str,
        shard_collection_name: Optional[str] = None,
        shard_idx_list: Optional[List[int]] = None,
    ) -> Optional[DocumentReference]:
        """Get entity from Firestore

        Args:
            collection_name (str): collection name
            id (str): indexed id
            shard_collection_name (Optional[str]): collection name of shards.
            shard_idx_list (Optional[List[int]]): subjobs child index tree definition. Default None.

        Returns:
            Optional[DocumentReference]: entity. None if not found
        """
        try:
            doc_ref: DocumentReference = self._client.collection(
                collection_name
            ).document(id)
            if shard_collection_name is not None:
                for idx in shard_idx_list:
                    shards_ref: CollectionReference = doc_ref.collection(
                        shard_collection_name
                    )
                    doc_ref = shards_ref.document(str(idx))
            return doc_ref
        except Exception:
            return None

    def get_document_snapshot(
        self,
        collection_name: str,
        id: str,
        shard_collection_name: Optional[str] = None,
        shard_idx_list: Optional[List[int]] = None,
    ) -> Optional[DocumentSnapshot]:
        """Get entity from Firestore

        Args:
            collection_name (str): collection name
            id (str): indexed id
            shard_collection_name (Optional[str]): collection name of shards.
            shard_idx_list (Optional[List[int]]): subjobs child index tree definition. Default None.

        Returns:
            Optional[DocumentSnapshot]: entity. None if not found
        """
        try:
            return self.get_document_ref(
                collection_name, id, shard_collection_name, shard_idx_list
            ).get()
        except Exception:
            return None

    def delete_document(self, doc_ref: DocumentReference):
        """Deletes document

        Args:
            doc_ref (DocumentReference): _description_
        """

        doc_ref.delete()

    def has_documents(
        self, collection_name: str, parent_document: Optional[DocumentReference] = None
    ):
        root_ref: Union[firestore.Client, DocumentReference] = (
            self._client if parent_document is None else parent_document
        )
        return len(root_ref.collection(collection_name).limit(1).get()) > 0

    def increment_cnt_with_id(
        self,
        collection_name: str,
        id: str,
        cnt_field: str,
        step: int,
        shard_collection_name: Optional[str] = None,
        shard_idx_list: Optional[List[int]] = None,
    ) -> Optional[DocumentSnapshot]:
        """Increment count of a Firestore data field

        Args:
            collection_name (str): collection name
            id (str): indexed id
            cnt_field (str): field to increment count
            step (int): quantity to be incremented
            shard_collection_name (Optional[str]): collection name of shards.
            shard_idx_list (Optional[List[int]]): subjobs child index tree definition. Default None.

        Returns:
            Optional[DocumentSnapshot]: document with incremented counter.
            None if not found
        """
        try:
            item = self.get_document_snapshot(
                collection_name, id, shard_collection_name, shard_idx_list
            )
            item._data[cnt_field] += step
            return item
        except Exception:
            return None
