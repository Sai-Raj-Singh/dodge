"""Response generator — converts raw query results into natural language using Gemini.

Takes execution results (graph rows + RAG chunks) and produces a
human-readable answer grounded in the data. No hallucination — only
facts from retrieved data are included.
"""

import json
import re

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted

from app.config import settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


SYSTEM_PROMPT = """\
You are a precise SAP Order-to-Cash document flow analyst.

RULES:
1. Answer ONLY using the DATA provided below. Never invent data.
2. Always include entity IDs (Sales Order numbers, Delivery numbers, etc.) in your answer.
3. When describing document flows use arrow notation: SalesOrder -> Delivery -> Billing -> Payment.
4. Format monetary values with currency (e.g. 1,234.56 INR).
5. If the data is empty or insufficient, say so clearly.
6. Be concise but complete. Use bullet points or tables when listing multiple items.
7. Do NOT add disclaimers about being an AI or about data accuracy.
"""


def _format_graph_results(rows: list[dict]) -> str:
    """Format graph query results into a readable context block."""
    if not rows:
        return "No graph results found."

    # Limit to avoid token overflow
    capped = rows[:50]
    lines = []
    for i, row in enumerate(capped, 1):
        # Clean None values for readability
        clean = {k: v for k, v in row.items() if v is not None}
        lines.append(f"  Row {i}: {json.dumps(clean, default=str)}")

    text = "\n".join(lines)
    if len(rows) > 50:
        text += f"\n  ... and {len(rows) - 50} more rows"
    return text


def _format_rag_results(chunks: list[dict]) -> str:
    """Format RAG search results into a readable context block."""
    if not chunks:
        return "No semantic search results found."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"  [{i}] {chunk.get('text', '')}")
    return "\n".join(lines)


def _fallback_answer_from_data(
    query: str,
    execution_result: dict,
    description: str,
    reason: str = "",
) -> str:
    """When Gemini is unavailable (rate limit, outage), show retrieved data in plain text."""
    graph_rows = execution_result.get("graph_results") or []
    rag_chunks = execution_result.get("rag_results") or []
    err = execution_result.get("error")

    lines: list[str] = []
    lines.append("Answer (from your data — AI summarization skipped)")
    if reason:
        lines.append(f"\n{reason}\n")
    lines.append(f"\nYour question: {query}")
    if description:
        lines.append(f"\nWhat we looked up: {description}")
    if err:
        lines.append(f"\nNote: {err}")

    if graph_rows:
        lines.append(f"\n\nGraph results ({len(graph_rows)} row(s)):")
        for i, row in enumerate(graph_rows[:40], 1):
            clean = {k: v for k, v in row.items() if v is not None}
            lines.append(f"\n{i}. {json.dumps(clean, default=str)}")
        if len(graph_rows) > 40:
            lines.append(f"\n… and {len(graph_rows) - 40} more rows.")

    if rag_chunks:
        lines.append(f"\n\nSemantic search ({len(rag_chunks)} chunk(s)):")
        for i, chunk in enumerate(rag_chunks[:12], 1):
            text = (chunk.get("text") or "")[:1200]
            lines.append(f"\n{i}. {text}")
        if len(rag_chunks) > 12:
            lines.append(f"\n… and {len(rag_chunks) - 12} more chunks.")

    if not graph_rows and not rag_chunks and not err:
        lines.append(
            "\nNo rows were returned. Try a different question or include a document ID "
            "(e.g. Sales Order 740506)."
        )

    lines.append(
        "\n\n---\nTip: If the AI is often unavailable, wait between questions or check "
        "Google AI Studio quotas for your API key."
    )
    return "".join(lines)


def _empty_results_message(query: str, description: str) -> str:
    """Clear message when graph + RAG return nothing (exact journal lookup vs generic)."""
    q = (query or "").lower()
    d = (description or "").lower()
    if "journal" in q or "journal" in d or "exact lookup for journal" in d:
        m = re.search(r"\b(\d{8,12})\b", query or "")
        nid = m.group(1) if m else "that document ID"
        return (
            f"No journal entry was found for document ID {nid}. "
            "The system searches by exact accounting document or reference document number only "
            "(not prefix matches such as 91150*). This ID may be absent from the loaded graph."
        )
    return (
        "No results found for your query. Please try rephrasing or provide specific entity IDs "
        "(e.g. Sales Order 740506)."
    )


def _safe_model_text(response: object) -> str:
    """Extract text from generate_content response without raising."""
    if response is None:
        return ""
    try:
        t = getattr(response, "text", None)
        if t:
            return str(t)
    except Exception:
        pass
    try:
        cands = getattr(response, "candidates", None) or []
        for c in cands:
            content = getattr(c, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []) or []:
                pt = getattr(part, "text", None)
                if pt:
                    return str(pt)
    except Exception:
        pass
    return ""


def generate(
    query: str,
    execution_result: dict,
    description: str = "",
) -> str:
    """Generate a natural language response using Gemini.

    Args:
        query: The original user question.
        execution_result: dict from executor.execute() with graph_results / rag_results.
        description: What the system did (from the plan).

    Returns:
        Natural language answer string.
    """
    _ensure_configured()

    # Build context from results
    context_parts = []

    if description:
        context_parts.append(f"Action taken: {description}")

    graph_rows = execution_result.get("graph_results")
    rag_chunks = execution_result.get("rag_results")
    error = execution_result.get("error")

    if error:
        context_parts.append(f"Error during execution: {error}")

    if graph_rows is not None:
        context_parts.append(
            f"GRAPH QUERY RESULTS ({len(graph_rows)} rows):\n"
            + _format_graph_results(graph_rows)
        )

    if rag_chunks is not None:
        context_parts.append(
            f"SEMANTIC SEARCH RESULTS ({len(rag_chunks)} chunks):\n"
            + _format_rag_results(rag_chunks)
        )

    if not graph_rows and not rag_chunks and not error:
        return _empty_results_message(query, description)

    data_context = "\n\n".join(context_parts)

    user_prompt = f"""USER QUESTION: {query}

DATA:
{data_context}

Provide a clear, concise answer based ONLY on the data above."""

    model = genai.GenerativeModel(
        model_name=settings.gemini_llm_model,
        system_instruction=SYSTEM_PROMPT,
    )

    # Single LLM attempt — on rate limit / any API error, return data fallback (no long retry loop).
    try:
        response = model.generate_content(user_prompt)
        text = _safe_model_text(response)
        if text.strip():
            return text
    except ResourceExhausted:
        print("[GEMINI] ResourceExhausted — returning data fallback.")
    except GoogleAPIError as e:
        print(f"[GEMINI] GoogleAPIError — {e!r}; returning data fallback.")
    except Exception as e:
        print(f"[GEMINI] {type(e).__name__}: {e!r}; returning data fallback if data exists.")

    if (graph_rows or []) or (rag_chunks or []):
        return _fallback_answer_from_data(
            query,
            execution_result,
            description,
            reason="Gemini could not produce a summary (quota/rate limit or API error). Showing retrieved rows below.",
        )

    return (
        "No results found for your query, and the language model could not run. "
        "Try again in a minute or check your GEMINI_API_KEY and quotas in Google AI Studio."
    )
