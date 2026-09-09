# Casper Ombre deployment design

## Status and scope

This bundle has passed C2C1 portable-toolchain, patched helper test, Kotlin
compile, debug APK assembly, artifact inspection, and Ombre decay-fixture
validation. C2D2B additionally passed a private-device, localhost-only session
test: two conversations stayed stable and isolated across multiple turns, app
restart, and the fastest legal client-limited switch; a provider without the
dynamic header emitted no session header; and a static header was unaffected.
No VPS, Cloudflare, OpenRouter, or model provider was contacted. The technical
session blocker is resolved. C2E freezes a production-safe, separately packaged
client design, but no production signing key or release APK exists yet.

Frozen source/build baseline:

- repository: https://github.com/Yinglianchun/Ombre-Brain.git
- branch: main
- SHA: 284c9c7b0e51a0ba0032c7028f705d72458cb304

This SHA is the frozen reviewed source/build baseline for this recorded bundle.
It is not the current local repository HEAD after the C2G10 construction-line
commits.

The intended VPS checkout root is /srv/casper-ombre. The bundle remains at
/srv/casper-ombre/casper-deploy, while the two persistent paths are:

- /srv/casper-ombre/data
- /srv/casper-ombre/state

Both containers mount both paths at /data and /state. They must always be
backed up and restored as one matched pair.

## Architecture and namespace

The Compose project is casper-ombre. It creates:

- casper-ombre-brain on casper-ombre-net
- casper-ombre-gateway on casper-ombre-net

Brain runs python server.py with streamable-http on container port 8000. It has
no host port publication or public route. Its MCP and Dashboard routes are
intended only for same-network services or host administrators with Docker-
network access; they are not treated as a public endpoint. This placement is
defense-in-depth only and does not replace application-layer authentication.

The Dashboard-to-Gateway admin bridge is initially disabled: Brain does not
receive OMBRE_GATEWAY_ADMIN_URL or the Gateway Bearer credential. This keeps
the client secret out of Brain, but Dashboard Gateway hot-update and cross-
service debug-injection controls are unavailable. Enabling that bridge later
requires a separate secret-boundary review.

Gateway runs python gateway.py on container port 8010. The only host
publication is 127.0.0.1:18202:8010. No service binds a Casper port on
0.0.0.0. The future public route is outside C2.

Gateway and Brain are independent processes. Normal Gateway chat does not call
Brain over HTTP; both processes directly use the same /data and /state.
Consequently, Gateway does not declare a false startup dependency on Brain.

## Image and source strategy

Dockerfile.production is the frozen local build recipe for the reviewed Casper
source state. The service commands remain:

- BRAIN_COMMAND=["python","server.py"]
- GATEWAY_COMMAND=["python","gateway.py"]

The production Dockerfile intentionally omits the upstream Dockerfile's
/app/buckets VOLUME, runs as UID/GID 10001, records the source SHA in OCI
metadata, pins the verified linux/amd64 Python child-manifest digest, and
installs the frozen production lock with hash enforcement. Compose uses
pull_policy never and does not reference a p0luz image. The pull policy prevents
an accidental registry fallback. The frozen deployment path must use the
already-built, identity-verified local candidate; it must not run a Compose or
remote build during deployment.

The Ombre decay fix is intentionally not applied inside the Dockerfile. The
selected audit strategy is:

1. start from a clean checkout at the frozen upstream SHA;
2. verify the patch artifact SHA-256 against `PATCH-MANIFEST.yaml`;
3. run `git apply --check --index --whitespace=error-all` and reject any offset,
   fuzz, whitespace error, or unexpected target;
4. apply the patch with `git apply --index --whitespace=error-all`;
5. require the staged file set and post-apply file digests to match the patch
   manifest, with no unstaged source change; and
6. build and label the image with upstream SHA plus patch SHA-256.

This is Option 1 (clean frozen checkout, verified patch, then build). It keeps
the source baseline and patch provenance separately visible and makes apply
failure a hard stop. Applying inside the Dockerfile would hide the intermediate
tree and add build-tool complexity. A Casper Git branch can later package the
same reviewed result, but it would require a separate commit/rebase lifecycle;
C2B creates no commit.

The production supply-chain inputs are now statically frozen and validated:

- Dockerfile.production uses the verified linux/amd64 Python child-manifest
  digest.
- requirements.production.linux-amd64-py312.lock.txt contains the frozen,
  hash-complete production dependency graph.
- constraints.production.txt is the current production constraint file; it
  records the compatibility pin for mcp. The older names
  requirements.production.txt and constraints-production.txt are not current
  canonical filenames unless a future note marks them historical.

### No-build dependency lock contract

Operators should treat `requirements.production.linux-amd64-py312.lock.txt`
as the canonical production install input and `constraints.production.txt` as
a minimal, subordinate source or regeneration overlay, not a complete
production install input unless a future authorized documentation update says
otherwise. The older names `requirements.production.txt` and
`constraints-production.txt` are non-current unless explicitly historical.

The lock is scoped to `linux/amd64` plus CPython 3.12 / `cp312`.
`Dockerfile.production` installs that platform lock with `--require-hashes`.
Current static inspection and the manifest record dependency count and hash
completeness, but that is not dependency install proof, Docker build proof, or
runtime proof. Preserve `--require-hashes` and full hash coverage.

Future lock regeneration requires a separate explicitly authorized
resolver/network stage naming the exact environment, toolchain pins, package
index targets, files allowed to change, and stop conditions. Review lock
changes as text before any install or build, including package additions or
removals, version changes, hash deltas, dependency count, sdist exceptions,
Dockerfile references, and manifest or documentation updates. Registry
freshness, yanked-package status, and security checks require separate
explicit network authorization.

This no-build dependency lock contract does not prove Docker build success,
dependency install success, Gateway runtime readiness, or production readiness.
Old Ombre remains out of scope and must not be touched.

### Base image digest refresh authorization envelope

This future human authorization envelope is for base image digest refresh /
registry freshness verification. It does not authorize registry contact,
Docker pull/build/image inspection, or any Docker action by itself, and it does
not imply that fresh registry validation has already occurred.

- Current tracked Dockerfile base image:
  `python@sha256:a249c9f47e05708dd367f3fe8ada03cf347390fad66fb8b0518c0ef55ae3cb84`
- Original reference: `python:3.12-slim`
- Platform: `linux/amd64`
- Multi-arch index digest:
  `sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217`
- Target child manifest digest:
  `sha256:a249c9f47e05708dd367f3fe8ada03cf347390fad66fb8b0518c0ef55ae3cb84`
- Config digest:
  `sha256:72a58063c7563c5c64052da2becebce3f25b60055cb351b668c4e2df9153702c`
- CPython/version/ABI: `3.12.14`, `cp312`
- Current status: `FROZEN_STATIC_VALIDATED`
- Meaning: static/frozen provenance only, not fresh registry validation.

