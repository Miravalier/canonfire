import pymongo
from bson import ObjectId
from pydantic import BaseModel, ValidationError
from pymongo import ReturnDocument
from pymongo.collection import Collection
from typing import Generic, List, Type, TypeVar, Union

from ..models import database_models as models


M = TypeVar('M', bound=BaseModel)


def _jsonify_oid(obj: Union[dict, ObjectId, None]):
    if obj is None:
        return None
    elif isinstance(obj, ObjectId):
        return obj.binary.hex()
    else:
        oid: ObjectId = obj.pop("_id", None)
        if oid is not None:
            obj["id"] = oid.binary.hex()
        return obj


def _prepare_filter(obj: Union[dict, str, None]):
    if obj is None:
        return {}

    elif isinstance(obj, str):
        return {"_id": ObjectId(obj)}

    else:
        id = obj.pop("id", None)
        if id is not None:
            obj["_id"] = ObjectId(id)
        return obj


class DocumentCollection(Generic[M]):
    def __init__(self, collection: Collection, model: Type[M]):
        self.collection = collection
        self.model = model
        self.name = collection.name
        self.collection.create_index("name")

    def create(self, obj):
        obj["id"] = self.insert_one(obj)
        return self.post_process_result(obj)

    def pre_process_filter(self, filter: dict):
        return _prepare_filter(filter)

    def post_process_result(self, document: dict) -> M:
        if document is None:
            return None

        try:
            return self.model.model_validate(_jsonify_oid(document))
        except ValidationError as exc:
            for error in exc.errors():
                location = list(error['loc'])
                terminal = location.pop()

                ancestry: list[tuple[dict|list, str|int]] = []
                cursor = document
                for component in location:
                    ancestry.append((cursor, component))
                    cursor = cursor[component]

                if isinstance(cursor, list):
                    cursor.pop(terminal)
                elif isinstance(cursor, set):
                    cursor.discard(error['input'])
                else:
                    del cursor[terminal]

            return self.model.model_validate(_jsonify_oid(document))


    def create_index(self, *args, **kwargs):
        self.collection.create_index(*args, **kwargs)

    def find_one(self, filter: Union[dict, str]) -> M:
        if filter is None:
            return None
        return self.post_process_result(self.collection.find_one(self.pre_process_filter(filter)))

    def find(self, filter: dict = None, *args, **kwargs) -> List[M]:
        return [self.post_process_result(document) for document in self.collection.find(self.pre_process_filter(filter), *args, **kwargs)]

    def delete_one(self, filter: dict = None, *args, **kwargs):
        return self.collection.delete_one(self.pre_process_filter(filter), *args, **kwargs).deleted_count != 0

    def delete_many(self, filter: dict = None, *args, **kwargs):
        return self.collection.delete_many(self.pre_process_filter(filter), *args, **kwargs).deleted_count

    def find_one_and_update(self, filter: dict, update: dict, *args, **kwargs) -> M:
        if filter is None:
            return None
        return self.post_process_result(
            self.collection.find_one_and_update(
                self.pre_process_filter(filter),
                update,
                *args,
                return_document=ReturnDocument.AFTER,
                **kwargs
            )
        )

    def update_many(self, filter: dict, update: dict, *args, **kwargs) -> int:
        return self.collection.update_many(self.pre_process_filter(filter), update, *args, **kwargs).matched_count

    def upsert(self, filter: dict, update: dict, *args, **kwargs):
        return _jsonify_oid(self.collection.update_one(self.pre_process_filter(filter), update, *args, **kwargs, upsert=True).upserted_id)

    def insert_one(self, *args, **kwargs) -> str:
        return _jsonify_oid(self.collection.insert_one(*args, **kwargs).inserted_id)

    def insert_many(self, *args, **kwargs) -> List[str]:
        return [_jsonify_oid(id) for id in self.collection.insert_many(*args, **kwargs).inserted_ids]


# Mongo Client
client = pymongo.MongoClient("mongodb://nonsense_db:27017")
db = client.nonsense_db

# Collections
abilities = DocumentCollection(db.abilities, models.Ability)
abilities.create_index("folder_id")
characters = DocumentCollection(db.characters, models.Character)
characters.create_index("folder_id")
notes = DocumentCollection(db.notes, models.Note)
notes.create_index("folder_id")
items = DocumentCollection(db.items, models.Item)
users = DocumentCollection(db.users, models.User)
combats = DocumentCollection(db.combats, models.Combat)
maps = DocumentCollection(db.maps, models.Map)
messages = DocumentCollection(db.messages, models.Message)
ability_folders = DocumentCollection(db.ability_folders, models.Folder)
character_folders = DocumentCollection(db.character_folders, models.Folder)
note_folders = DocumentCollection(db.note_folders, models.Folder)

sessions = DocumentCollection(db.sessions, models.Session)
sessions.create_index("auth_token")
sessions.create_index("last_auth_date", expireAfterSeconds=2592000)
