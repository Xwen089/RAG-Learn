import importlib
import io
import time
import os
import zipfile
import tempfile
from pathlib import Path
import streamlit as st
from knowledge_base import KnowledgeBaseService

st.title("知识库更新服务")

tab1, tab2, tab3, tab4 = st.tabs(["单文件上传", "批量文件上传", "文件夹上传", "文件管理"])

with tab1:
    st.subheader("单文件上传")
    uploader_file = st.file_uploader(
        "选择单个文件", type=["pdf", "txt", "docx", "xlsx", "xls", "md", "markdown"]
    )

with tab2:
    st.subheader("批量文件上传")
    batch_files = st.file_uploader(
        "选择多个文件", 
        type=["pdf", "txt", "docx", "xlsx", "xls", "md", "markdown"],
        accept_multiple_files=True
    )

with tab3:
    st.subheader("文件夹上传")
    folder_upload = st.file_uploader(
        "上传ZIP压缩包（包含文件夹）",
        type=["zip"],
        accept_multiple_files=False
    )

with tab4:
    st.subheader("已上传文件管理")

if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService("")

def process_file(file, filename=None):
    if filename is None:
        filename = file.name
    
    if hasattr(file, 'getvalue'):
        file_size = len(file.getvalue())
    elif hasattr(file, 'read'):
        current_pos = file.tell()
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(current_pos)
    else:
        file_size = 0
    
    file_details = {
        "filename": filename,
        "filetype": file.type if hasattr(file, 'type') else 'unknown',
        "filesize": file_size
    }  

    st.write(f"**文件名：** {file_details['filename']}")
    st.write(f"**格式：** {file_details['filetype']}")
    st.write(f"**大小：** {file_details['filesize']} bytes")

    file_ext = file_details["filename"].lower().split(".")[-1]
    segments = []

    if file_ext == "pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file.getvalue())) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    segments.append({"text": page_text, "page": page_num})
        st.success(f"PDF 共提取到 {len(segments)} 页有效内容")

    elif file_ext == "txt":
        txt_content = file.getvalue().decode("utf-8", errors="ignore")
        if txt_content.strip():
            segments = [{"text": txt_content, "page": None}]
        st.success("TXT 内容提取完成")

    elif file_ext == "docx":
        try:
            docx_module = importlib.import_module("docx")
            Document = docx_module.Document
        except ImportError:
            st.error("缺少 python-docx 依赖，请先安装：pip install python-docx")
            return None

        doc = Document(io.BytesIO(file.getvalue()))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        if paragraphs:
            segments = [{"text": "\n".join(paragraphs), "page": None}]
        st.success(f"DOCX 共提取到 {len(paragraphs)} 个有效段落")

    elif file_ext in ["xlsx", "xls"]:
        try:
            import pandas as pd
        except ImportError:
            st.error("缺少 pandas 依赖，请先安装：pip install pandas")
            return None

        try:
            excel_data = pd.read_excel(io.BytesIO(file.getvalue()), sheet_name=None)
            all_sheets_text = []
            for sheet_name, df in excel_data.items():
                sheet_text = f"工作表: {sheet_name}\n"
                columns = " | ".join(df.columns.astype(str))
                sheet_text += f"列名: {columns}\n\n"
                for idx, row in df.iterrows():
                    row_values = " | ".join([str(val) for val in row.values])
                    sheet_text += f"行 {idx+1}: {row_values}\n"
                all_sheets_text.append(sheet_text)
            if all_sheets_text:
                segments = [{"text": "\n\n".join(all_sheets_text), "page": None}]
                st.success(f"Excel 共提取到 {len(excel_data)} 个工作表的内容")
            else:
                st.warning("Excel文件为空或无法读取")
        except Exception as e:
            st.error(f"读取Excel文件时出错: {str(e)}")
            return None

    elif file_ext in ["md", "markdown"]:
        md_content = file.getvalue().decode("utf-8", errors="ignore")
        if md_content.strip():
            segments = [{"text": md_content, "page": None}]
            st.success("Markdown 内容提取完成")
        else:
            st.warning("Markdown文件为空")

    else:
        st.error(f"暂不支持该文件类型: {file_ext}")
        return None

    if not segments:
        st.warning("未提取到有效文本内容，无法上传到知识库")
        return None

    return segments, file_details

