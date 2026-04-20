# RAG-Learn: 智能知识库学习系统

一个基于 LangChain、Streamlit 和 ChromaDB 的检索增强生成（RAG）系统，支持文档上传、智能问答和知识学习。系统采用模块化设计，提供完整的文档处理、向量检索、对话生成和主动学习功能。

## 🎯 功能特性

- 📄 **文档上传**：支持 PDF、TXT、DOCX、EXCEL、MARKDOWN 格式
- 🔍 **智能问答**：基于知识库的准确回答
- 🎓 **知识学习**：AI生成闪卡，问答学习，进度跟踪

## 📁 项目结构

```
RAG-KnowledgeBase/
├── data/                          # 核心代码目录
│   ├── app_main.py               # 统一入口
│   ├── app_file_uploader.py      # 文档上传界面
│   ├── app_qa.py                 # 问答界面
│   ├── app_learning.py           # 知识学习界面
│   ├── config_data.py            # 配置文件
│   ├── file_history_store.py     # 对话历史存储
│   ├── flashcard_service.py      # 闪卡生成服务
│   ├── knowledge_base.py         # 知识库管理服务
│   ├── rag.py                    # RAG 核心服务
│   └── vector_stores.py          # 向量存储服务
├── chroma_db/                    # ChromaDB 向量数据库
├── chat_history/                 # 对话历史存储
├── flashcards/                   # 闪卡学习数据
├── requirements.txt              # Python 依赖包
├── md5.text                      # 文档去重记录
└── README.md                     # 项目文档
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- API Key（这里使用的是阿里云通义千问）

### 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖包
pip install streamlit langchain langchain-community langchain-chroma dashscope pdfplumber python-docx openpyxl markdown
```

### 配置 API Key

1. 前往 [阿里云 DashScope](https://dashscope.aliyun.com/) 注册并获取 API Key
2. 设置环境变量：

```bash
# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Windows (CMD)
set DASHSCOPE_API_KEY=your-api-key-here

# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key-here"
```

3. 或者创建 `.env` 文件：
```bash
DASHSCOPE_API_KEY=your-api-key-here
```

### 运行应用

#### 1. 统一入口（推荐）
```bash
cd data
streamlit run app_main.py
```
启动完整系统，包含文档上传和问答功能


## ⚙️ 配置说明

### 核心配置文件：`data/config_data.py`

#### 模型配置
```python
embedding_model = "text-embedding-v4"  # 嵌入模型
chat_model = "qwen3-max"              # 对话模型
```

#### 向量存储配置
```python
collection_name = "rag"               # ChromaDB 集合名称
persist_directory = "./chroma_db"     # 向量数据库存储路径
```

#### 文本处理配置
```python
chunk_size = 1000                     # 文本块大小
chunk_overlap = 100                   # 块重叠大小
similarity_search_k = 1               # 检索返回文档数量
separators = ["\n\n","\n","\t","。",",","，",".","?","？","!","！"," "]  # 文本分割符
```

## 📖 使用指南

### 1. 文档上传
1. 进入"文件上传"页面
2. 选择文件（PDF、TXT、DOCX、EXCEL、MARKDOWN）
3. 系统自动解析、去重、分块、向量化存储

### 2. 智能问答
1. 进入"知识问答"页面
2. 输入问题
3. 系统基于知识库生成回答
4. 支持多轮对话和历史记录

### 3. 知识学习
1. **生成闪卡**：
   - 进入"知识学习"页面
   - 勾选要学习的文件
   - 设置闪卡数量（5-50张）
   - AI自动生成问答对

2. **学习模式**：
   - 问答学习：显示问题，点击查看答案
   - 掌握评估：标记掌握程度
   - 进度跟踪：自动记录学习数据

3. **数据管理**：
   - 查看所有学习集
   - 导出闪卡为CSV格式
   - 统计学习进度和掌握情况

## 🏗️ 系统架构

### 核心模块
- **RAG 服务** (`rag.py`)：检索和生成流程
- **知识库服务** (`knowledge_base.py`)：文档处理、分块、向量化
- **闪卡服务** (`flashcard_service.py`)：AI生成闪卡，学习进度管理
- **Web 界面** (`app_main.py`)：统一入口，集成所有功能
- **学习界面** (`app_learning.py`)：知识学习功能

### 数据流
```
文档上传 → 解析分块 → 向量存储 → ChromaDB
    ↓
智能问答 → 检索 → 生成 → 回答
    ↓
知识学习 → 生成闪卡 → 问答学习 → 进度跟踪
```

## 🛠️ 技术栈

- **前端框架**: Streamlit
- **LLM 框架**: LangChain
- **向量数据库**: ChromaDB
- **嵌入模型**: DashScope (text-embedding-v4)
- **对话模型**: 通义千问 (qwen3-max)
- **文档解析**: pdfplumber, python-docx, openpyxl

### 支持的文档格式
- PDF (.pdf)
- 纯文本 (.txt)
- Word 文档 (.docx)
- Excel 文件 (.xlsx, .xls)
- Markdown (.md)

## ⚠️ 注意事项

### 安全建议
- 确保上传文档不包含敏感信息
- 不要将 API 密钥提交到版本控制系统
- 定期备份 `chroma_db`、`chat_history`、`flashcards` 目录

## 🔧 故障排除

### 日志查看
- Streamlit 控制台显示详细日志
- Web 界面显示错误提示
- 添加 `--logger.level=debug` 参数获取详细日志

## 🙏 致谢
