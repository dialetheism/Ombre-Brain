# Casper Ombre Runtime Operations and Troubleshooting Runbook

Last documentation update: 2026-08-27

## 1. Purpose and scope

This non-secret runbook tells future operators how to diagnose common Casper Ombre-Brain runtime and RikkaHub client problems in the least invasive order. It records safe checks, evidence boundaries, authorization gates, and stop conditions.

It does not authorize a live request, SSH connection, secret read, database inspection, log inspection, restart, build, deployment, signing, installation, backup, restore, or infrastructure change. Previously verified facts are historical handoff evidence, not a substitute for a newly authorized live check.

## 2. Current known-good Casper configuration

- Public OpenAI-compatible base URL: `https://casper.ticktackticktack.com/v1`
- Models endpoint: `GET /v1/models`
- Chat endpoint: `POST /v1/chat/completions`
- External model ID: `casper-gpt-5.4`
- Upstream model: `openai/gpt-5.4`
Authorization: <REDACTED_BEARER_PLACEHOLDER>
- Session header: `X-Ombre-Session-Id`
- Recommended patched header: `X-Ombre-Session-Id={{conversation_id}}`

Never replace the placeholder in this document with a real token or a real Authorization header.

Known completed stages include C2G8G session isolation `PASS`, C2G8I README completion `PASS`, C2G8J production handoff revalidation `PASS`, and C2G8K master index creation `PASS`.

## 3. Normal RikkaHub client configuration

- Application ID: `me.rerere.rikkahub.casper`
- Version: `2.4.9 (176)`
- ABI: `arm64-v8a`
- Provider type: `OpenAI-compatible / Custom OpenAI`
- Base URL: `https://casper.ticktackticktack.com/v1`
- Model ID: `casper-gpt-5.4`
- Custom Header: `X-Ombre-Session-Id={{conversation_id}}`
- Streaming: `True`

The client should need only the Casper Gateway token. The user enters and manages that token locally. The phone or client must not store the OpenRouter key, Cloudflare token, Nginx token, SSH key, or keystore password.

## 4. Ordinary RikkaHub fallback and its limitation

Ordinary RikkaHub 2.4.5 does not expand `{{conversation_id}}`; it sends that literal template value. Its temporary fallback is:

`X-Ombre-Session-Id=casper-rikkahub-main`

This static fallback makes all ordinary RikkaHub conversations share one Casper session. It is not equivalent to patched per-conversation isolation and should not be mistaken for the recommended production configuration.

## 5. Troubleshooting priority order

Always start with the least invasive checks:

1. Check client-side configuration first.
2. Check whether the correct patched RikkaHub app is being used.
3. Check Base URL, model ID, custom header, and streaming setting.
4. Check whether the Gateway token was entered locally by the user.
5. Do not ask the user to paste or reveal the real token.
6. Do not inspect server-side secrets unless a separate task explicitly authorizes it.
7. Do not restart services before collecting safe evidence.
8. Do not touch old Ombre.

Keep each troubleshooting task to one symptom, one main goal, and one acceptance target.

## Gateway-path runtime validation prerequisites

C2G10L89 was readonly design only. It was based on local HEAD
`2b83da2754baf29655c2f2ff7426ee337a305915`; that HEAD is historical L89
provenance only. Any future validation must re-observe current HEAD, branch,
git status, remotes, and ahead/behind state before execution.

Static Gateway routes identified for future scoped validation are:

- `/health`
- `/v1/models`
- `/v1/chat/completions`
- `/v1/messages`

Static admin/debug surfaces identified for future scoped review are:

- `/api/config`
- `/api/debug/injections`
- `/api/hook/recall`
- `/api/debug/recall-eval`
- `/api/debug/upstream-usage`

Placeholder-only boundaries:

- `CASPER_OMBRE_GATEWAY_TOKEN` maps to Gateway client auth.
- `CASPER_OPENROUTER_API_KEY` is Gateway-side provider auth.
- `CASPER_INTERNAL_HOOK_TOKEN` maps to Brain internal hook auth.

Brain internal hook paths identified for future scoped validation are:

