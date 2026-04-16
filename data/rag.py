from streamlit import context
from vector_stores import VectorStoreService
from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models import ChatTongyi
from langchain_core.runnables import RunnablePassthrough,RunnableWithMessageHistory
from langchain_core.documents import Document
from file_history_store import get_history
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser


class RAGService(object):
    def __init__(self):

        self.vector_store = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model)
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system","以我提供的已知参考资料为主体，回答用户的问题。如果用户的问题不在已知参考资料中，请直接回答“我不知道”。参考资料：{context}"),
                ("system","并且我提供用户的对话历史记录，如下："),
                MessagesPlaceholder("history"),
                ("user", "请回答用户提问:{input}"),
            ]
        )

        self.chat_model = ChatTongyi(model=config.chat_model)

        self.chain = self.__get_chain()

    def __get_chain(self):
        """获取RAG链"""
        retriever = self.vector_store.get_retriever()

        def fromat_document(docs:list[Document]):
            if not docs:
                return "无相关参考资料"

            formatted_str = ""
            for doc in docs:
                formatted_str += f"文档内容: {doc.page_content}\n文档元数据：{doc.metadata}\n\n"
            
            return formatted_str

        def format_for_retriever(value:dict) -> str:
            return value["input"]
        
        def format_for_prompt(value):
            #{input,context,history}
            new_value = {}
            new_value["input"] = value["input"]["input"]
            new_value["context"] = value["context"]
            new_value["history"] = value["input"]["history"]
            return new_value

        chain = (
            {
                "input": RunnablePassthrough(),
                "context":RunnableLambda(format_for_retriever) | retriever | fromat_document
            }| RunnableLambda(format_for_prompt) | self.prompt_template | self.chat_model | StrOutputParser()
        )

        conversational_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history"
        )

        return conversational_chain

if __name__ == "__main__":
    session_config = config.session_config
    result = RAGService().chain.invoke({"input":"什么是深度学习？"},session_config)
    print(result)