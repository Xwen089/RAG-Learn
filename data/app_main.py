import streamlit as st
import sys
import os
import uuid
from datetime import datetime
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_file_uploader import process_file, upload_segments
from knowledge_base import KnowledgeBaseService
from rag import RAGService
from supabase_store import UserService, SessionStore, MessageStore, init_db
import config_data as config

st.set_page_config(page_title="RAG知识库系统", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E3A8A; text-align: center; margin-bottom: 1rem; }
    .card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1rem; }
    .file-card { background: white; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #3B82F6; }
    .session-card { 
        background: white; 
        border-radius: 8px; 
        padding: 0.75rem; 
        margin-bottom: 0.5rem; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .session-card:hover { 
        background: #F3F4F6; 
        transform: translateX(2px);
    }
    .session-card.active { 
        background: #E0E7FF; 
        border-left: 4px solid #3B82F6;
    }
    .session-name { 
        font-weight: 600; 
        color: #1F2937; 
        margin-bottom: 0.25rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .session-preview { 
        font-size: 0.85rem; 
        color: #6B7280; 
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .session-info { 
        font-size: 0.75rem; 
        color: #9CA3AF; 
        display: flex;
        justify-content: space-between;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

def render_login():
    st.markdown('<h1 class="main-header">📚 RAG知识库系统</h1>', unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 用户登录")
        tab_login, tab_register = st.tabs(["登录", "注册"])
        
        with tab_login:
            username = st.text_input("用户名", key="login_user")
            password = st.text_input("密码", type="password", key="login_pwd")
            if st.button("登录", type="primary", use_container_width=True):
                result = UserService.login(username, password)
                if result["ok"]:
                    st.session_state["user_id"] = result["user_id"]
                    st.session_state["user_logged_in"] = True
                    st.rerun()
                else:
                    st.error(result["msg"])
        
        with tab_register:
            new_user = st.text_input("用户名", key="reg_user")
            new_pwd = st.text_input("密码", type="password", key="reg_pwd")
            if st.button("注册", type="primary", use_container_width=True):
                result = UserService.register(new_user, new_pwd)
                if result["ok"]:
                    st.success(result["msg"])
                else:
                    st.error(result["msg"])

def init_session():
    user_id = st.session_state["user_id"]
    
    if "service" not in st.session_state:
        st.session_state.service = KnowledgeBaseService(user_id)
    if "rag" not in st.session_state:
        st.session_state.rag = RAGService(user_id)
    
    if "sessions" not in st.session_state:
        st.session_state.sessions = SessionStore.get_all(user_id)
    
    if "current_session_id" not in st.session_state or st.session_state.current_session_id not in st.session_state.sessions:
        if st.session_state.sessions:
            latest_session = max(
                st.session_state.sessions.values(), 
                key=lambda x: x.get("updated_at", x.get("created_at", ""))
            )
            st.session_state.current_session_id = latest_session["id"]
        else:
            session_data = SessionStore.create(user_id, "新会话 1")
            st.session_state.sessions[session_data["id"]] = session_data
            st.session_state.current_session_id = session_data["id"]
    
    session_key = f"messages_{st.session_state.current_session_id}"
    if session_key not in st.session_state:
        messages = MessageStore.get_messages(st.session_state.current_session_id)
        if messages:
            st.session_state[session_key] = messages
        else:
            st.session_state[session_key] = [{"role": "assistant", "content": config.system_welcome_message}]

def create_new_session():
    user_id = st.session_state["user_id"]
    session_num = len(st.session_state.sessions) + 1
    session_data = SessionStore.create(user_id, f"新会话 {session_num}")
    session_id = session_data["id"]
    st.session_state.sessions[session_id] = session_data
    st.session_state.current_session_id = session_id
    session_key = f"messages_{session_id}"
    st.session_state[session_key] = [{"role": "assistant", "content": config.system_welcome_message}]

def switch_session(session_id):
    st.session_state.current_session_id = session_id
    session_key = f"messages_{session_id}"
    if session_key not in st.session_state:
        messages = MessageStore.get_messages(session_id)
        if messages:
            st.session_state[session_key] = messages
        else:
            st.session_state[session_key] = [{"role": "assistant", "content": config.system_welcome_message}]

def rename_session(session_id, new_name):
    if session_id in st.session_state.sessions:
        st.session_state.sessions[session_id]["name"] = new_name
        SessionStore.update(session_id, st.session_state["user_id"], {"name": new_name})

def delete_session(session_id):
    user_id = st.session_state["user_id"]
    if session_id in st.session_state.sessions:
        if session_id == st.session_state.current_session_id:
            other_sessions = [sid for sid in st.session_state.sessions.keys() if sid != session_id]
            if other_sessions:
                st.session_state.current_session_id = other_sessions[0]
            else:
                create_new_session()
        
        success = SessionStore.delete(session_id, user_id)
        if success:
            del st.session_state.sessions[session_id]
            session_key = f"messages_{session_id}"
            if session_key in st.session_state:
                del st.session_state[session_key]
        return success
    return False

def get_current_messages():
    session_key = f"messages_{st.session_state.current_session_id}"
    return st.session_state.get(session_key, [])

def update_current_messages(messages):
    session_key = f"messages_{st.session_state.current_session_id}"
    st.session_state[session_key] = messages
    
    if messages and len(messages) > 1:
        last_msg = messages[-1]
        preview = last_msg["content"][:50] + ("..." if len(last_msg["content"]) > 50 else "")
        
        updates = {
            "last_message": preview,
            "message_count": len(messages) - 1
        }
        
        st.session_state.sessions[st.session_state.current_session_id].update(updates)
        SessionStore.update(
            st.session_state.current_session_id,
            st.session_state["user_id"],
            updates
        )

def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📚 RAG知识库系统")
        st.markdown(f"**👤 用户:** {st.session_state['user_id']}")
        st.markdown("---")
        
        pages = {
            "💬 知识问答": "chat",
            "📤 文件上传": "upload", 
            "📁 文件管理": "manage",
            "🎓 知识学习": "learning"
        }
        
        page = st.radio("选择功能", list(pages.keys()), label_visibility="collapsed")
        st.markdown("---")
        
        files = st.session_state.service.get_uploaded_files()
        st.info(f"📄 已上传文件: **{len(files)}** 个")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("🚪 退出登录", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💭 会话列表")
        
        if st.button("➕ 新建会话", use_container_width=True):
            create_new_session()
            st.rerun()
        
        st.markdown("---")
        
        search_term = st.text_input("🔍 搜索会话", placeholder="输入会话名称搜索...", key="session_search")
        
        sessions = st.session_state.sessions
        current_id = st.session_state.current_session_id
        
        filtered_sessions = {}
        for session_id, session_info in sessions.items():
            if not search_term or search_term.lower() in session_info["name"].lower():
                filtered_sessions[session_id] = session_info
        
        if not filtered_sessions:
            st.info("🔍 未找到匹配的会话")
        else:
            for session_id, session_info in filtered_sessions.items():
                is_active = session_id == current_id
                
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        if st.session_state.get(f"editing_{session_id}", False):
                            new_name = st.text_input(
                                "新名称",
                                value=session_info["name"],
                                key=f"rename_{session_id}",
                                label_visibility="collapsed"
                            )
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("✅", key=f"save_{session_id}", help="保存"):
                                    rename_session(session_id, new_name)
                                    st.session_state[f"editing_{session_id}"] = False
                                    st.rerun()
                            with col_btn2:
                                if st.button("❌", key=f"cancel_{session_id}", help="取消"):
                                    st.session_state[f"editing_{session_id}"] = False
                                    st.rerun()
                        else:
                            st.markdown(f'<div class="session-name">💬 {session_info["name"]}</div>', unsafe_allow_html=True)
                            if session_info["last_message"]:
                                st.markdown(f'<div class="session-preview">{session_info["last_message"]}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div class="session-preview">暂无对话</div>', unsafe_allow_html=True)
                            
                            st.markdown(f'''
                            <div class="session-info">
                                <span>📅 {session_info["created_at"]}</span>
                                <span>💬 {session_info["message_count"]}条</span>
                            </div>
                            ''', unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("➡️", key=f"switch_{session_id}", help="切换到该会话"):
                            switch_session(session_id)
                            st.rerun()
                    
                    with col3:
                        with st.popover("⋯", help="更多操作"):
                            if st.button("✏️ 重命名", key=f"rename_btn_{session_id}"):
                                st.session_state[f"editing_{session_id}"] = True
                                st.rerun()
                            
                            if st.button("🗑️ 删除", key=f"delete_btn_{session_id}"):
                                st.session_state[f"confirm_delete_{session_id}"] = True
                                st.rerun()
                
                if st.session_state.get(f"confirm_delete_{session_id}", False):
                    st.warning(f"确定要删除会话 '{session_info['name']}' 吗？")
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button("✅ 确认删除", key=f"confirm_yes_{session_id}"):
                            delete_session(session_id)
                            st.rerun()
                    with col_confirm2:
                        if st.button("❌ 取消", key=f"confirm_no_{session_id}"):
                            st.session_state[f"confirm_delete_{session_id}"] = False
                            st.rerun()
                
                st.markdown("---")
    
    return pages[page]

def render_chat():
    current_session = st.session_state.sessions[st.session_state.current_session_id]
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        st.markdown(f'<h1 class="main-header">💬 {current_session["name"]}</h1>', unsafe_allow_html=True)
    
    messages = get_current_messages()
    
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("请输入您的问题..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        
        messages.append({"role": "user", "content": prompt})
        
        user_message = {"role": "user", "content": prompt}
        MessageStore.add_messages(st.session_state.current_session_id, st.session_state["user_id"], [user_message])
        
        with st.chat_message("assistant"):
            with st.spinner("🤔 正在思考..."):
                ai_res = []
                stream = st.session_state.rag.chain.stream(
                    {"input": prompt}, 
                    {"configurable": {"session_id": st.session_state.current_session_id}}
                )
                
                def capture(gen, cache):
                    for chunk in gen:
                        cache.append(chunk)
                        yield chunk
                
                st.write_stream(capture(stream, ai_res))
                full_response = "".join(ai_res)
                messages.append({"role": "assistant", "content": full_response})
                
                assistant_message = {"role": "assistant", "content": full_response}
                MessageStore.add_messages(st.session_state.current_session_id, st.session_state["user_id"], [assistant_message])
        
        update_current_messages(messages)
    
    if len(messages) > 1:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🗑️ 清空当前会话", type="secondary"):
                session_key = f"messages_{st.session_state.current_session_id}"
                MessageStore.clear(st.session_state.current_session_id)
                st.session_state[session_key] = [{"role": "assistant", "content": config.system_welcome_message}]
                
                st.session_state.sessions[st.session_state.current_session_id].update({
                    "last_message": "",
                    "message_count": 0
                })
                st.rerun()

def render_upload():
    st.markdown('<h1 class="main-header">📤 文件上传中心</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📄 单文件上传", "📦 批量文件上传", "📁 文件夹上传"])
    
    with tab1:
        st.markdown("### 📄 单文件上传")
        if file := st.file_uploader("选择文件", type=["pdf", "txt", "docx", "xlsx", "xls", "md", "markdown"], label_visibility="collapsed"):
            with st.spinner("🔍 正在分析文件..."):
                if result := process_file(file):
                    segments, file_details = result
                    upload_segments(segments, file_details, st.session_state["user_id"])
    
    with tab2:
        st.markdown("### 📦 批量文件上传")
        if files := st.file_uploader("选择多个文件", type=["pdf", "txt", "docx", "xlsx", "xls", "md", "markdown"], accept_multiple_files=True, label_visibility="collapsed"):
            st.markdown(f'<div class="card">📦 批量上传 <strong>{len(files)}</strong> 个文件</div>', unsafe_allow_html=True)
            progress = st.progress(0)
            success = 0
            
            for i, file in enumerate(files):
                with st.expander(f"📄 {file.name}", expanded=False):
                    if result := process_file(file):
                        segments, file_details = result
                        upload_segments(segments, file_details, st.session_state["user_id"])
                        success += 1
                progress.progress((i + 1) / len(files))
            
            if success:
                st.success(f"✅ 批量上传完成！成功: {success} 个文件")
    
    with tab3:
        st.markdown("### 📁 文件夹上传")
        if zip_file := st.file_uploader("上传ZIP文件", type=["zip"], label_visibility="collapsed"):
            import io, zipfile, tempfile
            from pathlib import Path
            
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    with zipfile.ZipFile(io.BytesIO(zip_file.getvalue()), 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    exts = {'.pdf', '.txt', '.docx', '.xlsx', '.xls', '.md', '.markdown'}
                    all_files = [(Path(root)/file, str((Path(root)/file).relative_to(temp_dir))) 
                                for root, _, files in os.walk(temp_dir) for file in files 
                                if (Path(root)/file).suffix.lower() in exts]
                    
                    if not all_files:
                        st.warning("⚠️ ZIP文件中未找到支持的文件格式")
                    else:
                        st.markdown(f'<div class="card">📁 找到 <strong>{len(all_files)}</strong> 个文件</div>', unsafe_allow_html=True)
                        progress = st.progress(0)
                        success = 0
                        
                        for i, (file_path, rel_path) in enumerate(all_files):
                            with st.expander(f"📄 {rel_path}", expanded=False):
                                try:
                                    with open(file_path, 'rb') as f:
                                        file_content = io.BytesIO(f.read())
                                        file_content.name = rel_path
                                        if result := process_file(file_content, filename=rel_path):
                                            segments, file_details = result
                                            upload_segments(segments, file_details, st.session_state["user_id"])
                                            success += 1
                                except Exception as e:
                                    st.error(f"❌ 处理文件出错: {str(e)}")
                            progress.progress((i + 1) / len(all_files))
                        
                        if success:
                            st.success(f"✅ 文件夹上传完成！成功: {success} 个文件")
                
                except zipfile.BadZipFile:
                    st.error("❌ 无效的ZIP文件")
                except Exception as e:
                    st.error(f"❌ 处理ZIP文件时出错: {str(e)}")

def render_manage():
    st.markdown('<h1 class="main-header">📁 文件管理中心</h1>', unsafe_allow_html=True)
    
    if st.button("🔄 刷新文件列表"):
        st.rerun()
    
    files = st.session_state.service.get_uploaded_files()
    
    if not files:
        st.info("📭 知识库为空，请先上传文件")
    else:
        total_chunks = sum(f['chunks'] for f in files)
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; color: white;">📊 文件统计</h4>
                    <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.9);">
                        共 <strong>{len(files)}</strong> 个文件，<strong>{total_chunks}</strong> 个文本块
                    </p>
                </div>
                <div style="font-size: 2rem;">📚</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        selected = []
        for file_info in files:
            st.markdown(f"""
            <div class="file-card">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="flex: 0 0 auto;">
                        {st.checkbox("", key=f"select_{file_info['filename']}", label_visibility="collapsed")}
                    </div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin: 0; color: #1F2937;">📄 {file_info['filename']}</h4>
                                <p style="margin: 0.25rem 0 0 0; color: #6B7280; font-size: 0.9rem;">
                                    📅 上传时间: {file_info['create_time']}
                                </p>
                            </div>
                            <div style="background: #3B82F6; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-weight: 600;">
                                🔢 {file_info['chunks']} 块
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.get(f"select_{file_info['filename']}", False):
                selected.append(file_info['filename'])
        
        if selected:
            st.warning(f"⚠️ 已选择 {len(selected)} 个文件")
            if st.button("🗑️ 删除选中文件", type="primary"):
                with st.spinner("🗑️ 正在删除文件..."):
                    if deleted := st.session_state.service.delete_files(selected):
                        st.success(f"✅ 成功删除 {deleted} 个文件")
                        st.rerun()
                    else:
                        st.error("❌ 删除文件失败")

def main():
    init_db()
    if "user_logged_in" not in st.session_state:
        render_login()
        return
    
    init_session()
    page = render_sidebar()
    
    if page == "chat":
        render_chat()
    elif page == "upload":
        render_upload()
    elif page == "manage":
        render_manage()
    elif page == "learning":
        from app_learning import render_learning
        render_learning()

if __name__ == "__main__":
    main()
