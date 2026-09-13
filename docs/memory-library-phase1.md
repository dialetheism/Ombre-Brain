# Casper Memory Library Phase 1 — Offline Manual Memory Facade

## 1. Phase 1 objective

Phase 1 defines the smallest independently usable Casper memory-library surface. It is a standalone, fully offline facade that requires an explicit isolated root path and supports only:

- manual creation of Markdown long-term memory;
- exact lookup by library-generated memory ID;
- bounded listing;
- deterministic local lexical/BM25-style search; and
- reconstruction of the facade and reload from disk.

The facade must not require API keys, Provider or OpenRouter access, Gateway runtime, Docker, production infrastructure, old-Ombre, or access to a real user memory corpus.

This document is a design and acceptance contract. It does not claim that the proposed facade or its tests already exist or pass.

## 2. Non-goals

Phase 1 explicitly excludes:

- Gateway or chat-client integration;
- automatic chat ingestion;
- automatic promotion from `raw_events` into long-term memory;
- embeddings, reranking, vector databases, or graph diffusion;
- dehydration, long-text digest, or model-generated tags;
- Persona, portrait, reflection, Dream, reminder, moment, node, edge, or word-map behavior;
- prompt-cache behavior;
- MCP or HTTP server startup;
- import workers, Bridge workers, scheduled jobs, or automatic writes;
- permanent deletion;
- use, migration, or validation of a real user memory corpus;
- inherited real config or environment state;
- Provider/OpenRouter calls or any other network access;
- Gateway, Docker, deployment, restart, production, or old-Ombre work.

## 3. Trust and safety boundaries

The Phase 1 facade must fail closed:

1. Construction requires an explicit absolute root path. There is no implicit root and no fallback to the repository's `./buckets` directory.
2. The facade must not call `utils.load_config()` or read `config.yaml`, a runtime config, `.env`, shell history, ignored config, a real memory corpus, or host Provider environment variables.
3. The facade must not import `server.py` or `gateway.py` and must not initialize any network client.
4. Its configuration surface must not accept URLs, tokens, keys, Provider settings, upstream settings, or model-routing settings.
5. Every constructed or resolved child path must be proven to remain inside the explicit root with `Path.relative_to()` or `os.path.commonpath()`. String `startswith()` is not a valid containment check.
6. Validation must reject path traversal, absolute child-path overrides, sibling-prefix confusion, and symlink escape.
7. Validation must reject the repository root, known real bucket or state roots, production paths, and known old-Ombre paths.
8. Test and demo directories must be created and owned by that test or demo. Cleanup may remove only the exact owned directory after containment and ownership checks.

## 4. Data model

The facade should expose a `MemoryRecord` containing:

| Field | Phase 1 rule |
| --- | --- |
| `id` | Library-generated and opaque. The caller cannot select it. It must contain no path separator, `..`, or control character. |
| `layer` | Phase 1 writes only to `dynamic`. Other layer directories do not expand the write scope. |
| `title` | Non-empty UTF-8 text, sanitized, no more than 80 characters, and never used as an unchecked path. |
| `body` | Non-empty UTF-8 Markdown. |
| `tags` | Strings only; stripped, deduplicated, and retained in stable order. |
| `created_at` | Library-generated, timezone-aware ISO-8601 timestamp. |
| `updated_at` | Library-generated, timezone-aware ISO-8601 timestamp. |
| `provenance` | Must include `source=phase1_manual`. An optional `source_id` is a short, non-path identifier and is never dereferenced. |
| `archived` | Derived from storage location and compatible metadata, not maintained as a separate drifting source of truth. |

The serialized Markdown/frontmatter representation must be sufficient to reconstruct every Phase 1 field without consulting a database or cache.

## 5. Persistence contract

Markdown bucket files are the only Phase 1 source of truth. Initial writes are restricted to:

```text
<explicit-root>/buckets/dynamic/.../*.md
```

The `archive`, `permanent`, and `feel` directories may exist as structural directories, but the first code patch must not write memories to them. Phase 1 must not create or treat any of the following as source of truth:

- SQLite databases or JSONL stores;
- embedding or dehydration caches;
- moment, node, edge, word-map, or recall-diagnostic stores;
- raw-event stores;
- Persona, portrait, reminder, Dream, or reflection state;
- runtime config or import state.

Phase 1 excludes `gateway_state.db`. Current source code places `gateway_state.db` under `buckets_dir`, while at least one deployment document describes `/state/gateway_state.db`. Phase 1 must document this drift but must not silently move or migrate the database. A future `state_dir` location may be preferable, but any change requires a separate compatibility, backup, migration, and rollback design.

