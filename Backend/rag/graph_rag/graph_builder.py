from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
from llm import OpenAIClient


class GraphBuilder:
    def __init__(self):
        self.graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )
        self.llm_client = OpenAIClient()
        self.llm = self.llm_client.get_llm()
        self.transformer = LLMGraphTransformer(llm=self.llm)

    def build_graph(self, documents: list[Document]) -> None:
        for i, doc in enumerate(documents):
            print(f"Processing document {i + 1}/{len(documents)}...")
            graph_docs = self.transformer.convert_to_graph_documents([doc])
            self.graph.add_graph_documents(graph_docs)
            self.graph.refresh_schema()

    def get_schema(self) -> str:
        return self.graph.schema
