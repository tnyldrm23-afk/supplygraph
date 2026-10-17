# Local LLM and query guardrails

## Actual execution path
`POST /api/ask` -> Ollama `/api/chat` with Qwen 2.5 1.5B -> intent/parameter selection -> constrained template generation -> structured
`{intent,cypher,parameters}` -> whole-template validation -> typed identifier and
limit checks -> Neo4j bounded transaction -> result/evidence envelope.

The model generates Cypher by selecting and reproducing complete reviewed query
templates. This intentionally trades expressiveness for a defensible Level 2
NL-to-Cypher surface. It is not an unrestricted text-to-database system. Questions
outside suppliers, product provenance, downstream exposure and single-source
bottlenecks should generate an unsupported intent and be rejected.

## Enforcement (not just prompt advice)
- Only four reviewed intent/query pairs can execute.
- The full generated Cypher, after whitespace normalization only, must equal the
  matching template. Added UNION, DELETE, procedures, comments or extra clauses fail.
- Parameters must match the intent's exact key set; no extra keys.
- `limit` is an integer 1–100, depth is an integer 1–6. Booleans do not count as integers.
- Organization and product IDs must exist in the actual snapshot.
- Supplier search strings are data parameters, not interpolated Cypher.
- A preliminary denylist rejects obvious write requests before even invoking the
  model. It is convenience and defense-in-depth; the full-template allowlist is
  the security boundary. Regex alone is not the security mechanism.
- One model question can generate at a time; concurrent requests receive an explicit busy response.
- Neo4j reads have a transaction timeout. LLM HTTP requests have bounded timeout.
- The local API binds host ports to loopback. Neo4j Community uses the configured
  application account; no unavailable Enterprise read-only RBAC role is claimed.
- No API endpoint accepts arbitrary Cypher or exposes ingestion writes.

## Reliability and evidence
The LLM creates a query plan. Numerical disruption summaries are generated
programmatically from validated results and the deterministic solver. The response
shows the executed Cypher, parameters, actual graph records, model identity and
observed/assumed labels. No free-form model explanation can invent mitigation
capacity or promote scenario assumptions to empirical supplier facts.

Unknown identifiers, unsupported intents and malformed output are rejected with
422; a missing model/service returns 503. A missing LLM is never silently replaced
by a keyword router or a canned answer. A small model may occasionally generate a
mismatched intent/template pair: rejection is the correct outcome, not execution.

## Evaluation
Unit tests exercise injected clauses, malformed JSON shapes, invalid identifiers,
extra fields, boolean-as-integer values, unbounded depth/results, incorrect
intent/query pairing and unavailable model handling. Test HTTP doubles are labeled
as such and are not counted as real-model evidence. `scripts/evaluate_assistant.py`
records actual end-to-end questions separately in `reports/llm-evaluation.json`.
The live demonstration includes a successful graph request and a rejected write.
