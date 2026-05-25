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
