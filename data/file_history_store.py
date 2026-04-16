import os
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from typing import Sequence
import json

def get_history(session_id):
    return FileChatMessageHistory(session_id,"./chat_history")

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