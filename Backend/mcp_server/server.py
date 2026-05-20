from fastmcp import FastMCP
from rag.graph_rag import GraphRetriever
from utils import get_logger

mcp = FastMCP("Fitness RAG MCP Server")
log = get_logger("mcp")


@mcp.tool()
def query_knowledge_graph(query: str):
    """Query the knowledge graph for fitness-related information"""
    log.info(f"Querying knowledge graph: {query}")
    retriever = GraphRetriever()
    response = retriever.query(query)
    return response


if __name__ == "__main__":
    mcp.run()
