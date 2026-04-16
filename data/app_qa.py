import streamlit as st
from streamlit import config
from rag import RAGService
import config_data as config
#标题
st.title("深度学习知识检索")
st.divider()

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "您好！有什么关于深度学习的问题我可以帮您解答吗？"}]

if "rag" not in st.session_state:
    st.session_state["rag"] = RAGService()

for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

#在页面最下方提供用户输入栏
prompt = st.chat_input()

if prompt:

    #在页面上展示用户输入的内容
    st.chat_message("user").write(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    ai_res_list = []
    with st.spinner("正在处理您的问题..."):
        #展示模型的回答
        res_stream = st.session_state["rag"].chain.stream({"input":prompt},config.session_config)
        
        def capture(generator,cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                yield chunk

        st.chat_message("assistant").write_stream(capture(res_stream,ai_res_list))
        st.session_state["messages"].append({"role":"assitant","content":"".join(ai_res_list)})