- `/auth-check-hook`
- `/breath-hook`
- `/introspection-hook`
- `/dream-hook`

Any future real validation requires a fresh human authorization envelope naming:

- environment;
- exact service/path;
- allowed secret placeholders by name only;
- allowed network targets;
- allowed commands, if any;
- maximum provider/paid request count;
- stop/abort conditions.

### Future authorization envelope template

C2G10L96 drafted this template from local HEAD
`2ec18814a25f395e2a407d36e4c959d8bbf8b507`; that HEAD is historical draft
provenance only. Future execution must re-observe current Git state and must
not rely on the historical L96 HEAD alone.

- Environment name: `<LOCAL_OR_NONPROD_ENVIRONMENT_NAME>`
- Local/non-production Gateway target descriptor:
  `<AUTHORIZED_LOCAL_OR_NONPROD_GATEWAY_TARGET>`
- Allowed service/path list: `<EXACT_PATHS_ONLY>`
- Exact HTTP methods by path: `<PATH_TO_METHOD_ALLOWLIST>`
- Allowed secret placeholders by name only:
  `CASPER_OMBRE_GATEWAY_TOKEN`, `CASPER_OPENROUTER_API_KEY`,
  `CASPER_INTERNAL_HOOK_TOKEN`
- Secret handling rule: `SET/MISSING` only; never values, lengths, headers,
  rendered env, or full env-file contents.
- Allowed network targets: `<EXACT_LOCAL_OR_NONPROD_TARGETS_ONLY>`
- Allowed readonly command categories: `<EXACT_READONLY_CATEGORIES_ONLY>`
- Maximum total request count: `<INTEGER_CAP>`
- Provider/OpenRouter authorization: `YES/NO`, default `NO`
- Maximum paid provider/OpenRouter request count: `<INTEGER_CAP>`, default `0`
- Production contact: `NO`
- Docker/build/test/script/hook execution: `NO`
- Restart/deploy: `NO`
- Old Ombre contact: `FORBIDDEN`
- Required Git preflight: re-observe current HEAD, latest commit,
  branch/tracking, git status, remotes, and ahead/behind before execution.
- Abort conditions: `<EXACT_ABORT_CONDITIONS>`
- Required final report evidence: `<EXACT_REDACTED_EVIDENCE_FIELDS>`

### Future local/non-production Gateway preflight checklist

C2G10L102 planned this checklist from local HEAD
`bbb05f9bd4186f553e9b4fed3048e95b8d3b389d`; that HEAD is historical plan
provenance only. Future execution must re-observe current Git state and must
not rely on the historical L102 HEAD alone. Passing preflight only permits
considering a later separately authorized local/non-production dry run; it does
not prove Gateway runtime readiness.

- Git state: expected HEAD, latest commit, branch/tracking, clean status,
  remotes, and ahead/behind must match the future authorization.
- Source identity: confirm local construction source, `myfork` writable backup,
  `origin` author/upstream reference only, and no P0luz/upstream chase.
- Documentation boundary: this Gateway prerequisite section and authorization
  template must be present before execution.
- Secret placeholders: names only; future `SET/MISSING` only; no values,
  lengths, headers, rendered env, or full env contents.
- Target identity: exact local/non-production Gateway target descriptor required
  before execution.
- Route/method authorization: exact path list and method-by-path allowlist
  required before execution.
- Request budget: total request cap required; no retries beyond cap.
- Provider/OpenRouter: default `NO`; paid request cap default `0`; separate
  provider/model authorization required if ever used.
- Production/Docker/restart: production `NO`; Docker/build/test/script/hook
  `NO`; restart/deploy `NO`.
- Old Ombre: `FORBIDDEN`.
- Abort-before-contact: stop before runtime/Gateway contact on ambiguity,
  drift, missing cap, secret exposure risk, target mismatch, or unapproved
  scope.
- Evidence: final report must use redacted evidence only and must not leak
  secrets.

Still unvalidated in this validation line:

- no runtime restart success has been proven;
- no Gateway runtime readiness has been proven;
- no production/deployment readiness has been proven;
- no Docker/build/dependency-install success has been proven;
- no broad provider/model cache support has been proven;
- no OpenRouter call has been made in this validation line;
- no Gateway call has been made;
- no target runtime call has been made;
- no production contact has been made;
- no old-Ombre check has been made;
- no real secret presence validation has been performed.

## 6. Symptom: RikkaHub cannot connect

Likely causes:

- Wrong Base URL.
- Missing `/v1` suffix.
- Network or VPN issue.
- Gateway public route unavailable.
- Cloudflare Tunnel issue.
- Gateway service issue.

Safe first checks:

- Verify the Base URL is exactly `https://casper.ticktackticktack.com/v1`.
- Verify the provider type is `OpenAI-compatible / Custom OpenAI`.
- Verify the model ID is `casper-gpt-5.4`.
- Verify the client has a Gateway token entered locally by the user.
- Record whether the VPN or network changed and the visible non-secret error code.
- Do not paste the token into chat.

Do not jump directly to server restarts. A live connectivity probe or synthetic request requires a separate task with its request count bounded in advance.

## 7. Symptom: 401 or unauthorized

Likely causes:

- Missing Gateway token.
- Wrong Gateway token.
- Authorization header not sent.
- Client saved an old token.

Safe handling:

- Confirm only that a token is present in the client; do not reveal its value.
- Let the user re-enter or manage the real token locally if needed.
- Record the visible HTTP status and approximate timestamp without copying headers.
- Do not print or paste the real Gateway token.
- Do not read the runtime env to retrieve the token unless a separate explicit authorization exists.
- The user must manage the real token locally.

## 8. Symptom: 404 from public endpoint

Likely causes:

- Wrong URL path.
- Missing `/v1`.
- Cloudflare catch-all route.
- Requesting an unsupported endpoint.

Known-good paths under the public host are:

- `/v1/models`
- `/v1/chat/completions`

First compare the configured Base URL and endpoint spelling. Do not change Cloudflare routes or DNS merely to chase a 404; any route inspection or change requires a separate explicit task.

## 9. Symptom: 502 or tunnel/upstream unavailable

Likely causes:

- Cloudflare Tunnel unavailable.
- Gateway not reachable on its localhost binding.
- Gateway container unhealthy.
- Host routing issue.

Record the visible status, approximate timestamp, whether the failure affects all conversations, and whether the network or VPN changed. Do not restart cloudflared, Docker, Gateway, Brain, or Nginx without separate explicit authorization. Do not modify Cloudflare, Nginx, or the tunnel during an evidence-only stage.

## 10. Symptom: models endpoint does not show expected model

The expected external model is `casper-gpt-5.4`.

Likely causes:

- Wrong Base URL.
- Wrong provider configuration.
- Gateway issue.
- Using an ordinary provider instead of the custom OpenAI-compatible provider.

Check the provider type, Base URL, and configured model ID first. Do not expose the token or send a new probe request unless that request is explicitly authorized and counted.

## 11. Symptom: chat completions request fails

Likely causes include an incorrect `/v1/chat/completions` path, missing or stale Gateway authentication, wrong model ID, malformed client request, network interruption, Gateway failure, or upstream failure.

Safe first checks:

- Confirm the provider, Base URL, and model ID from the client screen.
- Record the visible non-secret HTTP status or error message and approximate timestamp.
- Note whether the failure occurs in one conversation or all conversations.
- Note whether streaming was enabled.
- Do not paste request headers, private message bodies, or tokens.

A synthetic chat request, paid upstream request, raw log inspection, or server-side change requires a separately authorized task.

## 12. Symptom: streaming fails or hangs

Likely causes include a client streaming-setting mismatch, interrupted VPN or network connection, proxy or tunnel timeout, Gateway response-stream issue, or upstream delay.

Verify that Streaming is set to `True`, note whether non-streaming behavior was ever separately tested, record the approximate hang duration, and record whether the issue affects one or all conversations. Do not repeatedly resend paid requests. Any controlled comparison request must be separately authorized with an exact maximum request count.