Default denied posture: registry contact `NO` unless separately and explicitly
authorized later; Docker pull `NO`; Docker build `NO`; Docker image inspection
`NO` unless separately and explicitly authorized later; Docker tag creation
`NO`; Docker run / Compose `NO`; dependency install / pip / resolver `NO`;
compose.yaml mutation `NO`; manifest.yaml mutation `NO` unless a later
post-evidence patch is explicitly authorized; docs mutation `NO` unless a later
post-evidence patch is explicitly authorized; deploy/restart/runtime validation
`NO`; Gateway/OpenRouter/production contact `NO`; old Ombre `FORBIDDEN`.

Future phase split: static preflight observes only Git and tracked files, with
no network, Docker, production, or old-Ombre contact; optional registry
freshness lookup is allowed only with explicit future network/registry
authorization naming registry source, image reference, platform, and stop
conditions; optional digest comparison is allowed only after lookup evidence
exists; optional docs/manifest patch planning is readonly and only for changed
or newly recorded evidence; optional post-evidence docs/manifest patching needs
separate mutation authorization and makes no build/runtime claim; Docker
pull/build/runtime/deploy phases remain out of scope unless separately
authorized much later.

Required future evidence: exact human authorization text, observed Git preflight
state, current tracked base image reference, current tracked digest, platform
scope, CPython/version/ABI scope, registry source queried if later authorized,
fresh registry digest result if later authorized, comparison result against the
tracked digest, whether the digest changed, whether a docs/manifest patch is
needed, no Docker pull/build/image inspection unless separately authorized, no
dependency install/pip/resolver unless separately authorized, no
runtime/production contact, no real secret leakage, old-Ombre no-touch
statement, and a redacted final report.

Abort on HEAD drift, dirty worktree, remote mismatch, branch/tracking mismatch,
ahead/behind mismatch, ambiguous base image reference, ambiguous tracked digest,
ambiguous platform scope, ambiguous registry source, registry contact without
explicit future authorization, Docker pull/build/image inspection without
explicit future authorization, Docker tag creation without explicit future
authorization, package registry/pip/resolver/install without explicit future
authorization, compose/manifest/docs mutation without explicit future
authorization, deploy/restart/runtime/Gateway/OpenRouter/production contact,
old-Ombre involvement, real secret exposure risk, or unexpected output that
would require continuing anyway instead of stopping.

Documenting this envelope does not prove fresh base image registry validation,
Docker pull, Docker build freshness, Docker tag creation, Docker image
inspection, Gateway candidate image creation or observation, registry contact,
image push, deploy, restart, runtime verification, Gateway runtime readiness,
OpenRouter behavior, production readiness, dependency install, pip/resolver
execution, tests/scripts/hooks, old-Ombre safety proof, or real secret
validation.

These local facts do not make deployment ready. The candidate remains local,
has not been run, registry-pushed, transferred, loaded on a target host, or
deployed. The base-image digest and dependency lock are static/frozen
provenance only; they are not fresh registry validation, fresh Docker build
success, dependency-install success, Docker ignore behavior validation, Gateway
runtime readiness, or production readiness. A frozen Git SHA or OCI revision
label alone is still not image identity.

## Runtime configuration precedence

The source applies configuration in this order:

1. built-in defaults
2. /app/config.yaml
3. /state/config.runtime.yaml
4. supported environment-variable overrides

The same read-only config file is mounted into both services. Both use the same
/state/config.runtime.yaml. On a fresh deployment, preflight requires that
runtime override to be absent. On a restore, it is part of the state backup and
must be reviewed because it can override the static baseline.

The image root filesystem is read-only. Dashboard/config persistence may only
use the source's /state/config.runtime.yaml fallback; attempts to write
/app/config.yaml or /app/.env are intentionally not supported. A later
authorized live-host stage must verify
that /data and /state are owned by UID/GID 10001 with an owner-write mode
before the first start.

No populated environment file belongs in Git. The future root-only secret file
is /etc/casper-ombre/casper.env with root:root mode 0600. Compose is intended to
be invoked with that path via --env-file.

Preflight reads that file only with a strict NAME=nonempty-value parser and
prints SET/MISSING statuses. It does not source shell code or print values.
Alternatively, already-exported variables take precedence. Preflight also
rejects any untracked path outside casper-deploy, because the frozen build
context may otherwise include source that is not represented by HEAD.
Run it as root in that later stage so it can read only metadata/SET status from the root-only
secret file and inspect Docker, Nginx, systemd, and port references. If Docker
daemon read access is unavailable, the collision audit fails closed.

## OpenRouter and GPT-5.4

Gateway uses the source's OpenAI-compatible /v1/chat/completions path:

- protocol: openai
- base URL: https://openrouter.ai/api/v1
- public model alias: casper-gpt-5.4
- actual upstream model: openai/gpt-5.4
- API key environment: CASPER_OPENROUTER_API_KEY

The actual OpenRouter model identifier was reverified against OpenRouter's
official model catalogue during C2A and is frozen as openai/gpt-5.4. This does
not authorize a model request; C2A sent no inference traffic.

The OpenAI-to-OpenAI path deep-copies the client request. It changes the
upstream model, injects memory context/messages, normalizes stream to a boolean,
and applies configured prompt-cache hints. It does not use a request-field
allowlist, so reasoning, verbosity, tools, tool_choice, parallel_tool_calls,
max_completion_tokens, response_format, service_tier, and stream_options are not
intentionally removed. Streaming bytes are relayed as SSE; non-stream JSON is
returned as the upstream body.

This is source-level compatibility, not provider acceptance. A future
credentialed end-to-end stage must validate
OpenRouter behavior for all required fields without exposing credentials.
Current code also has no configuration mechanism for optional OpenRouter
HTTP-Referer or X-Title headers.

## Gateway authentication

The client credential is CASPER_OMBRE_GATEWAY_TOKEN in the root-only env file.
Compose maps it to the actual source key OMBRE_GATEWAY_TOKEN. Missing
configuration produces a 503; a missing or invalid Bearer credential produces
401. A Cloudflare route is not a replacement for this authentication.

Gateway /health is intentionally unauthenticated in current source and returns
non-secret model/base readiness metadata. It is safe for container health
checks, but the future reverse-proxy stage must decide whether it should expose that
path publicly.

## Brain internal hook, setup, and MCP authentication

The C2G10E local source patch adds explicit application-layer boundaries. It is
included in the reviewed local candidate recorded below, but that candidate has
not been run, transferred, or deployed. Before a patched Brain deployment:

- `CASPER_INTERNAL_HOOK_TOKEN` is the external secret placeholder mapped by
  Compose to `OMBRE_INTERNAL_HOOK_TOKEN`. Its real value must remain outside
  Git, must never be printed or rendered into documentation, and must not reuse
  `CASPER_OMBRE_GATEWAY_TOKEN`.
