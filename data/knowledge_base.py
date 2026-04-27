import os
import config_data as config
import hashlib
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
from typing import List

def check_md5(md5_str: str, user_id: str):
    from mongodb_store import db_vector
    return db_vector.md5_cache.find_one({"md5": md5_str, "user_id": user_id}) is not None

def save_md5(md5_str: str, user_id: str):
    from mongodb_store import db_vector
    db_vector.md5_cache.insert_one({"md5": md5_str, "user_id": user_id})

def get_string_md5(input_str: str, encoding='utf-8'):
    str_bytes = input_str.encode(encoding=encoding)
    md5_obj = hashlib.md5()
    md5_obj.update(str_bytes)
    return md5_obj.hexdigest()

class KnowledgeBaseService(object):
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.embedding_model = DashScopeEmbeddings(model=config.embedding_model)
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )

    def upload_by_str(self, data, filename, page=None):
        from mongodb_store import VectorStore
        md5_hex = get_string_md5(data)
        if check_md5(md5_hex, self.user_id):
            return "[跳过] 内容已存在于知识库中"
        
        if len(data) > config.max_split_char_number:
            knowledge_chunks = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        metadata = {
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": self.user_id
        }
        if page is not None:
            metadata["page"] = page

        metadatas = []
        for chunk_index, _ in enumerate(knowledge_chunks, start=1):
            chunk_meta = dict(metadata)
            chunk_meta["chunk_index"] = chunk_index
            metadatas.append(chunk_meta)

        # 生成 embedding
        embeddings = self.embedding_model.embed_documents(knowledge_chunks)
        
        vs = VectorStore(self.user_id)
        vs.add_texts(knowledge_chunks, metadatas, embeddings)
        
        save_md5(md5_hex, self.user_id)
        return "上传成功,内容已载入向量库"

    def upload_batch(self, documents):
        results = []
        for doc in documents:
            text = doc.get('text', '')
            filename = doc.get('filename', 'unknown')
            page = doc.get('page', None)
            if not text:
                results.append(f"{filename}: 空内容，跳过")
                continue
            result = self.upload_by_str(text, filename, page)
            results.append(f"{filename}: {result}")
        return results

    def get_uploaded_files(self):
        from mongodb_store import VectorStore
        vs = VectorStore(self.user_id)
        return vs.get_files()

    def delete_files(self, filenames):
        from mongodb_store import VectorStore
        vs = VectorStore(self.user_id)
        return vs.delete_files(filenames)
    
    def get_document_content(self, filename: str) -> str:
        from mongodb_store import VectorStore
        vs = VectorStore(self.user_id)
        return vs.get_document_content(filename)
    
    def get_selected_documents_content(self, filenames: List[str]) -> str:
        from mongodb_store import VectorStore
        vs = VectorStore(self.user_id)
        return vs.get_selected_content(filenames)
