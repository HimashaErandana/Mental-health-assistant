import json
import logging
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.messages import HumanMessage, SystemMessage
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
from llm import GroqClient

log = logging.getLogger("graph_retriever")

RELATIONSHIPS_TREAT = [
    "MANAGES",
    "TREATS",
    "REDUCES",
    "HELPS",
    "HELPS_WITH",
    "AMELIORATES",
    "PREVENTS",
    "LOWERS",
]
RELATIONSHIPS_SYMPTOM = [
    "HAS_SYMPTOM",
    "HAS_SYMPTOMS",
    "INCLUDES_SYMPTOM",
    "HAS_SYMPTOM_CATEGORY",
    "SYMPTOM_OF",
]
RELATIONSHIPS_RELATED = ["RELATED_TO", "ASSOCIATED_WITH", "CONNECTED_TO", "LINKED_TO"]


class GraphRetriever:
    def __init__(self):
        self.graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )
        self.llm_client = GroqClient()
        self.llm = self.llm_client.get_llm()
        self.chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            verbose=False,
            allow_dangerous_requests=True,
            return_direct=True,
            top_k=15,
        )

    def search_concepts(self, keyword: str, limit: int = 15) -> list[dict]:
        """Search any node containing keyword (case-insensitive)"""
        cypher = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS $keyword
        RETURN n.id AS id, labels(n)[0] AS label
        ORDER BY CASE WHEN labels(n)[0] IN ['Condition', 'Disorder', 'Emotion'] THEN 0 ELSE 1 END
        LIMIT $limit
        """
        return self.graph.query(cypher, {"keyword": keyword.lower(), "limit": limit})

    def get_related(self, concept: str, limit: int = 15) -> list[dict]:
        """Get concepts directly related to the given concept"""
        cypher = """
        MATCH (c)-[r:RELATED_TO|ASSOCIATED_WITH|CONNECTED_TO|LINKED_TO|LOOKS_LIKE]-(related)
        WHERE toLower(c.id) CONTAINS $concept
        RETURN related.id AS id, labels(related)[0] AS label
        LIMIT $limit
        """
        return self.graph.query(cypher, {"concept": concept.lower(), "limit": limit})

    def get_treatments(self, condition: str, limit: int = 15) -> list[dict]:
        """Get treatments/techniques that manage/reduce a condition"""
        rels = "|".join(RELATIONSHIPS_TREAT)
        cypher = f"""
        MATCH (treatment)-[r:{rels}]->(c)
        WHERE toLower(c.id) CONTAINS $condition
        RETURN treatment.id AS id, labels(treatment)[0] AS label, type(r) AS relationship
        LIMIT $limit
        """
        return self.graph.query(
            cypher, {"condition": condition.lower(), "limit": limit}
        )

    def get_symptoms(self, condition: str, limit: int = 15) -> list[dict]:
        """Get symptoms of a condition"""
        rels = "|".join(RELATIONSHIPS_SYMPTOM)
        cypher = f"""
        MATCH (c)-[r:{rels}]->(symptom)
        WHERE toLower(c.id) CONTAINS $condition
        RETURN symptom.id AS id, labels(symptom)[0] AS label, type(r) AS relationship
        LIMIT $limit
        """
        return self.graph.query(
            cypher, {"condition": condition.lower(), "limit": limit}
        )

    def get_full_context(self, concept: str, limit: int = 20):
        """Get full context: related concepts + treatments + symptoms"""
        related = self.get_related(concept, limit=limit)
        treatments = self.get_treatments(concept, limit=limit)
        symptoms = self.get_symptoms(concept, limit=limit)
        return {
            "related": related,
            "treatments": treatments,
            "symptoms": symptoms,
        }

    def query(self, question: str) -> list[dict]:
        # Extract keyword from question
        keywords = [
            "anxiety",
            "depression",
            "stress",
            "panic",
            "burnout",
            "loneliness",
            "sleep",
        ]
        keyword = None
        for kw in keywords:
            if kw in question.lower():
                keyword = kw
                break
        if not keyword:
            keyword = question.lower().split()[0] if question else "anxiety"

        # Try custom methods first (no LLM, fast + free)
        log.info(f"Trying custom retrieval for: {keyword}")
        fallback = self.get_full_context(keyword, limit=15)
        result = []
        for t in fallback.get("treatments", []):
            result.append(
                {
                    "text": t["id"],
                    "label": t["label"],
                    "relationship": t["relationship"],
                }
            )
        for s in fallback.get("symptoms", []):
            result.append(
                {
                    "text": s["id"],
                    "label": s["label"],
                    "relationship": s["relationship"],
                }
            )
        for r in fallback.get("related", []):
            result.append({"text": r["id"], "label": r["label"]})

        # If limited results, try LLM chain as fallback
        if len(result) < 3:
            try:
                log.info(f"Trying LLM chain for: {question}")
                response = self.chain.invoke({"query": question})
                llm_result = response["result"]
                if llm_result:
                    result.extend(llm_result)
            except Exception as e:
                log.warning(f"LLM chain failed: {e}")

        log.info(f"Retrieved {len(result)} results")
        print(f"\n=== Raw JSON Results ===")
        print(json.dumps(result, indent=2))
        print("=" * 24)
        return result

    def generate_answer(self, question: str) -> str:
        """Use LLM to generate natural language answer from retrieved context"""
        context_data = self.query(question)

        if not context_data:
            return "I couldn't find relevant information for your query."

        treatments = [
            r
            for r in context_data
            if r.get("relationship") in RELATIONSHIPS_TREAT
        ]
        symptoms = [r for r in context_data if r.get("relationship") in RELATIONSHIPS_SYMPTOM]
        related = [r for r in context_data if not r.get("relationship")]

        context_parts = []
        if treatments:
            context_parts.append(
                "TREATMENTS/MANAGEMENT:\n"
                + "\n".join(f"- {t['text']}" for t in treatments[:8])
            )
        if symptoms:
            context_parts.append(
                "SYMPTOMS:\n" + "\n".join(f"- {s['text']}" for s in symptoms[:8])
            )
        if related:
            context_parts.append(
                "RELATED CONCEPTS:\n" + "\n".join(f"- {r['text']}" for r in related[:8])
            )

        context = "\n\n".join(context_parts)

        system_prompt = """You are a helpful mental health assistant. Use the provided context from the knowledge graph to answer the user's question in a clear, supportive way.

Guidelines:
- Be empathetic and supportive
- Only provide information that's in the context
- If recommending treatments or techniques, mention that professional help is important
- Don't make medical claims - suggest consulting a healthcare provider
- Keep answers concise but informative
- Format with bullet points when listing items
- If the context doesn't fully answer the question, be honest about what's available"""

        user_prompt = f"""Context from knowledge graph:

{context}

User question: {question}

Please provide a helpful, empathetic response based on the context above."""

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            return response.content
        except Exception as e:
            log.error(f"LLM answer generation failed: {e}")
            return f"I found relevant information but couldn't generate a response. Here are the key items:\n{context}"

    def refresh_schema(self) -> None:
        self.graph.refresh_schema()

    def get_schema(self) -> str:
        schema = self.graph.schema
        print(f"\n=== Graph Schema ===")
        print(schema)
        print("=" * 24)
        return schema
