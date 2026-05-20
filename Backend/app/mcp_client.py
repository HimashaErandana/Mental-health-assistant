import json
import uuid
import logging
from config import GROQ_API_KEY
from utils import get_logger
from langchain_groq import ChatGroq
from db import save_message, get_chat_history, clear_session, get_recent_context

log = get_logger("mcp_client")

TOOLS = [
    {
        "name": "query_knowledge_graph",
        "description": "Query the knowledge graph for mental health and wellness information. Use when user asks about mental health conditions (anxiety, depression, stress, panic, burnout, etc.), coping techniques, emotions, treatments, symptoms, lifestyle, sleep, exercise, or any wellness-related topics.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user query about mental health or wellness",
                }
            },
            "required": ["query"],
        },
    }
]


class MCPClient:
    def __init__(self, session_id: str = None):
        self.llm_api_key = GROQ_API_KEY
        self.session_id = session_id or str(uuid.uuid4())

    def _llm_decide_tool(self, query: str) -> dict:
        llm = ChatGroq(
            groq_api_key=self.llm_api_key, model_name="llama-3.3-70b-versatile"
        )

        tools_json = json.dumps(TOOLS, indent=2)
        prompt = f"""You have these tools available:
{tools_json}

User query: "{query}"

Decide which tool to use. Return ONLY a JSON object with "tool" and "args" keys.

If no tool is needed, return: {{"tool": null, "args": {{}}}}"""

        response = llm.invoke(prompt)
        try:
            result = json.loads(response.content)
            log.info(f"LLM tool decision: {result}")
            return result
        except:
            log.warning(f"Failed to parse LLM response: {response.content}")
            return {"tool": "query_knowledge_graph", "args": {"query": query}}

    def _call_mcp_tool(self, tool_name: str, args: dict) -> dict:
        from rag.graph_rag import GraphRetriever

        try:
            if tool_name == "query_knowledge_graph":
                retriever = GraphRetriever()
                user_query = args.get("query", "")

                # Check if user wants raw data or natural language answer
                # Default to generate_answer for natural language response
                if "raw" in user_query.lower() or "json" in user_query.lower():
                    result = retriever.query(user_query)
                    return {"data": result}
                else:
                    # Generate natural language answer
                    answer = retriever.generate_answer(user_query)
                    return {"answer": answer}
            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            log.error(f"MCP tool call error: {e}")
            return {"error": str(e)}

    def process_query(self, query: str):
        log.info(f"Processing query: {query}")
        try:
            # Save user message to database
            try:
                save_message(self.session_id, "user", query)
            except Exception as e:
                log.warning(f"Failed to save user message: {e}")

            decision = self._llm_decide_tool(query)
            tool_name = decision.get("tool")

            if not tool_name:
                return {
                    "answer": "I couldn't find a suitable tool for this query.",
                    "session_id": self.session_id,
                }

            result = self._call_mcp_tool(tool_name, decision.get("args", {}))

            # If result has "answer" key, return it directly for chat UI
            if "answer" in result:
                # Save assistant response with message_type = "ai"
                try:
                    save_message(self.session_id, "ai", result["answer"])
                except Exception as e:
                    log.warning(f"Failed to save ai message: {e}")

                return {"answer": result["answer"], "session_id": self.session_id}

            # If result has "data" key, return raw JSON for debugging
            if "data" in result:
                return {"raw_data": result["data"], "session_id": self.session_id}

            return result
        except Exception as e:
            log.error(f"Error: {e}")
            return {
                "answer": f"I encountered an error: {str(e)}",
                "session_id": self.session_id,
            }
