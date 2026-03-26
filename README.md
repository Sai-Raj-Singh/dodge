# SAP O2C Graph + RAG Flow Engine

End-to-end enterprise document flow engine for SAP-style Order-to-Cash data.

This project transforms transactional JSONL datasets into a Neo4j graph and supports natural language querying over document flows:

`SalesOrder -> Delivery -> BillingDocument -> JournalEntry -> Payment`

The **Streamlit app** (`streamlit_app/app.py`) pairs an interactive **vis-network** graph (left) with a **chat panel** (right): chat answers come from `POST /ask`, and the graph view refreshes from `GET /graph/subgraph` with focus derived from classified entity IDs (sales order, delivery, billing, or journal) so the relevant O2C path is **highlighted** on top of a **full overview** subgraph.

---

## Working Demo Link

- First open the backend deployed link: 'https://dodge-5seu.onrender.com'
- After the backend server is running properly open the Demo UI link: 'https://dodge-1.onrender.com/'


---

## Problem Statement

Given SAP-like operational datasets (orders, deliveries, billing docs, journal entries, payments, customers, products, plants), build a query system that can:

1. Trace complete document flows
2. Detect broken flows (e.g., delivered-not-billed, billed-not-paid)
3. Answer natural language questions reliably with IDs and flow paths
4. Avoid hallucination by prioritizing graph retrieval and constrained generation

---

## High-Level Architecture

### Core stack

- **Backend API:** FastAPI
- **Graph DB:** Neo4j (Aura DB)
- **Vector DB:** ChromaDB (persistent local store)
- **LLM:** Google Gemini (`gemini-2.0-flash`)
- **Frontend:** Streamlit

### Data and processing flow

1. **Ingestion layer** parses JSONL folders into typed entities (Pydantic models)
2. **Graph builder** loads normalized entities into Neo4j nodes + relationships
3. **Chunker** generates entity and flow text summaries from graph data
4. **Vector seeder** stores chunk texts in ChromaDB (local embedding model)
5. **Query pipeline** classifies intent and routes to graph / rag / hybrid execution
6. **Response generator** synthesizes final answer only from retrieved evidence (with **fallback** text from raw graph/RAG evidence when the LLM is unavailable or rate-limited)
7. **Guardrails** reject unrelated questions before execution
8. **UI/API** exposes `/ask`, `**/graph/subgraph`** (merged overview + optional focused O2C chain with `highlightNodeIds` / `highlightEdgeIds`), flow trace endpoints, and broken flow summary; the Streamlit client renders the graph in an iframe and syncs focus after each chat reply

---

## Repository Structure

```text
app/
  config.py
  ingestion/
    schemas.py
    loader.py
    normalizer.py
  graph/
    connection.py
    builder.py
    indexes.py
    queries.py
  rag/
    chunker.py
    embeddings.py
    vector_store.py
  query/
    classifier.py
    enhancer.py
    executor.py
    response.py
    __init__.py
  flow/
    tracer.py
    detector.py
  guardrails/
    validator.py
  api/
    main.py
    routes.py

scripts/
  seed_graph.py
  seed_vectors.py
  reset_db.py

streamlit_app/
  app.py
```

---

## Database Choice and Rationale

### Why Neo4j for this workload

This problem is relationship-centric, not table-centric. O2C documents form chains and branching paths naturally represented as graph traversals.

- Sales order item to delivery item mapping is a relationship traversal problem
- Broken-flow detection is a missing-edge pattern (`NOT (d)-[:BILLED_AS]->(:BillingDocument)`)
- End-to-end trace is a variable-depth path query

Graph queries are faster to implement and easier to reason about than equivalent multi-join relational SQL for this use case.

### Why ChromaDB for semantic retrieval

RAG context is stored in ChromaDB using local embeddings (`all-MiniLM-L6-v2`) to avoid external embedding rate limits.

- Supports semantic lookup for contextual questions
- Persistent on-disk storage
- Metadata filtering (e.g., `status=DELIVERED_NOT_BILLED`, `type=flow`)

---

## Key Architecture Decisions

1. **Graph-first querying**
  - Structured questions route to Neo4j (source of truth)
  - Reduces hallucination risk compared to LLM-only reasoning
2. **Hybrid retrieval only when needed**
  - `graph` strategy for precise trace/aggregation
  - `rag` strategy for exploratory/contextual questions
  - `hybrid` strategy for partial structure + semantic context
3. **Rule-based classifier for reliability**
  - Deterministic keyword + regex extraction
  - Explicit query categories: `flow_trace`, `broken_flow`, `entity_lookup`, `aggregation`, `contextual`
4. **Guardrails before execution**
  - Out-of-domain queries rejected early
  - Required response message:
  `This system only answers questions about the provided business dataset`