Do not restart Gateway, Brain, Docker, cloudflared, or Nginx before safe evidence is collected.

## 13. Symptom: conversations appear to share memory/session

Expected patched behavior:

Patched RikkaHub 2.4.9 should send `X-Ombre-Session-Id={{conversation_id}}`, expanded into a persistent RikkaHub conversation UUID. Different RikkaHub conversations should produce different Casper sessions.

Likely causes:

- Using ordinary RikkaHub 2.4.5.
- Using static header `X-Ombre-Session-Id=casper-rikkahub-main`.
- Template expansion failed.
- Header missing.
- Client reset or changed conversation identity.

Collect only conversation labels such as A/B, non-secret marker labels, approximate timestamps, app version/package, and whether the header was template or static. Do not inspect raw message content or dump database rows unless a separate task explicitly authorizes a narrow redacted audit.

## 14. Symptom: `{{conversation_id}}` appears literally instead of a UUID-like session

Ordinary RikkaHub 2.4.5 sends the literal value `{{conversation_id}}` and does not expand it. Patched RikkaHub 2.4.9 is required for per-conversation isolation.

First confirm the installed package is `me.rerere.rikkahub.casper`, the version is `2.4.9 (176)`, and the custom header is exactly `X-Ombre-Session-Id={{conversation_id}}`. Do not replace the template with a shared static value unless the user knowingly accepts the fallback limitation.

## 15. Symptom: Gateway or Brain health is suspected unhealthy

Start with safe client-visible evidence: status code, non-secret error text, approximate timestamp, affected scope, VPN/network state, and whether the public Base URL is correct.

Do not infer that a restart is required from one client error. Server-side container health inspection, process inspection, localhost checks, Docker commands, and log inspection require a separately scoped task. A read-only server diagnosis does not authorize restart, rebuild, pull, redeploy, or secret access.

Never redirect Casper troubleshooting to old Ombre.

## 16. Symptom: persistence or “刚才 / just now” continuity seems wrong

Likely causes:

- Wrong session header.
- Static session fallback used unintentionally.
- Gateway persistence issue.
- Brain/Gateway synchronization issue.
- User testing across different clients or conversations.

Safe evidence:

- Conversation labels A/B.
- Non-secret marker labels.
- Approximate local timestamp.
- Whether patched or ordinary RikkaHub was used.
- Whether the header was template or static.
- Whether the issue occurred in the same conversation after an app restart.

Do not provide private message dumps unless separately authorized. Database inspection, raw row output, and server-side persistence inspection require a narrow redacted-audit task.

## 17. Symptom: OpenRouter upstream/model failure is suspected

The expected upstream model is `openai/gpt-5.4`. First separate client/Gateway configuration failures from an upstream failure using only the visible non-secret status, timestamp, and already-authorized evidence.

Do not expose or retrieve the OpenRouter key. Do not read runtime env or token files. Do not send repeated or synthetic upstream requests. Any OpenRouter or LLM request requires a separate explicit task with the provider/model and maximum paid request count specified in advance.

If a server-side upstream error or raw log would be needed, stop and request narrow authorization; logs must be redacted before reporting.

## 18. Safe evidence to collect before asking Codex

Safe evidence that may be shared without exposing secrets:

- RikkaHub version and package name.
- Whether the app is patched or ordinary.
- Base URL without token.
- Model ID.
- Custom header key and template value.
- Error code or visible non-secret error message.
- Approximate timestamp.
- Whether the issue happens on one conversation or all conversations.
- Whether VPN or network changed.
- Whether streaming is enabled.
- Conversation labels A/B and non-secret marker labels when session isolation is relevant.

Unsafe evidence that must not be provided:

- Gateway token.
- OpenRouter key.
- Cloudflare token.
- SSH private key.
- Keystore password.
- Password file content.
- Runtime env content.
- Authorization header with a real value.
- Credential JSON.
- Full database rows containing private messages.
- Raw logs containing secrets.

Screenshots must be checked for visible tokens, private messages, notification content, QR codes, or credentials before sharing.

## 19. Actions requiring separate authorization

Future tasks require separate, fresh, explicit authorization before any of these actions:

