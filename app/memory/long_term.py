import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.utils.logger import logger


class LongTermMemory:
    def __init__(self):
        from app.config import settings
        # Pass API key explicitly so LangChain can read it regardless of
        # whether it was set before or after module load
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        self.index_dir = "faiss_indexes"
        os.makedirs(self.index_dir, exist_ok=True)

    def _get_path(self, user_id: str) -> str:
        return os.path.join(self.index_dir, f"user_{user_id}")

    def add_preference(self, user_id: str, text: str) -> None:
        """Embed and store a user preference/habit in FAISS."""
        path = self._get_path(user_id)
        doc = Document(page_content=text, metadata={"user_id": str(user_id)})

        try:
            if os.path.exists(path):
                vectorstore = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
                vectorstore.add_documents([doc])
            else:
                vectorstore = FAISS.from_documents([doc], self.embeddings)

            vectorstore.save_local(path)
            logger.info("Added to long term memory", extra={"user_id": str(user_id)})
        except Exception as e:
            logger.error("Failed to add to long term memory", extra={"error": str(e)})

    def retrieve_context(self, user_id: str, query: str, k: int = 5) -> str:
        """Retrieve top-k relevant memories for current query. Returns empty string if none exist."""
        path = self._get_path(user_id)
        if not os.path.exists(path):
            return ""

        try:
            vectorstore = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
            docs = vectorstore.similarity_search(query, k=k)
            return "\n".join([d.page_content for d in docs])
        except Exception as e:
            logger.error("Failed to retrieve context", extra={"error": str(e)})
            return ""
