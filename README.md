# RAG 知识问答系统

一个基于 LangChain、Streamlit 和 ChromaDB 的检索增强生成（RAG）系统，支持文档上传、向量化存储和智能问答。

## 功能特性

- 📄 **多格式文档支持**：支持 PDF、TXT、DOCX、EXCEL、MARKDOWN格式文档上传
- 🔍 **智能检索**：基于向量相似度的文档检索
- 💬 **对话记忆**：支持多轮对话历史记录
- 🧠 **知识库管理**：自动去重、分块存储文档内容
- 🌐 **Web界面**：基于 Streamlit 的友好用户界面
- 🔧 **可配置**：支持多种参数配置和模型选择

## 系统架构

```
├── data/
│   ├── app_file_uploader.py    # 文档上传 Web 界面
│   ├── app_qa.py              # 问答 Web 界面
│   ├── config_data.py         # 配置文件
│   ├── file_history_store.py  # 对话历史存储
│   ├── knowledge_base.py      # 知识库管理服务
│   ├── rag.py                 # RAG 核心服务
│   └── vector_stores.py       # 向量存储服务
├── chroma_db/                 # ChromaDB 向量数据库
├── chat_history/              # 对话历史存储
├── md5.text                   # 文档去重记录
└── README.md
```

## 快速开始

### 环境要求

- Python 3.8+
- DashScope API Key（阿里云通义千问）

### 安装依赖

```bash
# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖包
pip install streamlit langchain langchain-community langchain-chroma dashscope pdfplumber python-docx
```

### 配置 API Key

1. 前往 [阿里云 DashScope](https://dashscope.aliyun.com/) 获取 API Key
2. 设置环境变量：
```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 运行应用

#### 1. 文档上传服务
```bash
cd data
streamlit run app_file_uploader.py
```
上传文档到知识库

#### 2. 问答服务
```bash
cd data
streamlit run app_qa.py
```
进行智能问答

## 配置说明

在 `data/config_data.py` 中可以修改以下配置：

- **模型配置**：
  - `embedding_model`: 嵌入模型（默认：text-embedding-v4）
  - `chat_model`: 对话模型（默认：qwen3-max）

- **向量存储配置**：
  - `collection_name`: ChromaDB 集合名称
  - `persist_directory`: 向量数据库存储路径

- **文本分块配置**：
  - `chunk_size`: 文本块大小（默认：1000）
  - `chunk_overlap`: 块重叠大小（默认：100）
  - `similarity_search_k`: 检索返回文档数量（默认：1）

## 使用示例

### 1. 上传文档
1. 启动文档上传服务
2. 选择 PDF/TXT/DOCX 文件上传
3. 系统自动提取文本、分块并向量化存储

### 2. 智能问答
1. 启动问答服务
2. 在输入框中提问
3. 系统基于知识库内容生成回答

### 3. 对话历史
- 系统自动保存对话历史
- 支持多轮上下文理解
- 历史记录存储在 `chat_history/` 目录

## 核心组件

### RAGService (`rag.py`)
- 集成检索和生成流程
- 支持对话历史管理
- 可配置的提示模板

### KnowledgeBaseService (`knowledge_base.py`)
- 文档处理与分块
- MD5 去重检查
- ChromaDB 向量化存储

### VectorStoreService (`vector_stores.py`)
- 向量检索器封装
- 相似度搜索配置

### FileChatMessageHistory (`file_history_store.py`)
- 基于文件的对话历史存储
- JSON 格式持久化

## 技术栈

- **前端框架**: Streamlit
- **LLM 框架**: LangChain
- **向量数据库**: ChromaDB
- **嵌入模型**: DashScope Embeddings
- **对话模型**: 通义千问 (ChatTongyi)
- **文档解析**: pdfplumber, python-docx

## 注意事项

1. **API 限制**: 注意 DashScope API 的调用频率和配额限制
2. **文档大小**: 大文档可能需要较长的处理时间
3. **存储空间**: 向量数据库会占用磁盘空间
4. **隐私安全**: 确保上传的文档不包含敏感信息

## 故障排除

### 常见问题

1. **API Key 错误**
   - 检查环境变量设置
   - 确认 API Key 有效

2. **依赖安装失败**
   - 使用 Python 3.8+ 版本
   - 尝试使用国内镜像源

3. **文档解析失败**
   - 检查文档格式是否支持
   - 确保安装了正确的解析库

### 日志查看
- Streamlit 会在控制台输出运行日志
- 错误信息会显示在 Web 界面

## 开发计划

- [ ] 添加用户认证系统

 

## 许可证

MIT License