The minimum backup unit is the complete `<explicit-root>/buckets` directory. Phase 1 exposes no delete API and defines no permanent-delete or tombstone path.

## 6. Minimal facade

A later code patch should introduce an independent module named `memory_library.py` with a narrow public surface:

```python
class MemoryLibrary:
    def __init__(
        self,
        root: Path,
        *,
        allow_existing_nonempty: bool = False,
    ) -> None: ...

    def validate_paths(self) -> PathValidation: ...

    def create(
        self,
        title: str,
        body: str,
        tags: list[str] | None = None,
    ) -> MemoryRecord: ...

    def get(self, memory_id: str) -> MemoryRecord | None: ...

    def list(
        self,
        *,
        archived: bool = False,
        limit: int = 100,
    ) -> list[MemoryRecord]: ...

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        archived: bool = False,
    ) -> list[SearchResult]: ...
```

The first facade patch must not expose update, delete, merge, touch, auto-grow, raw-event ingestion, Provider operations, or Gateway rendering.

`archive(memory_id)` and `restore(memory_id)` may be specified later as a paired, conditional interface. They must not be included in the first code patch without a separate review because the existing archive move may not be failure-atomic. Archive support requires isolated failure and restoration tests first.

## 7. Recall behavior

Phase 1 recall is local lexical/BM25-style recall only:

- Searchable content is limited to title, tags, domain or other path-safe metadata, and Markdown body.
- Embeddings, rerankers, Provider calls, graph diffusion, and time/emotion/importance weighting are disabled and must not be constructed.
- Search is read-only and must not update `last_active`, `activation_count`, timestamps, files, or derived stores.
- An empty query returns an empty list.
- `limit` is bounded to the inclusive range `1..100`.
- Archived records are excluded by default.
- Results sort deterministically by lexical score descending and then memory ID ascending.

The facade must not directly expose the current full `BucketManager.search()` behavior if that path mixes time, emotion, or importance weights. A later implementation may reuse side-effect-free enumeration such as `list_all()` and deterministic term scoring such as `calc_topic_scores()`, provided the facade itself enforces its threshold, ordering, limit, and read-only contract.

## 8. Isolation model

The expected isolated layout is:

```text
<root>/
  buckets/
    dynamic/
    permanent/
    archive/
    feel/
  state/
```

Only `buckets/dynamic` is an initial write target. The following rules apply:

- `root` must be absolute.
- `buckets_dir` and `state_dir` must resolve inside `root`.
- If `root` already exists and is non-empty, construction fails by default. Access requires explicit `allow_existing_nonempty=True` plus the same containment and prohibited-path validation.
- The facade never defaults to repository `./buckets` and never discovers a real corpus automatically.
- Tests use a unique owned temporary root for each case.
- Cleanup removes only the exact owned temporary root after path containment and ownership are validated; it must not use broad globs or delete an unowned path.

## 9. Offline configuration contract

Phase 1 uses a narrow in-process settings object, not the project's full YAML loader. Its conceptual shape is:

```yaml
mode: offline_phase1
root: <explicit absolute isolated root>
buckets_dir: <root>/buckets
state_dir: <root>/state
network_allowed: false
inherit_environment: false
load_config_file: false
load_runtime_config: false
matching:
  fuzzy_threshold: 50
  max_results: 5
scoring:
  topic: 1
  content: 1
  emotion: 0
  time: 0
  importance: 0
wikilink:
  enabled: false
```

This block documents an in-process contract; it is not an instruction to create or load a YAML file.

The validator must reject:

- `api_key`, `api_keys`, tokens, or secret-bearing fields;
- URLs or base URLs;
- upstream, Provider, or model-routing configuration;
- env-file or runtime-config paths;
- Gateway configuration;
- enabled embedding, reranker, dehydration, Persona, reflection, portrait, or Dream features;
- automatic scheduling or automatic writes; and
- real-corpus, production, or old-Ombre paths.

An empty credential is not sufficient proof of offline behavior. Provider-capable modules and network clients must not be constructed at all.

## 10. Module reuse strategy

Later implementation may reuse narrowly reviewed, side-effect-safe pieces:

- `BucketManager` Markdown read/write structure;
- `list_all()`;
- `get()`;
- `calc_topic_scores()` only if deterministic and side-effect-safe under the facade contract;
- metadata normalization from `memory_metadata.py`;
- layer constants and normalization from `memory_layers.py`;
- `sanitize_name()`;
- `now_iso()`; and
- strengthened path helpers that perform real containment checks.

