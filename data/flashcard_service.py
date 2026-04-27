import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import config_data as config
import streamlit as st

class FlashcardService:
    def __init__(self):
        self.chat_model = ChatTongyi(model=config.chat_model)
    
    def get_flashcard_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的教育专家，擅长将复杂知识转化为易于学习的问答对。"),
            ("user", """基于以下文档内容，生成{num_cards}个高质量的问答对（闪卡）：
            
要求：
1. 问题要具体、有针对性，避免模糊问题
2. 答案要准确、简洁，不超过3句话
3. 覆盖文档的核心知识点和关键概念
4. 难度适中，适合学习和复习
5. 每个问答对应该是一个独立的知识点

文档内容：
{document_content}

请严格按照以下JSON格式返回：
[
  {{
    "question": "问题内容",
    "answer": "答案内容",
    "difficulty": "easy/medium/hard"
  }},
  ...
]""")
        ])
    
    def generate_flashcards(self, document_content: str, num_cards: int = 10) -> List[Dict[str, Any]]:
        try:
            prompt = self.get_flashcard_prompt()
            chain = prompt | self.chat_model | StrOutputParser()
            
            result = chain.invoke({
                "document_content": document_content,
                "num_cards": num_cards
            })
            
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                flashcards = json.loads(json_match.group())
            else:
                flashcards = json.loads(result)
            
            for i, card in enumerate(flashcards):
                card["id"] = str(uuid.uuid4())
                card["created_at"] = datetime.now().isoformat()
                card["mastery_level"] = 0
                card["review_count"] = 0
                card["last_reviewed"] = None
                if "difficulty" not in card:
                    card["difficulty"] = "medium"
            
            return flashcards
        
        except Exception as e:
            print(f"生成闪卡时出错: {e}")
            return []
    
    def save_flashcards(self, flashcards: List[Dict[str, Any]], filename: str = None):
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flashcards_{timestamp}.json"
        FlashcardStore.save_set(user_id, filename, flashcards)
        return filename
    
    def load_flashcards(self, filename: str) -> List[Dict[str, Any]]:
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        return FlashcardStore.get_cards(user_id, filename)
    
    def get_all_flashcard_sets(self):
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        return FlashcardStore.get_sets(user_id)
    
    def update_flashcard_progress(self, card_id: str, mastery_level: int, filename: str):
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        return FlashcardStore.update_progress(card_id, user_id, mastery_level)
    
    def export_to_csv(self, filename: str, output_path: str = None):
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        flashcards = FlashcardStore.get_cards(user_id, filename)
        if not flashcards:
            return None
        
        import csv
        import io
        if not output_path:
            output_path = filename.replace('.json', '.csv')
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Question', 'Answer', 'Difficulty', 'Mastery Level', 'Review Count'])
            for card in flashcards:
                writer.writerow([
                    card.get('question', ''),
                    card.get('answer', ''),
                    card.get('difficulty', 'medium'),
                    card.get('mastery_level', 0),
                    card.get('review_count', 0)
                ])
        
        return output_path
    
    def get_set_stats(self, set_name: str) -> Dict:
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        return FlashcardStore.get_stats(user_id, set_name)
    
    def delete_set(self, set_name: str) -> bool:
        from mongodb_store import FlashcardStore
        user_id = st.session_state["user_id"]
        return FlashcardStore.delete_set(user_id, set_name)