- `OMBRE_DASHBOARD_SETUP_ENABLED` must be explicitly `false` in production.
  Existing password-hash, completion-lock, or pending-reservation state keeps
  setup closed; any first-setup window requires separate authorization.
- `OMBRE_MCP_AUTH_REQUIRED` must be explicitly `true`. A missing authentication
  provider fails closed, and Host/private-network placement is not a substitute
  for authentication.
- `OMBRE_MCP_MUTATIONS_ENABLED` must be explicitly `false`. Enabling mutations
  requires a separate authorization, and no write token belongs in MCP tool
  arguments or model/tool context.

Credential preflight may report only `SET` or `MISSING`. It must not print
values, value lengths, Authorization headers, environment dumps, shell-expanded
values, or rendered Compose output containing secrets.

## Session and prompt-cache policy

X-Ombre-Session-Id is a mandatory client capability even though current source
cannot enforce its presence. The configured default
__MISSING_X_OMBRE_SESSION_ID__ is only a visible failure sentinel.

Required client behavior:

- every logical chat window gets a unique stable session ID;
- the same window keeps that ID across all its turns;
- a new window gets a new ID;
- unrelated windows never share an ID;
- the client does not send an unrelated prompt_cache_key.

Session identity controls successful-round counters, recent-context cooldown,
session dedupe and hard-exclude state, raw-event conversation/session identity,
per-session Persona affect, reminder marks, turn/debug snapshots, reasoning
continuation cache, and the Gateway-generated prompt_cache_key. Conversation
turn rows retain the session ID. The Just Now selector is intentionally
cross-window for one profile and therefore is not isolated to the current
session; the session ID labels the selected source window instead.

The initial Just Now policy is
`KEEP_PROFILE_GLOBAL_RECENT_CONTINUITY`. It is deliberately profile-global,
not session-filtered: only an explicit just-now query triggers it, it looks back
six hours, examines at most 20 candidate turns, and injects no more than five
selected turns within a 420-character budget. This can carry very recent text
from another window, which is the intended “换窗口后仍记得刚才” behavior. It is
a separately labelled short-term context block, not a bucket/moment direct
factual seed. Session counters, cooldowns, raw-event identity, and Persona
session affect still depend on distinct `X-Ombre-Session-Id` values.

The header also determines whether Gateway considers a request the first
successful round of a new session and can therefore emit a handoff-tool hint.
It does not make every handoff section session-private: Portrait, self-anchor,
anchors, and recent life continuity are profile/global material. Care memos can
filter by session only when a session_id is actually passed to breath; the
Gateway hint itself does not copy the HTTP header into MCP tool arguments.

Prompt cache is configured as openai so Gateway supplies the Ombre session ID
as prompt_cache_key via setdefault. The bundle omits prompt_cache_retention and
does not add prompt_cache_breakpoint or prompt_cache_options. The client must
not provide an unrelated prompt_cache_key because setdefault preserves a
client-provided value. OpenRouter documents prompt_cache_key as a fallback
sticky-routing key and OpenAI GPT-5.4 uses automatic prompt caching, but cache
hits still require a separately authorized credentialed end-to-end measurement.

### RikkaHub C2A source audit

The official repository was audited read-only at commit
8dc3ebce3f422a422013097447234e4a97db4210. RikkaHub stores a stable random UUID
on each Conversation and keys ConversationSession by that ID. However:

- model/provider custom headers are stored as literal name/value strings;
- the UI saves the literal value with no conversation variable expansion;
- GenerationHandler builds TextGenerationParams without a conversation ID;
- ChatCompletionsAPI applies the resulting header list literally;
- the request interceptor is a no-op; and
- the prompt-template variables are message, role, time, date, and datetime,
  not conversation_id/chat_id/session_id.

Therefore static custom headers are supported, but a static
X-Ombre-Session-Id would be shared by every RikkaHub conversation. Dynamic
per-conversation X-Ombre-Session-Id is UNSUPPORTED in the audited upstream
request path.

C2B selected Option D and provides a two-file patch artifact. C2C1 applied it
exactly to the frozen official source with zero offset/fuzz, passed a
patched-source data-flow review, ran 10/10 targeted resolver tests, compiled the
debug Kotlin variant, and assembled a debug APK. It passes the existing
`Conversation.id` into `GenerationHandler` and expands only an
explicit custom-header value `{{conversation_id}}`. It does not add an Ombre
header implicitly, so ordinary providers are unchanged. Existing static values
remain literal; an unknown exact `{{variable}}` fails before network I/O. Full
design and runtime cases are in `RIKKAHUB-SESSION-PATCH.md`.

Session solution comparison:

| Option | Isolation and continuity | Required change | Result |
|---|---|---|---|
| A: derive from an identifier already in the request | Safe only if a stable collision-resistant conversation ID is already sent | None in theory | Not currently available; the audited request body/header layer does not receive Conversation.id |
| B: thin adapter/proxy | Stable only if the client supplies a reliable ID | New proxy plus a client-visible identifier | Cannot infer a missing ID; message hashing is collision-prone and not an acceptable identity boundary |
| C: minimal Ombre Gateway patch | Same limitation as B | Fork maintenance plus a reliable request property | Gateway cannot reconstruct an ID absent from the request; not independently sufficient |
| D: minimal RikkaHub enhancement | Same conversation UUID stays stable; each new/forked conversation already gets a new UUID | Pass Conversation.id to custom-header template resolution | Selected; exact apply, 10/10 helper tests, Kotlin compile, debug APK build, and C2D2B private-device runtime validation passed |

Random-per-request IDs and hashes of the current user message are explicitly
forbidden because they break multi-turn continuity. C2D2B resolved the technical
session blocker without using the configured default sentinel. The validated
artifact remains a debug-signed, distinct-package test client, not a frozen
long-term production client.

### Portable RikkaHub build provenance

C2C1 used an external portable toolchain only: Temurin JDK 17.0.20 launched the
repository Gradle wrapper 9.5.0 with `--no-daemon`; the frozen daemon criteria
selected JetBrains JBR 21.0.10 while Java/Kotlin bytecode remained targeted at
17. Android inputs were `platforms;android-37.0`, Build Tools 36.0.0, NDK
28.2.13676358, and CMake 3.22.1. The user accepted the Android SDK
license interactively; Codex did not auto-accept it. No permanent PATH,
JAVA_HOME, ANDROID_HOME, Android Studio, registry, or system package-manager
change was made.

The official repository ignores `google-services.json`. The external debug
copy therefore used a non-production placeholder configuration containing no
real credential. The selected arm64 debug APK is `me.rerere.rikkahub.debug`,
version 2.4.9 (176), SHA-256
`6572928a7fad57cf8bf119a8daf910f37fcdc9966d6cf0d0b80ba4b57a383e27`,
signed with an Android Debug certificate. It is distinct from release package
`me.rerere.rikkahub`, so package identity permits parallel installation. This
artifact was used only for the completed private C2D2B session test; it is not
a publication or long-term production client.

