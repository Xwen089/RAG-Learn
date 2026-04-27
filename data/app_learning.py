import streamlit as st
import json
import os
from datetime import datetime
from flashcard_service import FlashcardService

def render_learning():
    st.markdown('<h1 class="main-header">🎓 知识学习中心</h1>', unsafe_allow_html=True)
    
    if "flashcard_service" not in st.session_state:
        st.session_state.flashcard_service = FlashcardService()
    
    tab1, tab2, tab3 = st.tabs(["📝 生成闪卡", "📚 学习模式", "📊 学习记录"])
    
    with tab1:
        render_generate_flashcards()
    
    with tab2:
        render_learning_mode()
    
    with tab3:
        render_learning_records()

def render_generate_flashcards():
    st.markdown("### 📝 生成学习闪卡")
    st.markdown("选择知识库中的文件，AI将根据内容生成问答闪卡")
    
    files = st.session_state.service.get_uploaded_files()
    
    if not files:
        st.info("📭 知识库为空，请先上传文件")
        return
    
    st.markdown("#### 📁 选择学习文件")
    selected_files = []
    
    for file_info in files:
        col1, col2 = st.columns([1, 4])
        with col1:
            selected = st.checkbox("", key=f"learn_select_{file_info['filename']}", label_visibility="collapsed")
        with col2:
            st.markdown(f"**📄 {file_info['filename']}** - {file_info['chunks']}个文本块")
        
        if selected:
            selected_files.append(file_info['filename'])
    
    if not selected_files:
        st.warning("请至少选择一个文件")
        return
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        num_cards = st.slider("闪卡数量", min_value=5, max_value=50, value=15, step=5)
    with col2:
        difficulty = st.selectbox("难度偏好", ["自动", "简单", "中等", "困难"])
    
    if st.button("🚀 生成闪卡", type="primary", use_container_width=True):
        with st.spinner("🤖 AI正在生成闪卡..."):
            document_content = st.session_state.service.get_selected_documents_content(selected_files)
            
            if not document_content:
                st.error("无法获取文档内容")
                return
            
            flashcards = st.session_state.flashcard_service.generate_flashcards(
                document_content=document_content,
                num_cards=num_cards
            )
            
            if not flashcards:
                st.error("生成闪卡失败")
                return
            
            for card in flashcards:
                card["source_files"] = selected_files
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"学习集_{timestamp}_{len(selected_files)}个文件.json"
            st.session_state.flashcard_service.save_flashcards(flashcards, filename)
            
            st.success(f"✅ 成功生成 {len(flashcards)} 张闪卡")
            
            st.markdown("#### 📋 闪卡预览")
            for i, card in enumerate(flashcards[:3]):
                with st.expander(f"闪卡 #{i+1}: {card['question'][:50]}..."):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**问题:** {card['question']}")
                        st.markdown(f"**答案:** {card['answer']}")
                    with col2:
                        st.markdown(f"**难度:** {card['difficulty']}")
            
            if len(flashcards) > 3:
                st.info(f"还有 {len(flashcards) - 3} 张闪卡未显示")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📚 开始学习", key="start_learn_new"):
                    st.session_state.current_flashcard_set = filename
                    st.session_state.current_card_index = 0
                    st.rerun()
            with col2:
                st.success(f"闪卡已保存")
            with col3:
                csv_path = st.session_state.flashcard_service.export_to_csv(filename)
                if csv_path:
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            label="📥 导出CSV",
                            data=f,
                            file_name=os.path.basename(csv_path),
                            mime="text/csv"
                        )

