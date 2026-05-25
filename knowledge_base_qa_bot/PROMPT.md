# Design a Knowledge Base Q&A Bot

## System Requirements

Build a Q&A bot over a small Markdown knowledge base:

- The repo provides sample `.md` documents in `docs/`
- The system builds an index from those documents
- The Markdown KB strategy should write an inspectable `.kb/index.json`
- The Vector RAG strategy should persist its FAISS index in `.kb/faiss_index/`
- Users ask questions through an API
- Answers must be grounded in the indexed documents
- Answers must cite sources using `filename#heading`
- If the knowledge base does not contain the answer, the system should say it cannot confirm

## Choose a Retrieval Strategy

You can solve this with either strategy:

### Strategy A: Markdown KB

```text
Markdown files -> heading sections -> section index -> BM25 keyword search -> raw Markdown context -> LLM answer
```

This is inspired by the Karpathy-style LLM knowledge base pattern: plain Markdown files, explicit indexes, and LLM-readable context instead of embeddings.

### Strategy B: Vector RAG

```text
Markdown files -> chunks -> embeddings -> vector search -> retrieved context -> LLM answer
```

This is the traditional RAG path: semantic retrieval with embeddings and a vector store.

## Design Questions

Answer these before you start coding:

1. Which retrieval strategy did you choose, and why?

   I would choose Markdown KB because the knowledge base is small and I am still learning the retrieval flow. It is also easier to debug because the index is inspectable and the retrieved Markdown sections are human-readable.
2. What is the retrieval unit in your design: file, section, or chunk?

   The retrieval unit is a Markdown section. Each section is defined by a Markdown heading and its content. This is more precise than retrieving a whole file, while still preserving the document structure better than arbitrary chunks.
3. How do you decide what goes into the prompt?

   The prompt should include the user question, the top relevant Markdown sections, and each section's source reference such as `filename#heading`. It should also instruct the model to answer only from the provided context, cite sources clearly, and say it cannot confirm if the context does not contain enough information.
4. How do you cite sources so users can inspect the original Markdown?

   Each indexed section should have a stable source reference in the format `filename#heading`. The answer should include the relevant source references so users can open the original Markdown file and inspect the exact section used to generate the answer.
5. What should happen when retrieval finds weak or irrelevant results?

   If retrieval finds weak or irrelevant results, the system should return a fallback response instead of forcing an answer. I would use a score threshold and ask the model to say it cannot confirm from the knowledge base when the retrieved context is not strong enough.
6. When would you switch from Markdown KB to Vector RAG?

   I would switch from Markdown KB to Vector RAG when keyword or heading-based retrieval starts missing relevant answers, especially when users ask more semantic or paraphrased questions. I would also consider Vector RAG when the knowledge base becomes much larger and section-level keyword search is no longer accurate enough.
7. When would you switch from Vector RAG back to a Markdown index?

   I would switch from Vector RAG back to a Markdown index when the knowledge base is small, well-structured, and easier to navigate by headings or keywords. I would also switch back if vector search returns semantically similar but incorrect chunks, or if I need better debuggability, lower cost, and more inspectable citations.
8. If the knowledge base grows from 10 files to 100,000 files, what changes?

   If the knowledge base grows to 100,000 files, I would not rebuild the whole index on every update. I would need incremental indexing, better metadata, and a more scalable search backend instead of only an in-memory index or local JSON file. I would also consider hybrid retrieval with keyword and vector search, plus monitoring for retrieval quality and stale or incorrect documents.

## Verification

Before running the server, set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Both strategies use OpenAI for final answer generation. Vector RAG also uses OpenAI embeddings during `/index` and for each `/chat` query.

Your prototype should pass all of these:

```bash
# Health check
curl http://localhost:8000/health
# -> 200, {"status": "ok"}

# Chat before indexing
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How long do refunds take?"}'
# -> 200, should indicate the knowledge base has not been indexed yet

# Build the index from docs/*.md
curl -X POST http://localhost:8000/index
# -> 200, returns {"files_indexed": N, "sections_indexed": M}

# Markdown KB only: inspect the generated section index
cat .kb/index.json

# Markdown KB only: restart the server, then ask again without POST /index
# -> should load .kb/index.json on startup

# Vector RAG only: inspect the persisted FAISS index metadata
cat .kb/faiss_index/metadata.json

# Vector RAG only: restart the server, then ask again without POST /index
# -> should load .kb/faiss_index/ on startup

# Ask a question answered by the docs
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How long do refunds take?"}'
# -> 200, answer cites refund_policy.md#refund-timeline

# Ask another grounded question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Can I change my email address?"}'
# -> 200, answer cites account_help.md#change-email-address

# Ask an out-of-scope question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Which restaurants are nearby?"}'
# -> 200, answer should say it cannot confirm from the knowledge base
```

## Suggested Tech Stack

Python + FastAPI is recommended, but Challenge Track students may use any language or framework.

## Stretch Goals

Pick one or more after the core `/index` and `/chat` flow works.

### Score Threshold and Fallback

Add a retrieval score threshold. If the best sections or chunks are too weak, return an honest cannot-confirm answer instead of forcing a citation.

### Streaming Interface

After `/chat` works, add:

```text
POST /chat/stream
```

Use SSE to stream the answer token by token. A good streaming response should:

- Return selected sources first, so users can see what context the bot is using
- Stream answer tokens as they arrive
- End with a clear `done` event
- Preserve the same grounding and citation rules as `/chat`

Optional UI challenge: build a tiny HTML page that calls `/chat/stream` and renders the answer incrementally.

### Browser UI

Build a tiny browser UI over `/chat` or `/chat/stream`. Show selected sources before the answer so users can inspect grounding.

### Multi-Format Import

Add a small normalization pipeline before indexing:

```text
raw/*.txt or raw/*.html -> docs/*.md -> POST /index -> retrieval index
```

Requirements:

- Keep Markdown as the canonical knowledge format
- Preserve the original source filename
- Convert headings into Markdown headings
- Rebuild the retrieval index after import

Start with `.txt` or `.html`. More complex formats such as PDFs, spreadsheets, and transcripts can be discussed as production extensions.

### Alternative Interfaces

Expose the same retrieval core through another interface:

```text
CLI: kb index / kb ask
MCP: expose index, search, and chat as agent tools
Web UI: simple chat screen over /chat or /chat/stream
```

The goal is to compare interface tradeoffs, not to change the retrieval design.

### Wiki Index Generation

Generate `wiki/index.md` from `.kb/index.json` so humans and agents can browse the available topics.

### Answer Filing

Write useful Q&A results back into `wiki/` after review. Preserve citations back to the source Markdown sections.

### Conversation Memory

Add short conversation memory for follow-up questions. Memory can help interpret the query, but retrieved sources must still control the final answer.

### Paraphrase Comparison

Create paraphrased queries and compare Markdown KB vs Vector RAG. Look for synonym misses, semantic false positives, and citation quality.
