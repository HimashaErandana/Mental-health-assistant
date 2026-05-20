from langchain_groq import ChatGroq
from config import GROQ_API_KEY


class GroqClient:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=model_name)

    def get_llm(self):
        return self.llm
