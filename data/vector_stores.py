from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config

class VectorStoreService(object):
    def __init__(self, embedding, user_id: str = ""):
        self.embedding = embedding
        self.user_id = user_id
    
    def get_retriever(self, user_id: str = ""):
        uid = user_id or self.user_id
        from langchain_core.vectorstores import VectorStoreRetriever
        from mongodb_store import VectorStore
        vs = VectorStore(uid)
        k = config.similarity_search_k
        
        class MongoRetriever(VectorStoreRetriever):
            def __init__(self, vector_store, user_id, k, embedding_fn):
                super().__init__(vectorstore=vector_store, search_kwargs={"k": k})
                self._uid = user_id
                self._k = k
                self._embedding_fn = embedding_fn
            
            def _get_relevant_documents(self, query):
                query_embedding = self._embedding_fn.embed_query(query)
                results = vs.similarity_search(query_embedding, self._k)
                from langchain_core.documents import Document
                docs = []
                for r in results:
                    docs.append(Document(
                        page_content=r.get("text", ""),
                        metadata=r.get("metadata", {})
                    ))
                return docs
        
        return MongoRetriever(vs, uid, k, self.embedding)
