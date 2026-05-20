from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.mcp_client import MCPClient

router = APIRouter()

mcp_client = MCPClient()


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def query_graph(request: QueryRequest):
    try:
        response = mcp_client.process_query(request.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
