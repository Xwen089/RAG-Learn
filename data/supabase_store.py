import os
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash

def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        import streamlit as st
        try:
            url = st.secrets.get("DATABASE_URL", "")
        except:
            url = ""
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(url)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(username),
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_message TEXT DEFAULT '',
            message_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            user_id TEXT NOT NULL REFERENCES users(username),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(username),
            set_name TEXT NOT NULL,
            question TEXT,
            answer TEXT,
            difficulty TEXT DEFAULT 'medium',
            mastery_level INTEGER DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            last_reviewed TEXT,
            source_files TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(username),
            filename TEXT NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            text TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            embedding_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md5_cache (
            md5 TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(username)
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_flashcards_user_set ON flashcards(user_id, set_name);
        CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
    """)
    conn.commit()
    cur.close()
    conn.close()

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
            conn = get_conn()
            cur = conn.cursor()
            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s)",
                (username, password_hash, datetime.now().isoformat())
            )
            conn.commit()
            cur.close()
            conn.close()
            return {"ok": True, "msg": "注册成功"}
        except psycopg2.errors.UniqueViolation:
            return {"ok": False, "msg": "用户名已存在"}
        except Exception as e:
            return {"ok": False, "msg": f"注册失败: {str(e)}"}

    @staticmethod
    def login(username: str, password: str) -> Dict:
        if not username or not password:
            return {"ok": False, "msg": "请输入用户名和密码"}
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return {"ok": False, "msg": "用户名不存在"}
            if check_password_hash(row[0], password):
                return {"ok": True, "msg": "登录成功", "user_id": username}
            return {"ok": False, "msg": "密码错误"}
        except Exception as e:
            return {"ok": False, "msg": f"登录失败: {str(e)}"}

class SessionStore:
    @staticmethod
    def get_all(user_id: str) -> Dict:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, name, created_at, updated_at, last_message, message_count FROM sessions WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,)
        )
        sessions = {}
        for row in cur.fetchall():
            sessions[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_message": row["last_message"] or "",
                "message_count": row["message_count"] or 0
            }
        cur.close()
        conn.close()
        return sessions

    @staticmethod
    def create(user_id: str, name: str = None) -> Dict:
        session_id = str(uuid.uuid4())
        if not name:
            name = f"新会话 {datetime.now().strftime('%m-%d %H:%M')}"
        now = datetime.now().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (id, user_id, name, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
            (session_id, user_id, name, now, now)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"id": session_id, "name": name, "created_at": now, "updated_at": now, "last_message": "", "message_count": 0}

    @staticmethod
    def update(session_id: str, user_id: str, updates: Dict):
        updates["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = %s" for k in updates.keys())
        vals = list(updates.values()) + [session_id, user_id]
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"UPDATE sessions SET {sets} WHERE id = %s AND user_id = %s", vals)
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def delete(session_id: str, user_id: str) -> bool:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE session_id = %s AND user_id = %s", (session_id, user_id))
        cur.execute("DELETE FROM sessions WHERE id = %s AND user_id = %s", (session_id, user_id))
        deleted = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        return deleted

class MessageStore:
    @staticmethod
    def get_messages(session_id: str) -> List[Dict]:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT role, content FROM messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        msgs = [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return msgs

    @staticmethod
    def add_messages(session_id: str, user_id: str, messages: List[Dict]):
        now = datetime.now().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        for msg in messages:
            cur.execute(
                "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), session_id, user_id, msg["role"], msg["content"], now)
            )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def clear(session_id: str):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
        conn.commit()
        cur.close()
        conn.close()

class FlashcardStore:
    @staticmethod
    def get_sets(user_id: str) -> List[Dict]:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT set_name, COUNT(*) as card_count, MAX(created_at) as created_at FROM flashcards WHERE user_id = %s GROUP BY set_name ORDER BY created_at DESC",
            (user_id,)
        )
        sets = [{"filename": r["set_name"], "card_count": r["card_count"], "created_at": r["created_at"]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return sets

    @staticmethod
    def save_set(user_id: str, set_name: str, cards: List[Dict]):
        now = datetime.now().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        for card in cards:
            cur.execute(
                "INSERT INTO flashcards (id, user_id, set_name, question, answer, difficulty, mastery_level, review_count, last_reviewed, source_files, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (card["id"], user_id, set_name, card.get("question"), card.get("answer"),
                 card.get("difficulty", "medium"), card.get("mastery_level", 0),
                 card.get("review_count", 0), card.get("last_reviewed"),
                 json.dumps(card.get("source_files", []), ensure_ascii=False), now)
            )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def get_cards(user_id: str, set_name: str) -> List[Dict]:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, question, answer, difficulty, mastery_level, review_count, last_reviewed, source_files, created_at FROM flashcards WHERE user_id = %s AND set_name = %s",
            (user_id, set_name)
        )
        cards = []
        for r in cur.fetchall():
            card = dict(r)
            try:
                card["source_files"] = json.loads(card["source_files"]) if card["source_files"] else []
            except:
                card["source_files"] = []
            cards.append(card)
        cur.close()
        conn.close()
        return cards

    @staticmethod
    def update_progress(card_id: str, user_id: str, mastery_level: int) -> bool:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE flashcards SET mastery_level = %s, review_count = review_count + 1, last_reviewed = %s WHERE id = %s AND user_id = %s",
            (mastery_level, datetime.now().isoformat(), card_id, user_id)
        )
        ok = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        return ok

    @staticmethod
    def delete_set(user_id: str, set_name: str) -> bool:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM flashcards WHERE user_id = %s AND set_name = %s", (user_id, set_name))
        ok = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        return ok

    @staticmethod
    def get_stats(user_id: str, set_name: str) -> Dict:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN mastery_level >= 2 THEN 1 ELSE 0 END) as mastered, SUM(CASE WHEN review_count > 0 THEN 1 ELSE 0 END) as reviewed, COALESCE(AVG(mastery_level), 0) as avg_mastery FROM flashcards WHERE user_id = %s AND set_name = %s",
            (user_id, set_name)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return {
            "total": row["total"],
            "mastered": row["mastered"] or 0,
            "reviewed": row["reviewed"] or 0,
            "avg_mastery": round(float(row["avg_mastery"]), 1)
        }

class VectorStore:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def add_texts(self, texts: List[str], metadatas: List[Dict], embeddings: List[List[float]]):
        now = datetime.now().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        for i, text in enumerate(texts):
            meta = metadatas[i] if i < len(metadatas) else {}
            cur.execute(
                "INSERT INTO documents (id, user_id, filename, chunk_index, text, metadata_json, embedding_json, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), self.user_id, meta.get("source", "unknown"),
                 meta.get("chunk_index", 0), text,
                 json.dumps(meta, ensure_ascii=False),
                 json.dumps(embeddings[i] if i < len(embeddings) else []),
                 now)
            )
        conn.commit()
        cur.close()
        conn.close()

    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Dict]:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT text, metadata_json FROM documents WHERE user_id = %s",
            (self.user_id,)
        )
        results = []
        for row in cur.fetchall():
            try:
                emb = json.loads(row.get("embedding_json", "[]"))
            except:
                emb = []
            if not emb:
                continue
            score = sum(a * b for a, b in zip(emb, query_embedding))
            results.append({"text": row["text"], "metadata": json.loads(row["metadata_json"]), "score": score})
        cur.close()
        conn.close()
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def get_files(self) -> List[Dict]:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT filename, COUNT(*) as chunks, MAX(created_at) as create_time FROM documents WHERE user_id = %s GROUP BY filename ORDER BY create_time DESC",
            (self.user_id,)
        )
        files = [{"filename": r["filename"], "chunks": r["chunks"], "create_time": r["create_time"]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return files

    def delete_files(self, filenames: List[str]):
        conn = get_conn()
        cur = conn.cursor()
        import psycopg2.extras
        cur.execute(
            "DELETE FROM documents WHERE user_id = %s AND filename = ANY(%s)",
            (self.user_id, filenames)
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return deleted

    def get_document_content(self, filename: str) -> str:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT text FROM documents WHERE user_id = %s AND filename = %s ORDER BY chunk_index ASC",
            (self.user_id, filename)
        )
        texts = [r["text"] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return "\n\n".join(texts)

    def get_selected_content(self, filenames: List[str]) -> str:
        contents = []
        for name in filenames:
            content = self.get_document_content(name)
            if content:
                contents.append(f"=== 文件: {name} ===\n{content}\n")
        return "\n".join(contents)

def check_md5(md5_str: str, user_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM md5_cache WHERE md5 = %s AND user_id = %s", (md5_str, user_id))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def save_md5(md5_str: str, user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO md5_cache (md5, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (md5_str, user_id))
    conn.commit()
    cur.close()
    conn.close()