5. **Graceful LLM / quota handling**
  - When Gemini fails or hits rate limits, the pipeline can still return a useful answer from **structured graph rows** and RAG chunks (see `app/query/response.py`)
  - Avoid long blocking retry loops in the default path so the API stays responsive

---

## LLM Prompting Strategy

The generator in `app/query/response.py` uses a constrained system prompt with strict rules:

- Use only retrieved `DATA` context
- Include document/entity IDs
- Use document-flow notation (`->`)
- Be concise and factual
- If insufficient context, clearly state that

Prompting approach:

1. Build structured evidence context from graph rows and/or RAG chunks
2. Inject context into a single generation request
3. Enforce domain answer style through system rules
4. Never ask the model to infer outside retrieved data

---

## Guardrails

Implemented in `app/guardrails/validator.py`.

Behavior:

- Allows in-scope SAP O2C queries (orders, deliveries, billing, payments, products, customers, status, revenue)
- Allows ID-centric queries (e.g., `740506 status`)
- Rejects unrelated prompts (e.g., jokes, weather, politics)

Rejected query response:

`This system only answers questions about the provided business dataset`

---

## API Endpoints

Base: `/api`

- `GET /health`
- `POST /ask`
  - body: `{ "query": "Which orders are delivered but not billed?" }`
  - response includes `details.entity_ids` (e.g. `salesOrder`, `deliveryDocument`, `billingDocument`, `journalEntry`) and `details.evidence` for the UI to focus the graph
- `GET /graph/subgraph`
  - query params (optional; at most one “focus” id is used; priority in the client is sales order → delivery → billing → journal):
    - `limit` — sample size for the overview slice (default `220`, max `1200`)
    - `sales_order`, `delivery_document`, `billing_document`, `journal_document`
  - returns JSON: `nodes`, `edges`, `highlightNodeIds`, `highlightEdgeIds`, and `meta`
  - **Behavior:** always merges a **random overview** subgraph (`MATCH (n)-[r]->(m) … LIMIT`) with the **focused O2C chain** when a focus id is supplied, so the canvas stays populated while the answer path is visually emphasized
- `GET /flow/sales-order/{sales_order}`
- `GET /flow/delivery/{delivery_document}`
- `GET /flow/billing/{billing_document}`
- `GET /flow/broken`

---

## Streamlit UI (`streamlit_app/app.py`)

- **Layout:** wide two-column page — **graph** (~~4/5 width) and **chat** (~~1/5), top bar “Mapping / Order to Cash”.
- **Graph:** `st.components.v1.html` embeds **vis-network**; clicking a node opens a floating **detail card** (properties, connection count). After load, a primary node (prefer **JournalEntry** when on the highlighted path) can be auto-selected to show its card.
- **Styling:** focused path uses stronger blue nodes/edges; overview edges stay lighter so the full graph remains visible.
- **Chat:** messages are HTML-rendered; the composer is a bordered block with a status line and **Send**; submitting calls `POST /ask` and updates `session_state.focus` from `details.entity_ids` (with a fallback to journal IDs in `evidence` when needed), then the left panel refetches `/graph/subgraph` with the new focus.

**Requirements:** the FastAPI server must be running at `http://127.0.0.1:8000` (see `API_BASE` in `streamlit_app/app.py`). Neo4j must contain data seeded via `scripts.seed_graph`.

---

## Local Run Instructions

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Start Neo4j

```bash
docker compose up -d
```

## 3) Seed graph

```bash
python -m scripts.seed_graph
```

## 4) Seed vectors

```bash
python -m scripts.seed_vectors
```

Expected: `729` chunks stored.

## 5) Run API

```bash
uvicorn app.api.main:app --reload
```

## 6) Run UI

```bash
streamlit run streamlit_app/app.py
```

---

## Example Queries

- `Trace the flow for sales order 740506`
- `Which orders are delivered but not billed?`
- `Which billing documents are not paid?`
- `Show details for customer 310000108`
- `What is the total revenue by customer?`
- Journal-style lookups (exact document / reference ids are handled in the query layer), e.g. *find the journal entry linked to reference …* — the graph can focus the resolved `JournalEntry` when the classifier extracts an id

---

## Verification Notes

Current validated outputs from this environment:

- Graph seeded successfully (1,270 nodes, 1,193 relationships)
- Vector store seeded with `729` chunks
- Broken flow counts:
  - delivered_not_billed: `3`
  - billed_not_paid: `3`
  - ordered_not_delivered: `14`
  - total_broken: `20`
- Guardrail rejection path validated through API

---

## AI Coding Session Logs: 

https://opncd.ai/share/c1gExpME

---

## Environment Variables

Defined in `.env` (see `.env.example` if present):

- `GEMINI_API_KEY`
- Optional: `GEMINI_LLM_MODEL` (override default Gemini model name)
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `CHROMA_PERSIST_DIR`
- `DATASET_PATH`

---

