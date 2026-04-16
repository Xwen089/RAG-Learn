#基于Stramlit完成web网页上传服务

import importlib
import io
import time
import streamlit as st
from knowledge_base import KnowledgeBaseService
#添加网页标题
st.title("知识库更新服务")

# file_uploader组件，允许用户上传文件
uploader_file = st.file_uploader(
    "上传文件", type=["pdf", "txt", "docx"]
)

#创建知识库服务实例对象
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()


if uploader_file is not None:
    #提取文件信息
    file_details = {
        "filename": uploader_file.name,
        "filetype": uploader_file.type,
        "filesize": uploader_file.size
    }  

    st.subheader(f"文件名：{file_details['filename']}")
    st.write(f"格式：{file_details['filetype']}")
    st.write(f"大小：{file_details['filesize']} bytes")

    # 按文件类型提取文本，统一组织为 segments 进行上传（每段包含 text/page）
    file_ext = file_details["filename"].lower().split(".")[-1]
    segments = []

    if file_ext == "pdf":
        import pdfplumber

        with pdfplumber.open(io.BytesIO(uploader_file.getvalue())) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    segments.append({"text": page_text, "page": page_num})
        st.success(f"PDF 共提取到 {len(segments)} 页有效内容")

    elif file_ext == "txt":
        txt_content = uploader_file.getvalue().decode("utf-8", errors="ignore")
        if txt_content.strip():
            segments = [{"text": txt_content, "page": None}]
        st.success("TXT 内容提取完成")

    elif file_ext == "docx":
        try:
            docx_module = importlib.import_module("docx")
            Document = docx_module.Document
        except ImportError:
            st.error("缺少 python-docx 依赖，请先安装：pip install python-docx")
            st.stop()

        doc = Document(io.BytesIO(uploader_file.getvalue()))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        if paragraphs:
            segments = [{"text": "\n".join(paragraphs), "page": None}]
        st.success(f"DOCX 共提取到 {len(paragraphs)} 个有效段落")

    else:
        st.error("暂不支持该文件类型")
        st.stop()

    if not segments:
        st.warning("未提取到有效文本内容，无法上传到知识库")
        st.stop()

    # 将文本上传到向量数据库中
    with st.spinner("正在上传文件内容到知识库中..."):
        for segment in segments:
            time.sleep(1)
            result = st.session_state["service"].upload_by_str(
                segment["text"],
                file_details["filename"],
                page=segment["page"]
            )
            st.write(result)
