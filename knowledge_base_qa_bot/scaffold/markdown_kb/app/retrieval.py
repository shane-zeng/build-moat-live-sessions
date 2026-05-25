import os

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from . import indexer


# Write the system prompt for the knowledge base Q&A assistant.
#
# Design decision: Hallucination defense for raw Markdown context.
#
# Hints:
# 1. Only answer using the provided CONTEXT.
# 2. Cite only exact source IDs shown in [Source: ...].
#    Each source ID uses filename#heading format.
# 3. Define fallback behavior when the context lacks the answer.
# 4. Explicitly prohibit guessing or outside knowledge.
SYSTEM_PROMPT = """You are a knowledge base Q&A assistant.
Rules:
1. Only answer using the provided CONTEXT.
2. Cite only exact source IDs shown in [Source: ...].
3. If the CONTEXT does not contain the answer, say: "I cannot confirm from the knowledge base."
4. Do not guess, invent policies, or use outside knowledge.
"""
MIN_BM25_SCORE = float(os.getenv("MIN_BM25_SCORE", "1.5"))

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            request_timeout=20,
            max_retries=1,
        )
    return _llm


def build_prompt(query: str, ranked_sections: list) -> str:
    # Build the prompt from top-ranked Markdown sections.
    #
    # Design decision: Put raw Markdown sections into CONTEXT with citations.
    #
    # Hints:
    # 1. Include [Source: filename#heading] before each section.
    # 2. Include heading_path so the model sees the document structure.
    # 3. Include only top sections passed into this function.
    # 4. Place CONTEXT before QUESTION.
    context_blocks = []
    for section, score in ranked_sections:
        heading_lines = "\n".join(
            f"{'#' * (idx + 1)} {heading}"
            for idx, heading in enumerate(section.heading_path)
        )
        context_blocks.append(
            f"[Source: {section.id}]\n"
            f"[BM25 score: {score:.2f}]\n"
            f"{heading_lines}\n\n"
            f"{section.content}"
        )

    context = "\n\n---\n\n".join(context_blocks)
    return f"CONTEXT:\n{context}\n\nQUESTION:\n{query}"


def query(question: str) -> dict:
    if not indexer.sections:
        return {
            "answer": "The knowledge base has not been indexed yet. Call POST /index first.",
            "sources": [],
        }

    ranked_sections = indexer.search(question, k=3)
    if not ranked_sections:
        return {
            "answer": "I cannot confirm from the knowledge base.",
            "sources": [],
        }

    strong_sections = [
        (section, score)
        for section, score in ranked_sections
        if score >= MIN_BM25_SCORE
    ]
    if not strong_sections:
        return {
            "answer": "I cannot confirm from the knowledge base.",
            "sources": [],
        }

    response = get_llm().invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_prompt(question, strong_sections)),
    ])

    sources = [
        {
            "source": section.id,
            "heading": " > ".join(section.heading_path),
            "score": round(score, 3),
            "content": section.content[:240],
        }
        for section, score in strong_sections
    ]

    return {
        "answer": response.content,
        "sources": sources,
    }
