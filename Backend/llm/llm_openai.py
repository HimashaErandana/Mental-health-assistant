from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY


class OpenAIClient:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=model_name)

    def get_llm(self):
        return self.llm
