md5_path = "./md5.text"

embedding_model = "text-embedding-v4"
chat_model = "qwen3-max"

#chroma数据库配置
collection_name = "rag" #数据库表名
persist_directory = "./chroma_db" #数据库本地存储文件夹

#spliter文本分块配置
chunk_size = 1000 #分割后的文本段最大长度
chunk_overlap = 100 #连续文本段之间的字符重叠数量
separators = ["\n\n","\n","\t","。",",","，",".","?","？","!","！"," "] 
max_split_char_number = 1000 #文本分割的阈值

#检索返回匹配文档数量
similarity_search_k = 1

session_config = {
    "configurable":{
        "session_id":"user_001",
    }
}