### RikkaHub Casper production client

The long-lived client is frozen as a third, independent package:

- application ID: `me.rerere.rikkahub.casper`;
- display name: `RikkaHub Casper`;
- private callback/shortcut scheme: `rikkahub-casper`.

This ID is distinct from official `me.rerere.rikkahub` and validated debug
`me.rerere.rikkahub.debug`, so Android private data and signatures remain
separate. C2E selected the existing release variant plus a mandatory, verified
build-configuration patch rather than adding a larger product-flavor matrix or
relying on an easy-to-forget command-line application ID override.

The packaging patch SHA-256 is
`af02a95fe468ef592c63601964b98ca3dd11bb43c627d594b76e8c4828eedaf2`.
On a clean frozen RikkaHub copy it applies after the session patch with zero
offset and zero fuzz. It supplies environment-only signing hooks, isolates the
URI scheme, and removes app-level Firebase Analytics/Crashlytics plugins,
dependencies, registrations, and events. Core chat does not require a Firebase
project. ML Kit may retain transitive Firebase-named utility artifacts; those
are not permission to enable Firebase telemetry or use the debug placeholder.
The C2F1 clean-copy release graph confirms Analytics and Crashlytics are absent
and no Google Services project is required.

The reproducibility patch SHA-256 is
`81eb44e39a9fc8a099016870ff382980c459b1510cecb6334fb9281c0f388293`.
It removes `mavenLocal()`, pins the Gradle 9.5.0 distribution checksum, enables
strict Gradle locks, verifies dependency binaries, freezes sqlite-android to a
full commit and AAR digest, and replaces all 45 Web UI ranges with exact
versions. Dynamic selectors are 46 before and 0 after. A second clean-copy
`:app:packageRelease` passed and produced an external, unsigned arm64 APK for
`me.rerere.rikkahub.casper`; no APK or build cache is stored in this bundle.

The production signing key must be user-owned and long-lived, stored outside
Git, this bundle, and the VPS. The four required future build variables are
`CASPER_RIKKAHUB_KEYSTORE_PATH`, `CASPER_RIKKAHUB_KEYSTORE_PASSWORD`,
`CASPER_RIKKAHUB_KEY_ALIAS`, and `CASPER_RIKKAHUB_KEY_PASSWORD`; they must be
present together. C2F1 created none of them.

Provider migration is not a private-database copy. Full backup is an
unencrypted ZIP that can include settings, conversations, files, and other
personal data. Per-provider QR/text sharing exists, excludes models and
conversations, but carries provider secrets in Base64 rather than encryption.
The initial recommendation is therefore to create only the minimum Casper
provider manually; any per-provider share remains a separate user-controlled
secret transfer followed by model recreation.

The complete packaging, signing, Firebase, migration, provenance, dependency,
upgrade, and rollback policy is in `RIKKAHUB-PRODUCTION-CLIENT.md`.

## Initial memory and Persona policy

Automatic chat memory is explicitly frozen to:

RAW_EVENT_RETENTION_POLICY=KEEP_UNTIL_EXPLICIT_POLICY_DEFINED
DAILY_CHAT_MEMORY_MODE=off
AUTOMATIC_MEMORY_INITIAL_MODE=off

Raw user/assistant events still enter /state/raw_events.sqlite after successful
Gateway rounds. They are an archive, not curated factual memory, and have no
automatic TTL. C2 does not authorize automatic deletion.

Persona uses the minimum policy needed for relationship state and per-session
affect continuity:

- persona.enabled=true
- mode=llm
- event_recording_enabled=false
- conflict_nudge_enabled=false
- current_inner_state_interval_rounds=15
- date persona trace disabled
- relationship weather interval disabled

Persona/dehydration thinking_mode is left empty so the helpers do not force a
provider-specific thinking payload before their providers are selected.
Persona still requests provider-native JSON object output; a future end-to-end stage must verify that
the chosen Persona provider supports response_format=json_object.

Persona evaluates only on its configured interval and can expose a bounded
state-change context; it is not a factual-memory source or a second reply
generator. The initial numeric state is deliberately neutral. The Persona
provider remains a required user configuration because enabling the state
engine without a working evaluator would provide no evolving continuity.

NO_EVENT_TRACE is a policy label, not a source config key. It maps to
persona.event_recording_enabled=false and
gateway.date_persona_trace_enabled=false. Persona's global and per-session
state updates still persist, so affect and relationship continuity remain.
The tradeoff is reduced event-level audit evidence and fewer Persona-event
materials for a future Portrait generation; this does not disable handoff or
the core Persona state.

Normal per-turn Portrait injection remains retired in source regardless of the
configured legacy switch. The initial Portrait policy is manual opt-in:

- portrait.enabled=true permits an explicitly authorized manual maintenance;
- auto_enabled=false, auto_initial_enabled=false, and daily_enabled=false stop
  all scheduled/background generation;
- a fresh deployment has no portrait content until a manual generation;
- portrait_state.json persists under /state and handoff reads it whenever it
  exists, even while background generation stays off; and
- handoff returns private context and never writes Casper's final reply.

Reflection, daily impression, Dream, automatic memory, active reminder
injection, query planner, domain sentinel, and semantic rescue remain initially
disabled.

Graph recall and gated memory diffusion remain enabled. Relationship weather
and daily impression layers are excluded from ordinary direct factual seed and
are also not scheduled for interval injection.

Upstream has no auto-resolve switch. The C2B patch adds exactly one key,
`decay.auto_resolve_enabled`, with upstream-compatible default `true`. Casper
sets it explicitly to `false`. The existing hard-coded condition would set
`resolved=true` when an unprotected dynamic bucket has importance <=4 and
last_active/created is older than 30 days; the new guard skips only that update
when disabled. The decay loop still starts immediately and repeats every 24
hours.

This cycle scans active bucket Markdown only. Permanent, feel, pinned, and
protected buckets are skipped. It does not scan moments, raw_events.sqlite,
Persona state, reminders, embeddings, or other SQLite-derived stores. Manual
and automatically created dynamic buckets are not distinguished, so either is
eligible when metadata matches. resolved is a reversible metadata state, not
deletion: the file remains in dynamic storage, ordinary dynamic/direct recall
normally excludes it, explicit old/resolved queries or exact bucket reads can
still find it, and trace(resolved=0) restores normal participation. A separate
score archive, if enabled in a future policy, moves the Markdown file to
archive and can be reversed with activation.

With auto-resolve disabled, no automatic `resolved=true` update is performed.
The patch does not delete/move a memory, change importance, alter explicit
manual resolve/trace operations, touch raw events, or disable score calculation
and the separate archive path. Casper also retains lambda=0.0 and threshold=0.0
as the conservative archive/scoring policy. C2C ran the real patched
`DecayEngine` against isolated fixtures: disabled auto-resolve, upstream-enabled
behavior, importance 5, permanent, pinned/protected, manual resolve, raw-event
isolation, and archive/scoring equivalence all passed. The auto-resolve blocker
is therefore resolved.

