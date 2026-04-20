#知识库
import os
import config_data as config
import hashlib
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
from typing import List

def check_md5(md5_str:str):
    """检查传入的md5字符串是否已经被处理过"""
    if not os.path.exists(config.md5_path):
        open(config.md5_path,"w",encoding='utf-8').close() #如果文件不存在，创建一个空文件
        return False #未处理
    else:
        for line in open(config.md5_path,"r",encoding='utf-8').readlines(): #读取文件内容
            line = line.strip()     #处理字符串前后的空格和回车
            if line == md5_str:     #如果文件中存在相同的md5字符串，说明已经处理过了
                return True          #已处理
        return False             #未处理

def save_md5(md5_str:str):
    '''将传入的md5字符串保存到文件中'''
    open(config.md5_path,"a",encoding='utf-8').write(md5_str+"\n") #将md5字符串写入文件，换行分隔

def get_string_md5(input_str:str,encoding='utf-8'):
    '''传入字符串转换为md5值'''

    #将字符串转化为bytes字节数组
    str_bytes = input_str.encode(encoding=encoding)
    
    #创建md5对象
    md5_obj = hashlib.md5()
    md5_obj.update(str_bytes)#更新md5对象的内容为字符串的字节数组
    md5_hex = md5_obj.hexdigest() #获取md5对象的十六进制字符串表示
    return md5_hex


class KnowledgeBaseService(object):
    '''知识库服务类'''
    def __init__(self):
        os.makedirs(config.persist_directory, exist_ok=True) #创建数据库本地存储文件夹
        self.chroma = Chroma(
            collection_name=config.collection_name,     #数据库的表名
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,     #数据库本地存储文件夹
        ) #向量存储实例Chroma对象
        
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,   #分割后的文本段最大长度
            chunk_overlap=config.chunk_overlap, #连续文本段之间的字符重叠数量
            separators=config.separators,   #自然段落分割符列表，优先级从高到低
            length_function=len,            #计算文本长度的函数，默认为len()，也可以自定义函数来计算文本长度
        ) #文本分块器实例对象

    def upload_by_str(self,data,filename,page=None):
        '''将传入的字符串进行语义切分并向量化存储，可选写入页码元数据'''
        md5_hex = get_string_md5(data) #得到传入字符串的md5值
        if check_md5(md5_hex): #检查md5值是否已经被处理过
            return "[跳过] 内容已存在于知识库中"
        
        if len(data) > config.max_split_char_number: #如果文本长度小于分割的阈值，就不进行分割，直接存入数据库
            knowledge_chunks = self.spliter.split_text(data) #对文本进行分块，得到文本块列表
        else:
            knowledge_chunks = [data] #不进行分块，直接将整个文本作为一个块

        metadata = {
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "Shelly"
        }
        if page is not None:
            metadata["page"] = page

        metadatas = []
        for chunk_index, _ in enumerate(knowledge_chunks, start=1):
            chunk_meta = dict(metadata)
            chunk_meta["chunk_index"] = chunk_index
            metadatas.append(chunk_meta)

        self.chroma.add_texts(  #内容加载到Chroma数据库中
            knowledge_chunks,
            metadatas=metadatas,
            ) #将文本块列表存入数据库，元数据中记录文件名
        
        save_md5(md5_hex) #将md5值保存到文件中，表示已经处理过了
        return "上传成功,内容已载入向量库"

    def upload_batch(self, documents):
        '''批量上传多个文档
        documents: 列表，每个元素为字典，包含 'text', 'filename', 'page' 键
        '''
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
        '''获取已上传的文件列表'''
        try:
            # 从Chroma数据库中获取所有文档的元数据
            collection = self.chroma.get()
            if not collection or 'metadatas' not in collection:
                return []
            
            # 提取唯一的文件名
            files = {}
            for metadata in collection['metadatas']:
                if metadata and 'source' in metadata:
                    filename = metadata['source']
                    if filename not in files:
                        files[filename] = {
                            'filename': filename,
                            'create_time': metadata.get('create_time', '未知'),
                            'chunks': 0
                        }
                    files[filename]['chunks'] += 1
            
            return list(files.values())
        except Exception as e:
            print(f"获取文件列表时出错: {e}")
            return []

    def delete_files(self, filenames):
        '''删除指定的文件
        filenames: 要删除的文件名列表
        '''
        deleted_count = 0
        try:
            # 获取所有文档
            collection = self.chroma.get()
            if not collection or 'ids' not in collection or 'metadatas' not in collection:
                return 0
            
            # 找出要删除的文档ID
            ids_to_delete = []
            for i, metadata in enumerate(collection['metadatas']):
                if metadata and 'source' in metadata and metadata['source'] in filenames:
                    ids_to_delete.append(collection['ids'][i])
            
            # 删除文档
            if ids_to_delete:
                self.chroma.delete(ids=ids_to_delete)
                deleted_count = len(ids_to_delete)
            
            return deleted_count
        except Exception as e:
            print(f"删除文件时出错: {e}")
            return 0
    
    def get_document_content(self, filename: str) -> str:
        '''获取指定文件的完整内容'''
        try:
            collection = self.chroma.get()
            if not collection or 'documents' not in collection or 'metadatas' not in collection:
                return ""
            
            content_parts = []
            for i, metadata in enumerate(collection['metadatas']):
                if metadata and 'source' in metadata and metadata['source'] == filename:
                    if i < len(collection['documents']):
                        content_parts.append(collection['documents'][i])
            
            # 按chunk_index排序
            content_parts_sorted = sorted(
                content_parts,
                key=lambda x: int(collection['metadatas'][collection['documents'].index(x)].get('chunk_index', 0))
            ) if content_parts else []
            
            return "\n\n".join(content_parts_sorted)
        except Exception as e:
            print(f"获取文档内容时出错: {e}")
            return ""
    
    def get_selected_documents_content(self, filenames: List[str]) -> str:
        '''获取多个选中文件的合并内容'''
        all_content = []
        for filename in filenames:
            content = self.get_document_content(filename)
            if content:
                all_content.append(f"=== 文件: {filename} ===\n{content}\n")
        
        return "\n".join(all_content)

