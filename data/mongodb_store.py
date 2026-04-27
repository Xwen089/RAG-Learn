import os
import json
import uuid
import bcrypt
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import config_data as config

def get_mongo_uri():
    uri = os.environ.get("MONGO_URI")
    if not uri:
        import streamlit as st
        try:
            uri = st.secrets.get("MONGO_URI", "mongodb://localhost:27017")
        except:
            uri = "mongodb://localhost:27017"
    return uri

def get_client():
    uri = get_mongo_uri()
    if "localhost" in uri:
        return MongoClient(uri)
    return MongoClient(uri, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=10000)

def get_rag_db():
    return get_client()["rag_app"]

def get_vector_db():
    return get_client()["rag_vector"]

class UserService:
    @staticmethod
    def register(username: str, password: str) -> Dict:
        if not username or not password:
            return {"ok": False, "msg": "用户名和密码不能为空"}
        if len(username) < 2 or len(username) > 20:
            return {"ok": False, "msg": "用户名长度2-20个字符"}
        if len(password) < 4:
            return {"ok": False, "msg": "密码至少4个字符"}
        try:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            get_rag_db().users.insert_one({
                "_id": username,
                "password_hash": password_hash,
                "created_at": datetime.now().isoformat()
            })
            return {"ok": True, "msg": "注册成功"}
        except DuplicateKeyError:
            return {"ok": False, "msg": "用户名已存在"}
        except Exception as e:
            return {"ok": False, "msg": f"注册失败: {str(e)}"}

    @staticmethod
    def login(username: str, password: str) -> Dict:
        if not username or not password:
            return {"ok": False, "msg": "请输入用户名和密码"}
        user = get_rag_db().users.find_one({"_id": username})
        if not user:
            return {"ok": False, "msg": "用户名不存在"}
        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return {"ok": True, "msg": "登录成功", "user_id": username}
        return {"ok": False, "msg": "密码错误"}

class SessionStore:
    @staticmethod
    def get_all(user_id: str) -> Dict:
        sessions = {}
        for doc in get_rag_db().sessions.find({"user_id": user_id}).sort("updated_at", -1):
            sessions[doc["_id"]] = {
                "id": doc["_id"],
                "name": doc["name"],
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
                "last_message": doc.get("last_message", ""),
                "message_count": doc.get("message_count", 0)
            }
        return sessions

    @staticmethod
    def create(user_id: str, name: str = None) -> Dict:
        session_id = str(uuid.uuid4())
        if not name:
            name = f"新会话 {datetime.now().strftime('%m-%d %H:%M')}"
        session = {
            "_id": session_id,
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_message": "",
            "message_count": 0
        }
        get_rag_db().sessions.insert_one(session)
        session["id"] = session_id
        return session

    @staticmethod
    def update(session_id: str, user_id: str, updates: Dict):
        updates["updated_at"] = datetime.now().isoformat()
        get_rag_db().sessions.update_one(
            {"_id": session_id, "user_id": user_id},
            {"$set": updates}
        )

    @staticmethod
    def delete(session_id: str, user_id: str) -> bool:
        get_rag_db().messages.delete_many({"session_id": session_id, "user_id": user_id})
        result = get_rag_db().sessions.delete_one({"_id": session_id, "user_id": user_id})
        return result.deleted_count > 0

class MessageStore:
    @staticmethod
    def get_messages(session_id: str) -> List[Dict]:
        msgs = list(get_rag_db().messages.find(
            {"session_id": session_id},
            {"_id": 0, "role": 1, "content": 1}
        ).sort("created_at", 1))
        return msgs

    @staticmethod
    def add_messages(session_id: str, user_id: str, messages: List[Dict]):
        now = datetime.now().isoformat()
        docs = []
        for msg in messages:
            docs.append({
                "_id": str(uuid.uuid4()),
                "session_id": session_id,
                "user_id": user_id,
                "role": msg["role"],
                "content": msg["content"],
                "created_at": now
            })
        if docs:
            get_rag_db().messages.insert_many(docs)

    @staticmethod
    def clear(session_id: str):
        get_rag_db().messages.delete_many({"session_id": session_id})