`lambda=0` does not make scores age-invariant: `_calc_time_weight()` and the
short-term/long-term weighting branch remain time-sensitive. C2C1 freezes this
as an accepted ranking-only policy:
`ACCEPT_RECENCY_RANKING_WITH_NO_DESTRUCTIVE_MEMORY_MUTATION`. The freshness
factor is not a percentage of memory content or importance. It does not mutate,
resolve, delete, or archive memory, while explicit retrieval remains available.
`threshold=0` continues to prevent score-based archive and
`auto_resolve_enabled=false` prevents the hard-coded 30-day resolve. The
freshness policy blocker is therefore resolved without a third patch.

## Helper model execution

All model inference is remote:

- embedding: remote OpenAI-compatible embeddings API; local SQLite stores
  returned vectors and Python computes cosine similarity;
- reranker: remote provider /rerank API, explicitly disabled initially;
- dehydration/compression/tagging: remote OpenAI-compatible chat API;
- Persona: remote OpenAI-compatible chat API.

No torch, transformers, Qwen weights, embedding model, or reranker model is
loaded on the VPS. Provider model strings are remote API identifiers only.

Each provider has a separate credential by default. Sharing a key may be
technically possible for a compatible provider, but it is not assumed.

## Resources and logs

Regular Compose service-level limits are used rather than Swarm-only deploy
resources:

- Brain: 384 MiB hard, 192 MiB reservation, 0.50 CPU, 128 PIDs
- Gateway: 512 MiB hard, 256 MiB reservation, 0.75 CPU, 128 PIDs
- combined hard memory cap: 896 MiB
- combined CPU cap: 1.25

This leaves headroom on the 1.6 GiB / 2 vCPU VPS and avoids local model loads.
It is a static budget, not a load-test result. A later separately authorized
preflight may verify only the approved Casper resource budget and non-conflict
metadata. It must not inspect old Ombre processes, services, containers, usage,
or status.

Container logs use json-file rotation at 10 MiB times three files per service.
Operators must monitor:

- /state/raw_events.sqlite growth;
- /data and /state filesystem usage;
- container memory/OOM counters;
- log volume.

Recommended alerts begin at 70 percent disk usage, become urgent at 85 percent,
and block writes/deployment at 90 percent until reviewed. No raw-event cleanup
is automatic.

## Health semantics

Brain GET /health reads bucket/edge/engine stats and does not call a memory
operation. Gateway GET /health reads configuration and bucket stats, requires
no Bearer credential, and does not call an upstream model. Compose uses Python
stdlib probes inside each container, so curl is not added to the image.

The operator healthcheck script can probe Gateway on 127.0.0.1:18202 or Brain
inside its container. It never calls an MCP memory tool. These probes prove
local process/application liveness only; they do not prove Gateway Bearer auth,
upstream readiness, provider credentials, or any end-to-end model request.

## C2G10 source identity and no-deploy rollout gate

The reviewed source/build baseline remains HEAD
`284c9c7b0e51a0ba0032c7028f705d72458cb304`. That marker records the
historical C2G10E review baseline, not the current repository HEAD. At the time
of the C2G10E review, the auth hardening existed as a local `server.py`-only
diff of 238 insertions and 24 deletions; it is no longer the current repository
state.

The current Casper construction line is local `main` at
`650efba18da50f1a884e40ec83a5332dae21475c`. The construction-line commits
after `284c9c7` are:

- `bd8c555` Add safe auth-check hook
- `3aa3d83` Add Casper Ombre deploy bundle and restart coverage artifacts
- `c6597ba` Document Casper source identity and static gaps
- `650efba` Add internal hook token secret placeholder

This construction line has been pushed to `myfork/main` at
`https://github.com/dialetheism/Ombre-Brain.git`. `origin` remains
`https://github.com/Yinglianchun/Ombre-Brain.git` as the author/upstream
reference remote, and this record does not state or imply a push to `origin`.
`https://github.com/P0luz/Ombre-Brain` remains historical upstream/original
reference only, not the active installed baseline.

These source identities are review and backup evidence only: they are not a
deployed image identity and do not make current production patched or
production-ready.

The source-only gate below is historical context. Its build and immutable-image
recording steps are complete for the reviewed C2G10L local candidate; they do
not authorize or require another build. Before any later deployment:

1. Record the base HEAD and a stable identity for the reviewed local patch,
   without including secrets.
2. Verify the five C2G10H documentation/configuration files contain the four
   hardened Brain variables and safe production invariants.
3. Provision the internal-hook and MCP authentication credentials through an
   external secret path; record only `SET/MISSING`.
4. Obtain separate authorization for credential presence gating, candidate
   transfer, production deployment/restart, and post-deploy boundary checks.
5. Preserve and verify the already recorded C2G10L candidate image ID and tag;
   do not rebuild, and do not rely on the uncommitted source diff or an OCI
   revision label alone.
6. During post-deploy auth checks, record status and safe metadata only and
   discard response bodies. Do not call chat completions, mutation/admin
   endpoints, or memory-returning hooks in a no-content check.
7. Reconfirm that old Ombre is outside every build, route, restart, validation,
   rollback, and fallback target.

This documentation/configuration patch does not authorize or perform any of
those later actions. Current production remains unpatched until the separately
authorized presence gate, transfer, deploy, restart, and verification stages
complete.

## C2G10L7 frozen Brain-only deployment contract

This section records a local plan only. It authorizes no Docker command, image
export/import, file transfer, SSH, production access, deployment, restart,
Gateway mutation, old Ombre access, or C2G10M execution. C2G10M remains blocked.

### Local candidate identity

The reviewed local-only candidate is:

- tag: `casper-ombre-brain:c2g10l-local-candidate-284c9c7`
- image ID:
  `sha256:dc538274cbd7a33cdc1a23ed75b9719069365e1a75933d51ce51eab595b25cb7`
- repo digest:
  `casper-ombre-brain@sha256:dc538274cbd7a33cdc1a23ed75b9719069365e1a75933d51ce51eab595b25cb7`
- OS/architecture: `linux/amd64`
- local-only: `true`
- run status: `NOT_RUN`
- Docker image/registry push status: `NOT_PUSHED`
- deployed: `false`

This `NOT_PUSHED` field is the Docker image/registry status only. It is not the
Git commit backup status for `myfork/main`.

The current compose.yaml now has Brain separated onto
`casper-ombre-brain:c2g10l-local-candidate-284c9c7`. Gateway remains on
`casper-ombre-source:284c9c7...` and still has a build block. The Gateway does
not yet have a separately recorded immutable Gateway candidate identity.

### Brain/Gateway image identity separation policy

