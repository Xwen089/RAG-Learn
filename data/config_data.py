from langchain_core.prompts import MessagesPlaceholder

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

# RAG提示词模板配置
rag_prompt_template = [
    ("system", "以我提供的已知参考资料为主体，回答用户的问题。如果用户的问题不在已知参考资料中，请直接回答“我不知道”。参考资料：{context}"),
    ("system", "并且我提供用户的对话历史记录，如下："),
    MessagesPlaceholder("history"),
    ("user", "请回答用户提问:{input}"),
]

# 系统欢迎消息
system_welcome_message = "您好！我是您的知识库助手，有什么问题我可以帮您解答吗？🤖"