Phase 1 must avoid importing or constructing:

- `server.py`;
- `gateway.py`;
- `load_config()`;
- `Dehydrator`;
- `EmbeddingEngine`;
- `RerankerEngine`;
- `RawEventStore`;
- `ImportEngine`;
- `MemoryWriteGate`;
- `PersonaStateEngine`;
- `ReflectionEngine`;
- `DailyPortraitMaintainer`;
- `DreamEngine`;
- decay, moment, node, edge, or word-map systems; and
- runtime scripts or workers.

Reuse is subordinate to the Phase 1 safety contract. If an existing helper has import-time side effects, implicit paths, writes, or network-capable construction, the facade must not import it merely to avoid duplicating a small pure function.

## 11. Later test plan

Tests are future work and must operate only in unique, test-owned temporary roots. The later test suite should verify:

1. Creating one dynamic memory produces exactly one legal Markdown bucket file.
2. A newly constructed facade reloads the record from disk.
3. `get(id)` returns the same core fields.
4. A related lexical query returns the record.
5. An unrelated query returns an empty result.
6. `list()` defaults to active dynamic memories only.
7. Sorting and limits are deterministic.
8. Path traversal, absolute child override, sibling-prefix paths, and symlink escape are rejected.
9. Malformed frontmatter is skipped or produces a fixed error without overwriting the source file.
10. `server.py` and `gateway.py` are not imported.
11. No DB, JSONL, runtime-config file, cache, or Provider client is created.
12. Socket and HTTP entry points are monkeypatched to prove zero network calls.
13. The real corpus path is neither read nor modified.
14. Repository files remain unchanged.

Archive/restore tests belong to a separate later change and must cover:

- archive followed by restore;
- destination conflict that fails closed;
- simulated move failure without half-archived metadata or location; and
- absence of any permanent-delete path.

## 12. Phase 1 acceptance criteria

Phase 1 is accepted only after a later implementation and isolated test task proves all of the following:

- The facade is independent and does not import Brain or Gateway runtime entrypoints.
- An explicit isolated absolute root is required.
- Markdown files are the only source of truth.
- `create()`, `get()`, `list()`, and `search()` work within the agreed surface.
- Reconstructing the facade reloads records from disk.
- Lexical hit, lexical miss, deterministic sorting, and bounded limits work.
- Path escape and prohibited-root access are rejected.
- No delete operation exists.
- No Provider, OpenRouter, Gateway, Docker, production, or old-Ombre path is used.
- No real secret, inherited real config, or real memory corpus is used.
- Network-call count is zero.
- Tests operate only inside exact owned temporary directories.
- No unnecessary derived database, JSONL, cache, or runtime state is generated.

## 13. Recommended implementation sequence

Keep each future change independently reviewable:

1. **Review and commit this specification.** Make no code or config change in the same patch.
2. **Harden path containment and add the minimal facade.** Add `memory_library.py` with only `validate_paths()`, `create()`, `get()`, `list()`, and `search()`; do not import runtime entrypoints.
3. **Add isolated regression tests.** Cover persistence reload, deterministic lexical recall, path containment, zero network, zero derived state, and real-corpus non-access.
4. **Design and test failure-safe archive/restore separately.** Add neither operation until atomicity, conflicts, restoration, and no-delete behavior are proven.
5. **Consider an ingestion caller only after Phase 1 acceptance.** Any manual CLI, Gateway, chat, or automatic ingestion integration requires a separate scope, security review, and authorization.

The first code patch after this document should therefore be the path-safety and minimal-facade patch, not a Gateway integration, provider feature, persistence migration, or archive implementation.

## 14. Claims not made

This specification does not claim:

- that the current real Casper memory library is usable;
- that a real memory corpus has been read, verified, backed up, migrated, or modified;
- that Gateway automatic retrieval or context injection is connected;
- that automatic chat memory is available;
- that embeddings, reranking, vector search, graph diffusion, or Provider-backed behavior is available;
- that Persona, portrait, reflection, or Dream behavior is available;
- that persistence migration, recovery, backup restoration, or `gateway_state.db` relocation is verified;
- that Docker, deployment, restart, production, or old-Ombre safety is established;
- that archive/restore is safe or available in the initial facade;
- that Phase 1 implementation exists; or
- that any Phase 1 test has passed.