Brain currently has a service-specific local candidate image identity:
`casper-ombre-brain:c2g10l-local-candidate-284c9c7`. That Brain candidate
remains local-only, `NOT_RUN`, `NOT_PUSHED`, and not deployed.

Gateway currently remains source-tagged as
`casper-ombre-source:284c9c7b0e51a0ba0032c7028f705d72458cb304`. It still has a
build block using `casper-deploy/Dockerfile.production` and
`SOURCE_SHA=284c9c7...`. Gateway does not yet have a service-specific immutable
candidate identity.

Future Gateway identity evidence should record the service name, candidate tag,
immutable image ID or digest, source SHA, build evidence, local-only status, run
status, push status, and deploy status. Future compose should reference
distinct immutable Brain and Gateway candidate images only after Gateway
identity exists. The Gateway build block remains an unresolved blocker until a
separately authorized compose, manifest, or Docker patch changes it.

Do not claim tag separation until clean Git state, static compose fields,
manifest and documentation records, exact service-specific tags, immutable IDs
or digests, and source/build provenance all agree. Tag separation planning does
not prove Docker build freshness, Docker tag creation, registry push, deploy,
restart, Gateway runtime readiness, OpenRouter behavior, production readiness,
old-Ombre safety, dependency install, pip/resolver execution,
tests/scripts/hooks, or real secret validation. Old Ombre remains out of scope
and must not be touched.

### Gateway immutable candidate identity authorization envelope

This is a placeholder-only future human authorization envelope. It does not
authorize execution or imply that a Gateway candidate identity already exists.

- Gateway service name: `casper-ombre-gateway`
- Gateway source SHA: `284c9c7b0e51a0ba0032c7028f705d72458cb304`
- Gateway Dockerfile path: `casper-deploy/Dockerfile.production`
- Gateway build context path: `..`
- Placeholder candidate tag shape:
  `casper-ombre-gateway:<human-approved-candidate-tag>`
- Default denied posture: Docker build `NO`, Docker tag creation `NO`,
  registry contact `NO`, image push `NO`, compose mutation `NO`, manifest
  mutation `NO`, deploy/restart/runtime validation `NO`, production contact
  `NO`, old Ombre `FORBIDDEN`, file modification none by default, and network
  contact none by default.
- Allowed command categories: none by default unless separately authorized.
- Allowed files to modify: none by default unless separately authorized.
- Allowed files to read: tracked docs/static metadata only unless separately
  authorized.
- Secret/privacy rules: no real secret values, no env dump, no auth headers,
  and no rendered env output.

If a later Gateway identity stage is separately authorized, its required
evidence is Gateway candidate tag, immutable image ID or digest, source SHA,
Dockerfile path, build context, build evidence, local-only status, run status,
push status, deploy status, verification status, clean Git state, and a
redacted final report.

Abort on Git drift, dirty worktree, remote mismatch, ambiguous Gateway source
SHA, ambiguous candidate tag, missing Dockerfile or build context identity,
unauthorized Docker tag/build, unauthorized registry contact, unauthorized
compose or manifest mutation, deploy/restart/runtime/Gateway/OpenRouter/
production contact, old-Ombre involvement, or real secret exposure risk.

Documenting this envelope does not prove Docker build freshness, Docker tag
creation, registry push/contact, deploy, restart, runtime verification, Gateway
runtime readiness, OpenRouter behavior, production readiness, dependency
install, pip/resolver execution, tests/scripts/hooks, old-Ombre safety proof,
or real secret validation.

### Gateway local-only build/tag evidence authorization envelope

This future human authorization envelope is separate from the placeholder-only
Gateway immutable candidate identity envelope above. It does not authorize
Docker/build/tag work by itself and does not imply that a Gateway candidate
image already exists.

- Human authorization title: `Gateway local-only build/tag evidence authorization`
- Required Git preflight: exact HEAD, latest commit, `main` tracking
  `myfork/main`, clean status, expected remotes, `0 ahead / 0 behind`, and
  immediate re-observation before any future action.
- Gateway service name: `casper-ombre-gateway`
- Gateway source SHA: `284c9c7b0e51a0ba0032c7028f705d72458cb304`
- Gateway Dockerfile: `casper-deploy/Dockerfile.production`
- Gateway build context: `..`
- Proposed local-only candidate tag shape:
  `casper-ombre-gateway:<human-approved-candidate-tag>`
- Explicit authorization switches: Docker build `YES` only if separately and
  explicitly authorized later, otherwise `NO`; Docker tag creation `YES` only
  if separately and explicitly authorized later, otherwise `NO`; Docker image
  metadata observation `YES` only if separately and explicitly authorized later,
  otherwise `NO`; Docker run / Compose up `NO` by default; registry contact /
  image push `NO` by default; compose.yaml mutation `NO` by default;
  manifest.yaml mutation `NO` by default unless a later post-evidence
  docs/manifest patch is explicitly authorized; deploy/restart/runtime
  validation `NO` by default; Gateway/OpenRouter/production contact `NO` by
  default; old Ombre `FORBIDDEN`.
- Phase breakdown: preflight-only first; optional local Docker build only with
  explicit future authorization; optional local image identity observation only
  with explicit future authorization; optional local Docker tag creation only
  with explicit future authorization; optional post-evidence docs/manifest patch
  planning only after evidence exists; registry/image push/deploy/runtime phases
  remain out of scope unless separately authorized much later.
- Required future evidence: Gateway candidate tag, immutable local image ID
  and/or digest, source SHA, Dockerfile path, build context path, build evidence,
  local-only status, run status, push status, deploy status, verification
  status, clean Git state, no real secret leakage, old-Ombre no-touch, and a
  redacted final report.
- Abort conditions: HEAD drift, dirty worktree, remote mismatch, ambiguous
  Gateway source SHA, ambiguous candidate tag, missing Dockerfile identity,
  missing build context identity, Docker unavailable or unexpected Docker
  context, unauthorized registry contact, unauthorized image push, unauthorized
  compose/manifest mutation, deploy/restart/runtime/Gateway/OpenRouter/
  production contact, unauthorized dependency install/pip/resolver/test/script/
  hook execution, old-Ombre involvement, real secret exposure risk, or
  unexpected output that would require continuing anyway.

Documenting this local-only build/tag evidence envelope does not prove Docker
build freshness, Gateway candidate tag creation, Gateway immutable image ID or
digest, registry contact, image push, deploy, restart, runtime verification,
Gateway runtime readiness, OpenRouter behavior, production readiness, dependency
install, pip/resolver execution, tests/scripts/hooks, old-Ombre safety proof, or
real secret validation.

### Local-only Docker build authorization envelope

This future human authorization envelope is for local-only Docker build planning.
It does not authorize Docker build, Docker pull, Docker image inspection, Docker
tag creation, Docker run, Compose, registry push, deploy, runtime, Gateway,
OpenRouter, or production contact by itself. It does not imply that a Gateway
candidate image already exists or that Docker build freshness has been proven.