def render_learning_mode():
    st.markdown("### 📚 闪卡学习模式")
    
    flashcard_sets = st.session_state.flashcard_service.get_all_flashcard_sets()
    
    if not flashcard_sets:
        st.info("📭 还没有闪卡学习集，请先生成闪卡")
        return
    
    set_names = [s["filename"] for s in flashcard_sets]
    selected_name = st.selectbox(
        "选择闪卡学习集",
        options=set_names,
        format_func=lambda x: f"{x} ({next(s['card_count'] for s in flashcard_sets if s['filename']==x)}张卡)",
        key="flashcard_set_select"
    )
    
    if not selected_name:
        return
    
    flashcards = st.session_state.flashcard_service.load_flashcards(selected_name)
    
    if not flashcards:
        st.error("加载闪卡失败")
        return
    
    if "current_flashcard_set" not in st.session_state:
        st.session_state.current_flashcard_set = selected_name
    if "current_card_index" not in st.session_state:
        st.session_state.current_card_index = 0
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    
    if st.session_state.current_flashcard_set != selected_name:
        st.session_state.current_flashcard_set = selected_name
        st.session_state.current_card_index = 0
        st.session_state.show_answer = False
    
    current_index = st.session_state.current_card_index
    current_card = flashcards[current_index] if current_index < len(flashcards) else None
    
    if not current_card:
        st.error("闪卡数据错误")
        return
    
    total_cards = len(flashcards)
    mastered = sum(1 for card in flashcards if card.get("mastery_level", 0) >= 2)
    reviewed = sum(1 for card in flashcards if card.get("review_count", 0) > 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总闪卡数", total_cards)
    with col2:
        st.metric("当前进度", f"{current_index + 1}/{total_cards}")
    with col3:
        st.metric("已掌握", mastered)
    with col4:
        st.metric("已复习", reviewed)
    
    st.markdown("---")
    st.markdown(f"### 闪卡 #{current_index + 1}")
    
    difficulty_colors = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
    difficulty_icon = difficulty_colors.get(current_card.get("difficulty", "medium"), "🟡")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**难度:** {difficulty_icon} {current_card.get('difficulty', 'medium').upper()}")
    with col2:
        mastery_level = current_card.get("mastery_level", 0)
        mastery_text = ["未学习", "基本掌握", "熟练掌握"][mastery_level] if mastery_level < 3 else "已掌握"
        st.markdown(f"**掌握程度:** {mastery_text}")
    
    st.markdown("---")
    st.markdown(f"#### ❓ 问题")
    st.markdown(f"**{current_card['question']}**")
    
    if not st.session_state.show_answer:
        if st.button("👁️ 显示答案", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()
    else:
        st.markdown("---")
        st.markdown(f"#### ✅ 答案")
        st.markdown(f"{current_card['answer']}")
        
        st.markdown("---")
        st.markdown("#### 📊 掌握程度评估")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🤔 仍需复习", use_container_width=True, type="secondary"):
                st.session_state.flashcard_service.update_flashcard_progress(
                    current_card["id"], 0, st.session_state.current_flashcard_set
                )
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            if st.button("😊 基本掌握", use_container_width=True, type="primary"):
                st.session_state.flashcard_service.update_flashcard_progress(
                    current_card["id"], 1, st.session_state.current_flashcard_set
                )
                st.session_state.show_answer = False
                st.rerun()
        with col3:
            if st.button("🎯 熟练掌握", use_container_width=True, type="primary"):
                st.session_state.flashcard_service.update_flashcard_progress(
                    current_card["id"], 2, st.session_state.current_flashcard_set
                )
                st.session_state.show_answer = False
                st.rerun()
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("⏮️ 上一张", disabled=current_index == 0):
            st.session_state.current_card_index = max(0, current_index - 1)
            st.session_state.show_answer = False
            st.rerun()
    with col2:
        if st.button("随机一张"):
            import random
            st.session_state.current_card_index = random.randint(0, total_cards - 1)
            st.session_state.show_answer = False
            st.rerun()
    with col3:
        if st.button("下一张 ⏭️"):
            st.session_state.current_card_index = min(total_cards - 1, current_index + 1)
            st.session_state.show_answer = False
            st.rerun()
    with col4:
        if st.button("🔄 重置进度"):
            st.session_state.current_card_index = 0
            st.session_state.show_answer = False
            st.rerun()

def render_learning_records():
    st.markdown("### 📊 学习记录与统计")
    
    flashcard_sets = st.session_state.flashcard_service.get_all_flashcard_sets()
    
    if not flashcard_sets:
        st.info("📭 还没有学习记录")
        return
    
    total_sets = len(flashcard_sets)
    total_cards = sum(s["card_count"] for s in flashcard_sets)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("学习集数量", total_sets)
    with col2:
        st.metric("总闪卡数", total_cards)
    
    st.markdown("---")
    st.markdown("#### 📚 我的学习集")
    
    for set_info in flashcard_sets:
        with st.expander(f"{set_info['filename']} ({set_info['card_count']}张卡)"):
            stats = st.session_state.flashcard_service.get_set_stats(set_info["filename"])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总卡数", stats["total"])
            with col2:
                st.metric("已掌握", stats["mastered"])
            with col3:
                st.metric("已复习", stats["reviewed"])
            with col4:
                st.metric("平均掌握", f"{stats['avg_mastery']}/2.0")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📚 学习", key=f"learn_{set_info['filename']}"):
                    st.session_state.current_flashcard_set = set_info["filename"]
                    st.session_state.current_card_index = 0
                    st.session_state.show_answer = False
                    st.rerun()
            with col2:
                csv_path = st.session_state.flashcard_service.export_to_csv(set_info["filename"])
                if csv_path:
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            label="📥 导出CSV",
                            data=f,
                            file_name=os.path.basename(csv_path),
                            mime="text/csv",
                            key=f"export_{set_info['filename']}"
                        )
            with col3:
                if st.button("🗑️ 删除", key=f"delete_{set_info['filename']}", type="secondary"):
                    st.session_state.flashcard_service.delete_set(set_info["filename"])
                    st.success("删除成功")
                    st.rerun()