- SSH, SCP, or SFTP.
- Docker build, up, down, restart, pull, or Compose restart.
- Gateway restart.
- Brain restart.
- cloudflared reload or restart.
- Nginx reload or restart.
- Cloudflare Tunnel, route, DNS, or Access changes.
- Runtime env reads.
- Token-file reads.
- Password-file reads.
- Production keystore reads or copying.
- Database inspection.
- Raw log inspection.
- OpenRouter or other LLM API requests.
- Gradle.
- APK build.
- APK signing.
- ADB installation.
- Actual backup execution.
- Restore execution.
- Old Ombre inspection or modification.

Authorization for a read-only check does not authorize a write, restart, retry, fallback, repair, or next stage.

## 20. Absolute stop conditions

A future task must stop immediately if:

- A real secret would need to be read, printed, copied, uploaded, logged, or pasted into chat.
- Old Ombre would need to be touched.
- A restart, build, deploy, signing, installation, or API call would be needed but was not explicitly authorized.
- The task begins to expand beyond one main goal.
- A failure would require modifying production files to chase `PASS`.
- Codex quota is close to the user-defined lower bound.
- The correct target, ownership boundary, or permitted request count is ambiguous.

Report the blocker without attempting a workaround that expands scope.

## 21. Secret-handling rules

- Never print, paste, quote, log, screenshot, upload, or store a real Gateway token, OpenRouter key, Cloudflare token, SSH private key, keystore password, password-file content, runtime env content, token-file content, credential JSON, or real Authorization header.
- Do not ask the user to send secrets to Codex or ChatGPT.
- The user manages real tokens and passwords locally.
- Inventory checks may report only safe metadata such as existence, size, timestamp, expected path match, ACL summary, or a specifically authorized redacted hash prefix.
- Do not expose private message content, private database rows, or raw logs containing user data.
- Placeholder examples such as `<CASPER_OMBRE_GATEWAY_TOKEN>` must remain placeholders.

### Production signing continuity

Production keystore:

`C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\signing\casper-rikkahub\casper-rikkahub-production.jks`

Alias:

`casper_rikkahub_production`

Future Casper RikkaHub production updates and restore workflows for package `me.rerere.rikkahub.casper` must use the same production keystore and alias shown above. Do not use build-cache, debug, temporary, regenerated, ad-hoc, replacement, or any other non-production keystore for Casper RikkaHub production updates or restore workflows. Using a different keystore will break Android update continuity for `me.rerere.rikkahub.casper`.

### Complete password-file handling rule

The keystore password file is a local secret. Do not read, print, dump, paste into chat, commit, log, screenshot, upload, or read aloud its contents.

Do not copy the keystore password or password-file contents into plaintext notes, README files, handoff documents, chat messages, screenshots, logs, commits, tickets, cloud notes, or any other non-secret storage.

Codex and ChatGPT must not ask the user to paste, reveal, transcribe, summarize, screenshot, upload, or otherwise provide the keystore password or password-file contents. Only the user may use the password file locally in a safe signing context. Documentation and inventory tasks may verify password-file existence and ACL only, without reading password contents.

### Backup and restore requirement

A safe backup set should preserve the production signed APK, production keystore, corresponding password file, and handoff README together. Actual backup execution requires a separate explicit task. Do not execute backup automatically. Do not upload secrets automatically. Do not expose raw passwords, Gateway tokens, OpenRouter keys, Cloudflare tokens, SSH private keys, runtime env contents, token file contents, Authorization headers, or credential JSON contents in plaintext notes.

To restore signing continuity, recover the same production keystore and corresponding password file, then sign future `me.rerere.rikkahub.casper` APK updates with alias `casper_rikkahub_production`. Do not substitute a debug, build-cache, regenerated, temporary, ad-hoc, replacement, or any other non-production keystore.

## 22. C2G10 hardened Brain pre-deploy and recovery rules

### Pre-deploy checklist

Before any future patched-Brain deployment is authorized, verify all of the following without starting or changing production:

