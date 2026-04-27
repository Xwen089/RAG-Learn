import os
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from typing import Sequence

def get_history(session_id):
    return MongoChatMessageHistory(session_id)

class MongoChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id):
        self.session_id = session_id

    def add_messages(self, messages: Sequence[BaseMessage]):
        from mongodb_store import MessageStore
        session_key = f"messages_{self.session_id}"
        import streamlit as st
        if session_key in st.session_state:
            all_messages = list(st.session_state[session_key])
            existing_ids = set()
            for msg in st.session_state.get("_msg_ids", {}).get(self.session_id, []):
                existing_ids.add(msg)
            new_msgs = []
            for msg in messages:
                msg_id = id(msg)
                if msg_id not in existing_ids:
                    role = "assistant" if isinstance(msg, BaseMessage) and hasattr(msg, 'type') and msg.type == "ai" else "user"
                    new_msgs.append({"role": role, "content": msg.content})
            if new_msgs:
                pass

    @property
    def messages(self) -> list[BaseMessage]:
        from mongodb_store import MessageStore
        import streamlit as st
        session_key = f"messages_{self.session_id}"
        if session_key in st.session_state:
            raw = st.session_state[session_key]
            from langchain_core.messages import AIMessage, HumanMessage
            result = []
            for m in raw:
                if m["role"] == "assistant":
                    result.append(AIMessage(content=m["content"]))
                else:
                    result.append(HumanMessage(content=m["content"]))
            return result
        return []

    def clear(self):
        from mongodb_store import MessageStore
        import streamlit as st
        MessageStore.clear(self.session_id)
        session_key = f"messages_{self.session_id}"
        if session_key in st.session_state:
            st.session_state[session_key] = []