class FlashcardStore:
    @staticmethod
    def get_sets(user_id: str) -> List[Dict]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$set_name",
                "card_count": {"$sum": 1},
                "created_at": {"$max": "$created_at"}
            }},
            {"$sort": {"created_at": -1}}
        ]
        sets = []
        for doc in get_rag_db().flashcards.aggregate(pipeline):
            sets.append({
                "filename": doc["_id"],
                "card_count": doc["card_count"],
                "created_at": doc["created_at"]
            })
        return sets

    @staticmethod
    def save_set(user_id: str, set_name: str, cards: List[Dict]):
        now = datetime.now().isoformat()
        docs = []
        for card in cards:
            card["_id"] = card["id"]
            card["user_id"] = user_id
            card["set_name"] = set_name
            card["created_at"] = now
            docs.append(card)
        if docs:
            get_rag_db().flashcards.insert_many(docs)

    @staticmethod
    def get_cards(user_id: str, set_name: str) -> List[Dict]:
        return list(get_rag_db().flashcards.find(
            {"user_id": user_id, "set_name": set_name},
            {"_id": 0}
        ))

    @staticmethod
    def update_progress(card_id: str, user_id: str, mastery_level: int) -> bool:
        result = get_rag_db().flashcards.update_one(
            {"_id": card_id, "user_id": user_id},
            {"$set": {
                "mastery_level": mastery_level,
                "last_reviewed": datetime.now().isoformat(),
                "$inc": {"review_count": 1}
            }}
        )
        return result.modified_count > 0

    @staticmethod
    def delete_set(user_id: str, set_name: str) -> bool:
        result = get_rag_db().flashcards.delete_many({"user_id": user_id, "set_name": set_name})
        return result.deleted_count > 0

    @staticmethod
    def get_stats(user_id: str, set_name: str) -> Dict:
        cards = list(get_rag_db().flashcards.find(
            {"user_id": user_id, "set_name": set_name},
            {"mastery_level": 1, "review_count": 1}
        ))
        total = len(cards)
        mastered = sum(1 for c in cards if c.get("mastery_level", 0) >= 2)
        reviewed = sum(1 for c in cards if c.get("review_count", 0) > 0)
        avg_mastery = sum(c.get("mastery_level", 0) for c in cards) / total if total else 0
        return {"total": total, "mastered": mastered, "reviewed": reviewed, "avg_mastery": round(avg_mastery, 1)}

class VectorStore:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.collection = get_vector_db().documents

    def add_texts(self, texts: List[str], metadatas: List[Dict], embeddings: List[List[float]]):
        now = datetime.now().isoformat()
        docs = []
        for i, text in enumerate(texts):
            meta = metadatas[i] if i < len(metadatas) else {}
            embedding = embeddings[i] if i < len(embeddings) else []
            docs.append({
                "user_id": self.user_id,
                "text": text,
                "embedding": embedding,
                "metadata": meta,
                "filename": meta.get("source", "unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "created_at": now
            })
        if docs:
            self.collection.insert_many(docs)

    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Dict]:
        pipeline = [
            {"$match": {"user_id": self.user_id, "embedding": {"$exists": True, "$ne": []}}},
            {"$addFields": {
                "score": {
                    "$let": {
                        "vars": {
                            "dot": {"$reduce": {
                                "input": {"$zip": {"inputs": ["$embedding", query_embedding]}},
                                "initialValue": 0.0,
                                "in": {"$add": ["$$value", {"$multiply": [{"$arrayElemAt": ["$$this", 0]}, {"$arrayElemAt": ["$$this", 1]}]}]}
                            }}
                        },
                        "in": "$$dot"
                    }
                }
            }},
            {"$sort": {"score": -1}},
            {"$limit": k},
            {"$project": {"text": 1, "metadata": 1, "score": 1, "_id": 0}}
        ]
        return list(self.collection.aggregate(pipeline))

    def get_files(self) -> List[Dict]:
        pipeline = [
            {"$match": {"user_id": self.user_id}},
            {"$group": {
                "_id": "$filename",
                "chunks": {"$sum": 1},
                "create_time": {"$max": "$created_at"}
            }},
            {"$sort": {"create_time": -1}}
        ]
        files = []
        for doc in self.collection.aggregate(pipeline):
            files.append({
                "filename": doc["_id"],
                "chunks": doc["chunks"],
                "create_time": doc["create_time"]
            })
        return files

    def delete_files(self, filenames: List[str]):
        result = self.collection.delete_many({
            "user_id": self.user_id,
            "filename": {"$in": filenames}
        })
        return result.deleted_count

    def get_document_content(self, filename: str) -> str:
        docs = list(self.collection.find(
            {"user_id": self.user_id, "filename": filename},
            {"text": 1, "chunk_index": 1, "_id": 0}
        ).sort("chunk_index", 1))
        return "\n\n".join(d["text"] for d in docs)

    def get_selected_content(self, filenames: List[str]) -> str:
        contents = []
        for name in filenames:
            content = self.get_document_content(name)
            if content:
                contents.append(f"=== 文件: {name} ===\n{content}\n")
        return "\n".join(contents)