def upload_segments(segments, file_details, user_id=""):
    with st.spinner("正在上传文件内容到知识库中..."):
        service = st.session_state["service"]
        for segment in segments:
            time.sleep(0.5)
            result = service.upload_by_str(
                segment["text"],
                file_details["filename"],
                page=segment["page"]
            )
            st.write(f"{file_details['filename']}: {result}")

with tab1:
    if uploader_file is not None:
        st.divider()
        result = process_file(uploader_file)
        if result:
            segments, file_details = result
            upload_segments(segments, file_details, st.session_state.get("user_id", ""))

with tab2:
    if batch_files and len(batch_files) > 0:
        st.divider()
        st.subheader(f"批量上传 {len(batch_files)} 个文件")
        
        progress_bar = st.progress(0)
        success_count = 0
        fail_count = 0
        
        for i, file in enumerate(batch_files):
            st.write(f"**处理文件 {i+1}/{len(batch_files)}:** {file.name}")
            result = process_file(file)
            if result:
                segments, file_details = result
                upload_segments(segments, file_details, st.session_state.get("user_id", ""))
                success_count += 1
            else:
                fail_count += 1
            progress_bar.progress((i + 1) / len(batch_files))
        
        st.success(f"批量上传完成！成功: {success_count} 个，失败: {fail_count} 个")

with tab3:
    if folder_upload is not None:
        st.divider()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(io.BytesIO(folder_upload.getvalue()), 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                supported_extensions = {'.pdf', '.txt', '.docx', '.xlsx', '.xls', '.md', '.markdown'}
                all_files = []
                
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in supported_extensions:
                            rel_path = file_path.relative_to(temp_dir)
                            all_files.append((file_path, str(rel_path)))
                
                if not all_files:
                    st.warning("ZIP文件中未找到支持的文件类型（pdf, txt, docx, xlsx, xls, md, markdown）")
                else:
                    st.subheader(f"在ZIP文件中找到 {len(all_files)} 个支持的文件")
                    
                    progress_bar = st.progress(0)
                    success_count = 0
                    fail_count = 0
                    
                    for i, (file_path, rel_path) in enumerate(all_files):
                        st.write(f"**处理文件 {i+1}/{len(all_files)}:** {rel_path}")
                        
                        try:
                            with open(file_path, 'rb') as f:
                                file_content = io.BytesIO(f.read())
                                file_content.name = rel_path
                                
                                result = process_file(file_content, filename=rel_path)
                                if result:
                                    segments, file_details = result
                                    upload_segments(segments, file_details, st.session_state.get("user_id", ""))
                                    success_count += 1
                                else:
                                    fail_count += 1
                        except Exception as e:
                            st.error(f"处理文件 {rel_path} 时出错: {str(e)}")
                            fail_count += 1
                        
                        progress_bar.progress((i + 1) / len(all_files))
                    
                    st.success(f"文件夹上传完成！成功: {success_count} 个，失败: {fail_count} 个")
                    
            except zipfile.BadZipFile:
                st.error("上传的文件不是有效的ZIP压缩包")
            except Exception as e:
                st.error(f"处理ZIP文件时出错: {str(e)}")

with tab4:
    if st.button("刷新文件列表", key="refresh_files"):
        st.rerun()
    
    files = st.session_state["service"].get_uploaded_files()
    
    if not files:
        st.info("知识库中暂无文件")
    else:
        st.write(f"共找到 {len(files)} 个文件")
        
        selected_files = []
        for file_info in files:
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                selected = st.checkbox("", key=f"select_{file_info['filename']}")
                if selected:
                    selected_files.append(file_info['filename'])
            with col2:
                st.write(f"**{file_info['filename']}**")
            with col3:
                st.write(f"分块数: {file_info['chunks']}")
                st.write(f"上传时间: {file_info['create_time']}")
            st.divider()
        
        if selected_files:
            st.warning(f"已选择 {len(selected_files)} 个文件进行删除")
            if st.button("删除选中文件", type="primary"):
                with st.spinner("正在删除文件..."):
                    deleted_count = st.session_state["service"].delete_files(selected_files)
                    if deleted_count > 0:
                        st.success(f"成功删除 {deleted_count} 个文件")
                        st.rerun()
                    else:
                        st.error("删除文件失败")