- The reviewed C2G10E `server.py` patch remains the only intended source change, and the non-secret documentation/configuration update has passed its own review.
- `OMBRE_INTERNAL_HOOK_TOKEN` will be supplied through an external secret path and is distinct from the Gateway token.
- `OMBRE_DASHBOARD_SETUP_ENABLED` is explicitly `false`, or an exceptional first-setup window has its own separate authorization.
- Existing password-hash, completion-lock, or pending-reservation state keeps Dashboard setup closed.
- `OMBRE_MCP_AUTH_REQUIRED` is explicitly `true`, and the required MCP authentication provider is configured to fail closed.
- `OMBRE_MCP_MUTATIONS_ENABLED` is explicitly `false`.
- Record the current source HEAD and reviewed local patch identity before a build. Only after a separately authorized future build may the resulting image digest and tag be recorded as the deployable immutable source identity; an uncommitted source patch is not a deployed image identity.

Credential verification must report only `SET` or `MISSING`. Never print values, value lengths, headers, environment dumps, shell-expanded values, or rendered Compose output that could contain secrets. Do not use `env`, `printenv`, container-environment inspection, shell tracing, or any equivalent value-dumping method.

### Dashboard setup state and pending-reservation recovery

- `.dashboard_auth.json` is password-hash state. Normal operational checks may verify only its existence and file metadata; they must not read its content.
- `.dashboard_setup.complete` is the persistent completion lock.
- `.dashboard_setup.pending` is the exclusive first-setup reservation.
- A corrupt or partial auth file fails closed. Its existence is not permission to replace, truncate, or delete it.
- A pending reservation after interruption is a blocker that requires a separately authorized manual recovery stage. Do not automatically delete it or retry setup.
- Any recovery decision must first use metadata-only checks to rule out an active setup attempt and determine whether accepted auth or completion state exists. Exact deletion or repair, if ever justified, requires a separately named Casper-only maintenance action.
- Backup, restore, image rollback, and configuration rollback must preserve `.dashboard_auth.json`, `.dashboard_setup.complete`, and `.dashboard_setup.pending`; none may be removed automatically to reopen setup.

### MCP transport and mutation rules

- MCP authentication is required in production. Missing provider configuration must fail closed.
- Host headers, protected-host lists, private Docker networking, and absence of a public route are defense-in-depth only and are not authentication.
- MCP mutations remain disabled by default. Enabling them requires a separate explicit authorization and a bounded mutation review.
- A write credential must never be exposed as an MCP tool argument or passed through model/tool context.
- Read-only and sensitive-read MCP tools still require transport authentication.

### Safe status-only boundary checks

Use unauthenticated `GET` or `HEAD` checks only where a separately authorized route review has already classified them as safe. Record status code and safe response metadata only, discard response bodies, and do not print headers. Do not call `/v1/chat/completions`, mutation tools, setup writes, admin mutation endpoints, or any endpoint that could read or change memory. These rules do not authorize a network request, container command, restart, or deployment.

Never redirect a hardened-Brain check, setup recovery, or MCP test to old Ombre.

## 23. Old Ombre no-touch boundary

Known historical identity:

- Container: `ombre-brain`
- Container ID: `<REDACTED_HEX_IDENTIFIER>`
- StartedAt: `2026-07-16T07:47:33.068769789Z`
- RestartCount: `0`
- Old listen: `0.0.0.0:8000`
- Old route: `Cloudflare -> localhost:18080 -> Nginx /mcp -> 127.0.0.1:8000/mcp`

Do not stop, restart, rebuild, modify, migrate, inspect, or touch old Ombre. Do not modify `/opt/ombre-brain`. Do not use old Ombre as a fallback target for Casper troubleshooting.

The identity above is boundary metadata only and is not permission to inspect the old service.

## 24. Recommended next-stage rule

Do not execute next-stage recommendations automatically. Each future task must have one main goal, one acceptance target, and stop immediately after the final report. Any build, deployment, restart, signing, installation, API request, backup, restore, or secret-adjacent operation requires a new explicit task.

If the current evidence is insufficient, report what is missing and wait for a new bounded authorization instead of changing production or retrying automatically.
