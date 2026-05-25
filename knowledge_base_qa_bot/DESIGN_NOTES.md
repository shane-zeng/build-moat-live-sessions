# Knowledge Base Q&A Bot Notes

## Current Choice

I chose the Guided Track with the Markdown KB strategy.

The main reason is that the sample knowledge base is small, and I am still learning the retrieval flow. Markdown KB is easier to debug because the generated `.kb/index.json` is inspectable and the retrieved Markdown sections are human-readable.

## Core Idea

The bot should not answer only from the model's memory. It should first retrieve relevant knowledge base content, then ask the LLM to answer using only that context.

The Markdown KB flow is:

```text
Markdown files
-> heading sections
-> section index
-> BM25 keyword search
-> raw Markdown context
-> LLM answer with citations
```

## Retrieval Unit

The retrieval unit is a Markdown section, not a whole file or arbitrary chunk.

This keeps the retrieved context focused while preserving the structure of the original document. For example, a refund question should retrieve:

```text
refund_policy.md#refund-timeline
```

instead of the whole `refund_policy.md` file.

## Source Citation

Each indexed section has a stable source reference in this format:

```text
filename#heading
```

Examples:

```text
refund_policy.md#refund-timeline
account_help.md#change-email-address
shipping_faq.md#standard-shipping
```

The answer should cite these source references so users can inspect the original Markdown section.

## Prompt Design

The prompt includes:

- the user question
- the top retrieved Markdown sections
- each section's source id
- instructions to answer only from the provided context
- fallback behavior when the context does not contain the answer

The prompt should not include the entire knowledge base because unrelated content can distract the model and waste tokens.

## Fallback Behavior

If retrieval finds no relevant sections, or if the context does not contain enough information, the system should say:

```text
I cannot confirm from the knowledge base.
```

This is better than forcing an answer with weak evidence.

## Score Threshold and Fallback

The BM25 score works like a small search relevance score. This is similar to Elasticsearch: search returns documents with scores, and the application can set a threshold so weak matches are not treated as good results.

In this bot, the threshold is a quality gate before the LLM. Finding a section is not enough. The best retrieved section also needs to be relevant enough before it is added to the prompt.

The flow becomes:

```text
question
-> BM25 search
-> filter sections by minimum score
-> fallback if all scores are too weak
-> send strong sections to the LLM
```

This helps avoid sending weak or irrelevant context to the model. If the retrieval score is too low, the bot should say it cannot confirm from the knowledge base instead of forcing an answer with a shaky citation.

The current implementation uses `MIN_BM25_SCORE`, which can be tuned through the environment if the retrieval behavior is too strict or too loose.

## How to Test the Score Threshold

The threshold is read when the server starts, so the server needs to be restarted after changing `MIN_BM25_SCORE`.

Start with the default threshold:

```bash
MIN_BM25_SCORE=1.5 python -m uvicorn app.main:app --reload
```

Then build the index:

```bash
curl -X POST http://localhost:8000/index
```

Ask a strong in-scope question:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Can I change my email address?"}'
```

With the default threshold, this should return an answer with `account_help.md#change-email-address`. The response may also show weaker matches with lower scores, such as `shipping_faq.md#tracking-number`, if their score is still above the threshold.

To prove the threshold is working, restart the server with a very high threshold:

```bash
MIN_BM25_SCORE=10 python -m uvicorn app.main:app --reload
```

Ask the same question again. Since the best score for the email question is below 10, the system should now return:

```json
{
  "answer": "I cannot confirm from the knowledge base.",
  "sources": []
}
```

This confirms that retrieval can find sections, but the system still refuses to send them to the LLM when the scores are below the threshold.

Another useful test is setting the threshold to `2`. For the email question, the strong account section should remain, while weaker sections around `1.5` should be filtered out.

## Verification Results

The core curl tests passed:

- `/health` returns server status.
- `/chat` before indexing asks the user to call `POST /index` first.
- `/index` indexes 3 files and 9 sections.
- refund questions retrieve `refund_policy.md#refund-timeline`.
- email change questions retrieve `account_help.md#change-email-address`.
- out-of-scope questions fall back instead of inventing an answer.

## Tradeoffs

Markdown KB is strong when:

- the knowledge base is small or medium-sized
- documents are well-structured with headings
- debugging and inspectability matter
- citations should map cleanly to Markdown sections
- embedding cost and vector infrastructure are not necessary

Markdown KB is weaker when:

- users ask many paraphrased or semantic questions
- relevant answers use different wording than the query
- the knowledge base becomes very large
- keyword search misses synonyms or related concepts

Vector RAG becomes more useful when semantic retrieval matters more than inspectability. However, it can retrieve chunks that are semantically similar but not actually correct, so it still needs careful evaluation.

## Possible Next Steps

Good stretch goals for this prototype:

- Add a BM25 score threshold for weak retrieval results.
- Generate `wiki/index.md` from `.kb/index.json`.
- Compare paraphrased questions between Markdown KB and Vector RAG.

I would start with the score threshold because it directly improves retrieval quality and fallback behavior.