- Primary future build candidate from tracked files: `casper-ombre-gateway`,
  because compose.yaml still has a Gateway build block.
- Gateway build inputs: service `casper-ombre-gateway`, Dockerfile
  `casper-deploy/Dockerfile.production`, build context `..`, and
  `SOURCE_SHA=284c9c7b0e51a0ba0032c7028f705d72458cb304`.
- Exact service-specific human-approved local candidate tag is required before
  any future build. Brain currently has documented local candidate metadata at
  `casper-ombre-brain:c2g10l-local-candidate-284c9c7` and remains `NOT_RUN`,
  `NOT_PUSHED`, `NOT_DEPLOYED`, and `NOT_VERIFIED`; any Brain rebuild requires a
  separate reason and exact candidate tag.
- Base image boundary: fresh base image registry validation remains
  `INCONCLUSIVE / NOT_VALIDATED`; the tracked base image digest remains
  `FROZEN_STATIC_VALIDATED`, meaning static/frozen provenance only, not fresh
  registry validation.
- Default denied posture: network / registry contact `NO` unless separately and
  explicitly authorized later; Docker pull `NO`; Docker build `NO` unless
  separately and explicitly authorized later; Docker image inspection `NO` unless
  separately and explicitly authorized later; Docker tag creation `NO` unless
  separately and explicitly authorized later; Docker run / Compose `NO`;
  dependency install / pip / resolver `NO` unless separately and explicitly
  authorized later; compose.yaml mutation `NO`; manifest.yaml mutation `NO`
  unless a later post-evidence patch is explicitly authorized; docs mutation
  after this patch `NO` unless later explicitly authorized; registry push /
  image push `NO`; deploy/restart/runtime validation `NO`; Gateway/OpenRouter/
  production contact `NO`; old Ombre `FORBIDDEN`.
- Future phase split: static Git/repo preflight only; static Dockerfile,
  compose, and manifest input identity preflight; exact build target selection
  gate; exact candidate tag approval gate; local Docker build execution gate only
  with separate explicit future authorization; optional local image metadata
  observation gate only with separate explicit future authorization; optional
  docs/manifest patch planning only after evidence exists; runtime/run/Compose
  validation only with separate explicit future authorization; registry push,
  deploy, and production phases remain out of scope unless separately authorized
  much later.
- Required future evidence if build is later authorized: exact human
  authorization text, observed Git preflight state, service name, Dockerfile
  path, build context, SOURCE_SHA/build args, approved service-specific
  candidate tag, build result and redacted build log if build occurs, local image
  ID/digest only if image metadata observation is separately authorized, tag
  status, run status still `NOT_RUN` unless separately authorized, push status
  still `NOT_PUSHED`, deploy status still `NOT_DEPLOYED`, verification status
  still `NOT_VERIFIED` unless separately authorized, no secret leakage,
  old-Ombre no-touch statement, and a redacted final report.
- Abort on HEAD drift, dirty worktree, branch/tracking mismatch, remote mismatch,
  ahead/behind mismatch, ambiguous build target, ambiguous service name,
  ambiguous Dockerfile path, ambiguous build context, ambiguous SOURCE_SHA or
  build args, ambiguous candidate tag, candidate tag collision with Brain/Gateway
  naming, candidate tag implying pushed/deployed/runtime-verified status before
  evidence exists, unexpected Docker pull or network need without explicit
  authorization, unexpected package registry / pip / resolver / install need
  without explicit authorization, Docker unavailable or non-local Docker context,
  Docker image inspection required without explicit authorization, file mutation
  outside an authorized docs patch, registry push/contact required, Docker
  run/Compose/runtime required, deploy/restart/production/Gateway/OpenRouter
  contact required, old-Ombre involvement, real secret exposure risk, or
  unexpected output requiring continuation instead of stopping.

Documenting this envelope does not prove Docker build freshness, Docker pull,
Docker image inspection, Docker tag creation, Gateway candidate image creation or
observation, runtime validation, Gateway/OpenRouter readiness, production
readiness, dependency install/resolver success, old-Ombre safety, or real secret
validation.

### Gateway local build and image metadata evidence

The Gateway candidate now has human-run normal PowerShell build-only evidence and
separately observed local image metadata. The build command shape was:

```text
docker build --pull=false -f casper-deploy/Dockerfile.production --build-arg SOURCE_SHA=284c9c7b0e51a0ba0032c7028f705d72458cb304 -t casper-ombre-gateway:c2g10l-local-candidate-284c9c7 .
```

- Build status: `PASS_BUILT_NETWORK_ALLOWED_WITH_BOUNDARY_NOTE`
- Approved candidate tag: `casper-ombre-gateway:c2g10l-local-candidate-284c9c7`
- Image ID:
  `sha256:e310204389ef5a6240bdc3533c382d2b8b77a00a559a0a3615d7ac66a2148dee`
- Repo digest:
  `casper-ombre-gateway@sha256:e310204389ef5a6240bdc3533c382d2b8b77a00a559a0a3615d7ac66a2148dee`
- OS/architecture: `linux/amd64`
- Created: `2026-08-30T17:46:11.42035904Z`
- Size: `106514296`
- Verification status: `IMAGE_METADATA_OBSERVED_ONLY`
- Run status: `NOT_RUN`
- Push status: `NOT_PUSHED`
- Deploy status: `NOT_DEPLOYED`

Boundary notes: Docker Hub metadata/auth contact was observed despite
`--pull=false`, so zero registry contact must not be claimed. Docker layer pull
is not proven by the visible build output. The locked pip install step was
`CACHED`, so fresh dependency install/download is not proven. Full `Config.Env`
was not printed, and no secret-like values were printed in the narrow metadata
output. No Docker run, Compose, image push, deploy, or runtime validation
occurred.

Fresh base image registry validation remains `INCONCLUSIVE / NOT_VALIDATED`.
Static base image provenance remains `FROZEN_STATIC_VALIDATED`. This evidence
does not prove runtime readiness, Gateway readiness, OpenRouter behavior,
production readiness, registry push, deploy readiness, tests/scripts/hooks,
old-Ombre safety proof, or real secret validation.

### Future Brain-only Compose delta

This historical delta has already been represented for the Brain image and
Brain build-block state in current compose.yaml. If a later documentation or
deployment gate revisits it, it must treat the existing Brain state as the
baseline and must not broaden into Gateway changes:

1. Confirm `casper-ombre-brain.image` remains
   `casper-ombre-brain:c2g10l-local-candidate-284c9c7`.
2. Confirm the `casper-ombre-brain` build block remains absent.
3. Preserve the Brain service name, command, environment placeholder names,
   mounts, expose setting, network, healthcheck, resource limits, and labels
   unless a separate stage explicitly authorizes another exact change.
4. Preserve the complete `casper-ombre-gateway` stanza conceptually unchanged,
   including its image, build block, command, configuration, environment,
   ports, mounts, network, healthcheck, limits, and labels.
