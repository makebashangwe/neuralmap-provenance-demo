# Architecture

## Problem

Conversation archives contain two different kinds of structure that should not be confused:

1. **Source structure** — what message actually followed what, including branches and regenerated answers.
2. **Semantic structure** — what activities, concepts, decisions, and relationships the content represents.

NeuralMap keeps those layers separate.

## Layer 1 — Lossless normalized source

The normalized source model separates:

- `conversation` — the archive container,
- `node` — a structural position in the conversation tree,
- `message` — communication/content associated with a node,
- `text_span` — a traceable source string within a message.

A node is not the same thing as a message. Structural nodes may exist even when they contain no user-visible text.

## Layer 2 — Dialogue projection

The dialogue layer creates human-meaningful units without discarding source topology.

An `exchange_unit` groups a user message with the assistant continuation that follows it **on the same source path**.

A fork ends linear compaction. Alternate assistant answers remain alternate branches.

## Layer 3 — Semantic segmentation

The production project asks a deliberately narrow macro question:

> **What activity is the user doing, and when did that activity actually change?**

This is different from extracting every concept mentioned in the text.

Example:

```text
Activity segment:
  Building Viridian backend

Concepts inside it:
  FastAPI
  PostgreSQL
  authentication
  JWT
  migrations
```

The public demo uses deterministic labels on synthetic evidence so the architecture can be inspected safely.

## Layer 4 — Knowledge graph

Later semantic records can represent:

- projects,
- concepts,
- technologies,
- decisions,
- goals,
- beliefs,
- people,
- events,
- relationships.

Critically, these are **derived records** that point back to source evidence.

Example:

```text
Viridian --uses--> PostgreSQL
          evidence:
          exchange_17
          text_span_221
```

The inferred relationship can be revised later without mutating the original source text.

## Provenance

The core design rule is:

> Preserve source truth. Layer interpretation on top. Keep a path back to evidence.

That allows later models to be replaced, compared, or corrected without rewriting history.
