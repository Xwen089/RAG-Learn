import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import config_data as config

class FlashcardService:
    def __init__(self):
        self.chat_model = ChatTongyi(model=config.chat_model)
        self.flashcards_dir = "./flashcards"
        os.makedirs(self.flashcards_dir, exist_ok=True)
    
    def get_flashcard_prompt(self):
        """获取闪卡生成提示词"""
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
        """生成闪卡"""
        try:
            prompt = self.get_flashcard_prompt()
            chain = prompt | self.chat_model | StrOutputParser()
            
            result = chain.invoke({
                "document_content": document_content,
                "num_cards": num_cards
            })
            
            # 解析JSON响应
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                flashcards = json.loads(json_match.group())
            else:
                # 尝试直接解析
                flashcards = json.loads(result)
            
            # 添加元数据
            for i, card in enumerate(flashcards):
                card["id"] = str(uuid.uuid4())
                card["created_at"] = datetime.now().isoformat()
                card["mastery_level"] = 0  # 0-未掌握, 1-基本掌握, 2-熟练掌握
                card["review_count"] = 0
                card["last_reviewed"] = None
                
                # 确保difficulty字段存在
                if "difficulty" not in card:
                    card["difficulty"] = "medium"
            
            return flashcards
            
        except Exception as e:
            print(f"生成闪卡时出错: {e}")
            return []
    
    def save_flashcards(self, flashcards: List[Dict[str, Any]], filename: str = None):
        """保存闪卡到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flashcards_{timestamp}.json"
        
        filepath = os.path.join(self.flashcards_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_cards": len(flashcards),
                    "source_files": list(set(card.get("source_file", "") for card in flashcards if card.get("source_file")))
                },
                "flashcards": flashcards
            }, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def load_flashcards(self, filepath: str) -> List[Dict[str, Any]]:
        """从文件加载闪卡"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("flashcards", [])
        except Exception as e:
            print(f"加载闪卡时出错: {e}")
            return []
    
    def get_all_flashcard_sets(self):
        """获取所有闪卡学习集"""
        sets = []
        for filename in os.listdir(self.flashcards_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.flashcards_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sets.append({
                            "filename": filename,
                            "filepath": filepath,
                            "metadata": data.get("metadata", {}),
                            "card_count": len(data.get("flashcards", []))
                        })
                except:
                    continue
        return sets
    
    def update_flashcard_progress(self, card_id: str, mastery_level: int, filepath: str):
        """更新闪卡学习进度"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            flashcards = data.get("flashcards", [])
            for card in flashcards:
                if card.get("id") == card_id:
                    card["mastery_level"] = mastery_level
                    card["review_count"] = card.get("review_count", 0) + 1
                    card["last_reviewed"] = datetime.now().isoformat()
                    break
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"更新闪卡进度时出错: {e}")
            return False
    
    def export_to_csv(self, filepath: str, output_path: str = None):
        """导出闪卡为CSV格式"""
        try:
            flashcards = self.load_flashcards(filepath)
            if not flashcards:
                return None
            
            import csv
            if not output_path:
                output_path = filepath.replace('.json', '.csv')
            
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
        except Exception as e:
            print(f"导出CSV时出错: {e}")
            return None