5. Never treat the Gateway's old shared tag as Brain candidate identity.
6. Make no Nginx, cloudflared, old Ombre, source, manifest, Dockerfile, lock, or
   unrelated Compose change in that stage.

After that delta is applied and statically validated, the only frozen future
deployment command shape is:

```text
docker compose -f casper-deploy/compose.yaml up -d --no-deps --no-build casper-ombre-brain
```

It is not valid until the Compose delta is validated, the candidate has landed
on the explicitly authorized target, the target tag points to the exact image
ID above, every required configuration name passes the presence-only gate, all
preflight stop rules pass, and the previous Brain rollback identity is recorded.

### Hash-verified save/load transfer evidence

The frozen transfer strategy is a hash-verified Docker save/load archive. A
separately authorized future transfer must:

1. export only the exact local candidate tag;
2. record the archive SHA-256 and size;
3. record the transfer path without exposing secrets;
4. verify the same SHA-256 on the target before load;
5. run `docker load` only after an exact hash match; and
6. verify after load that the target tag maps to image ID
   `sha256:dc538274cbd7a33cdc1a23ed75b9719069365e1a75933d51ce51eab595b25cb7`.

Remote build and `docker import` are forbidden. Registry push/pull is forbidden
unless separately authorized with its own registry identity and credential
contract. None of these actions is authorized by this document.

### Presence-only configuration gate

The gate covers these 12 unique required names (21 required Compose references):

- `CASPER_DEHYDRATION_API_KEY`
- `CASPER_DEHYDRATION_BASE_URL`
- `CASPER_DEHYDRATION_MODEL`
- `CASPER_EMBEDDING_API_KEY`
- `CASPER_EMBEDDING_BASE_URL`
- `CASPER_EMBEDDING_MODEL`
- `CASPER_INTERNAL_HOOK_TOKEN`
- `CASPER_OMBRE_GATEWAY_TOKEN`
- `CASPER_OPENROUTER_API_KEY`
- `CASPER_PERSONA_API_KEY`
- `CASPER_PERSONA_BASE_URL`
- `CASPER_PERSONA_MODEL`

For each name, the only allowed outputs are `SET_NONEMPTY`, `MISSING`,
`PLACEHOLDER_LIKE`, or `UNCHECKED`. The gate must not print values, lengths,
hashes, headers, expanded Compose configuration, sensitive paths, or file
contents. It fails closed unless every required name is `SET_NONEMPTY`.

### Preflight hard stops

Stop before any production mutation if:

- the target host is unauthorized or ambiguous;
- the project directory differs from the frozen path;
- the service name is not exactly `casper-ombre-brain`;
- any Gateway service, container, image, command, configuration, environment,
  port, mount, network, or health behavior would change;
- any command would build an image or start dependencies;
- the candidate tag or image ID does not match the frozen identity;
- the archive hash does not match;
- any port, mount, network, or configuration path differs from the frozen plan;
- raw logs, data, database, state, or memory content would need to be read;
- old Ombre would need to be inspected, touched, or used as fallback;
- the previous Casper Brain rollback identity is not recorded;
- any required configuration result is not `SET_NONEMPTY`; or
- any command is broader than the exact frozen allowlist.

### Gateway and old Ombre no-touch contracts

Gateway must not be rebuilt, restarted, have its image replaced, or receive any
command, configuration, environment, port, mount, or other stanza change. Its
logs, environment, and tokens must not be read, and no Gateway health request
is allowed without separate authorization. Every future deployment command must
target Brain only with `--no-deps`.

Old Ombre must not be inspected, restarted, stopped, read, status-checked, used
as fallback, or treated as sharing safe routing or resources. Its files, logs,
processes, services, data, routes, and runtime remain outside every Casper
deployment, verification, rollback, and recovery target.

### Remaining deployment blockers

- The Brain-only Compose delta is not applied or statically validated.
- The candidate archive is not exported, transferred, hash-verified, or loaded.
- The target host and project path are not explicitly authorized.
- The presence-only configuration gate has not run.
- The previous production Casper Brain rollback identity is not recorded.
- The candidate has not been deployed or run.
- Runtime, Persona, and OpenRouter compatibility verification is incomplete.
- Prompt Cache validation remains blocked by no safe Gateway-token source.
- C2G10M remains blocked and is not authorized by this document.

## BLOCKING_USER_CONFIGURATION

Before any deployment or start:

1. Supply a new Casper Gateway Bearer credential outside Git.
2. Supply the OpenRouter API key outside Git.
3. Select and supply dehydration provider, base URL, model, and key.
4. Select and supply embedding provider, base URL, model, and key.
5. Select and supply Persona provider, base URL, model, and key.
6. Decide whether remote reranking remains disabled; if enabled, supply a
   compatible /rerank provider, model, and separate key.
7. In C2F2, create and protect the user-owned signing identity, produce the
   signed `me.rerere.rikkahub.casper` artifact from the already frozen/locked
   graph, inspect certificate and provenance, and run only the separately
   authorized minimum production-package smoke.
8. Migrate only the minimum provider/model configuration by manual entry or a
   separately authorized per-provider secret transfer; never copy the official
   private database.
9. Prove the client does not override prompt_cache_key incorrectly.
10. Verify streaming, non-streaming, reasoning, verbosity, tools, tool_choice,
   parallel_tool_calls, max_completion_tokens, response_format, service_tier,
   and prompt cache against openai/gpt-5.4 through OpenRouter.
11. Choose the new Casper public hostname and reverse-proxy path policy.
12. Revalidate that 18202 is still free on the VPS.
13. Apply and statically validate the frozen Brain-only Compose delta without
    changing Gateway.
14. Export, transfer, verify, and load the exact candidate through the separately
    authorized hash-verified archive contract; no remote build or import.
15. Explicitly authorize the target host and project path, then pass the
    non-value configuration presence gate and every preflight hard stop.
16. Record the previous production Casper Brain identity and rollback metadata
    before any deployment mutation.
17. Keep old Ombre completely outside inspection, status checks, deployment,
    verification, rollback, fallback, routing assumptions, and shared-resource
    assumptions.
18. Complete the separately authorized Brain deployment and bounded status-only
    runtime checks without reading raw logs, data, database, state, or memory.
19. Verify Persona and OpenRouter runtime compatibility separately.
20. Resolve the no-safe-Gateway-token blocker before Prompt Cache validation.
21. Keep C2G10M blocked until every preceding deployment gate is satisfied and
    a fresh explicit authorization is granted.

C2D2B PASS adds private-device proof of session stability, isolation, restart
persistence, no-header absence, and static-header compatibility. C2E froze the
production-client identity and policy; C2F1 has now frozen dependency inputs
and validated the unsigned release path. It still does not create a production
signing key, produce a signed APK, run a production-package device smoke test,
or establish real-provider/VPS production readiness.
