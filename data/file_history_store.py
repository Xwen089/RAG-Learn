import os
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from typing import Sequence, Dict, Any
import json
import uuid
from datetime import datetime

def get_history(session_id):
    return FileChatMessageHistory(session_id,"./chat_history")

class SessionManager:
    """会话管理器，负责会话元数据的持久化"""
    
    def __init__(self, storage_path="./chat_history"):
        self.storage_path = storage_path
        self.sessions_file = os.path.join(storage_path, "sessions.json")
        os.makedirs(storage_path, exist_ok=True)
    
    def load_sessions(self) -> Dict[str, Dict[str, Any]]:
        """加载所有会话"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    sessions_data = json.load(f)
                    # 确保数据格式正确
                    if isinstance(sessions_data, dict):
                        return sessions_data
            return {}
        except Exception as e:
            print(f"加载会话数据时出错: {e}")
            return {}
    
    def save_sessions(self, sessions: Dict[str, Dict[str, Any]]):
        """保存所有会话"""
        try:
            with open(self.sessions_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话数据时出错: {e}")
    
    def create_session(self, name=None) -> Dict[str, Any]:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        if not name:
            name = f"新会话 {datetime.now().strftime('%m-%d %H:%M')}"
        
        session_data = {
            "id": session_id,
            "name": name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_message": "",
            "message_count": 0,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return session_data
    
    def update_session(self, session_id: str, updates: Dict[str, Any], sessions: Dict[str, Dict[str, Any]]):
        """更新会话信息"""
        if session_id in sessions:
            sessions[session_id].update(updates)
            sessions[session_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_sessions(sessions)
    
    def delete_session(self, session_id: str, sessions: Dict[str, Dict[str, Any]]) -> bool:
        """删除会话"""
        if session_id in sessions:
            # 删除会话元数据
            del sessions[session_id]
            self.save_sessions(sessions)
            
            # 删除对应的历史文件
            history_file = os.path.join(self.storage_path, session_id)
            try:
                if os.path.exists(history_file):
                    os.remove(history_file)
            except Exception as e:
                print(f"删除历史文件时出错: {e}")
            
            return True
        return False
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话（包括从文件系统发现的）"""
        sessions = self.load_sessions()
        
        # 扫描文件系统中的历史文件，确保没有遗漏的会话
        if os.path.exists(self.storage_path):
            for filename in os.listdir(self.storage_path):
                if filename != "sessions.json" and not filename.endswith(".json"):
                    session_id = filename
                    if session_id not in sessions:
                        # 发现未记录的会话，创建基本记录
                        sessions[session_id] = {
                            "id": session_id,
                            "name": f"发现会话 {session_id[:8]}",
                            "created_at": datetime.fromtimestamp(os.path.getctime(os.path.join(self.storage_path, filename))).strftime("%Y-%m-%d %H:%M:%S"),
                            "last_message": "",
                            "message_count": 0,
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
        
        return sessions

class FileChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, session_id,storage_path):
        self.session_id = session_id
        self.storage_path = storage_path    #不同会话id的存储文件，所在的文件夹路径
        self.file_path = os.path.join(self.storage_path, self.session_id)  #完整文件路径

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def add_messages(self, messages:Sequence[BaseMessage]):
        all_messages = list(self.messages)
        all_messages.extend(messages)  #将新消息添加到现有消息列表中

        new_messages = [message_to_dict(message) for message in all_messages]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f)

    @property
    def messages(self) -> list[BaseMessage]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)
                return messages_from_dict(messages_data)  #将json数据转换为BaseMessage对象列表
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([], f)