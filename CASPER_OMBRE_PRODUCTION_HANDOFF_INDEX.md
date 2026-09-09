# Casper Ombre Production Handoff Master Index

Last documentation update: 2026-09-09

This file is the non-secret master handoff index for Casper Ombre-Brain. It records previously verified production and handoff facts; it is not a live VPS check. This document does not authorize any operational next stage.

## 1. Current production status

- Casper Brain and Gateway were previously verified running and healthy.
- The public Gateway was previously verified through the Cloudflare Tunnel.
- Gateway authentication, one bounded OpenRouter GPT-5.4 end-to-end request, persistence, client-style history, Chinese continuity, and patched RikkaHub per-conversation session isolation have passed their authorized verification stages.
- Patched RikkaHub 2.4.9 uses each persisted conversation ID as `X-Ombre-Session-Id`, keeping different conversations in different Casper sessions.
- The C2G10E `server.py` application-layer hardening patch exists only in the local working tree and has not been built or deployed.
- Current production therefore remains on the pre-hardening source until credential provisioning, build, deployment, and the required Casper restart are separately authorized and completed.
- Separate local-only Gateway candidate evidence is classified `HEALTH_OK_WITH_CLEANUP_RECOVERY_LOCAL_ONLY`. It did not contact, deploy, restart, or validate production and does not alter the current production image or configuration.

## 2. Completed verification stages

- `C2G8G`: patched RikkaHub per-conversation session isolation — `PASS`.
- `C2G8H`: initial production handoff inventory — `FAIL` only because README safety and backup/restore documentation was incomplete.
- `C2G8I`: README safety and backup/restore documentation completion — `PASS`.
- `C2G8J`: patched RikkaHub production handoff read-only revalidation — `PASS`.
- `C2G10C`: public and Gateway unauthenticated boundaries were normal and no public sensitive-data leak was observed; strict result was `FAIL` because internal Brain hooks, first-run setup, and MCP mutation boundaries lacked explicit application-layer closure.
- `C2G10D`: read-only source-hardening review and minimal patch plan — `PASS`.
- `C2G10E`: local-only `server.py` hardening patch and isolated fake-token tests — `PASS` (`29/29`); the patch was not deployed.
- `C2G10F`: read-only patch review — `PASS`; the tracked diff remained only `server.py`, existing auth boundaries were not weakened, and the source was ready for a documentation/configuration stage only.
- `C2G10G`: read-only documentation/configuration planning — `PASS`; it authorized an exact five-file, no-secret C2G10H scope.
- `C2G10H`: this stage updates only the five approved non-secret documentation/configuration files; it performs no source change, credential provisioning, build, network request, restart, or deployment.
- `C2G10L194`: the exact local Gateway candidate started under isolated, dummy-environment, no-host-port, no-bind, network-none boundaries; one container-internal `/health` returned HTTP `200` with `status=ok`. The stage ended `ABORT_L194_CLEANUP_STOP_FAILED`, so it is not a clean single-pass PASS.
- `C2G10L195`: cleanup-only exact-container verification returned `PASS_CLEANUP_ALREADY_ABSENT`, with `final_absent=true` and `cleanup_succeeded=true`. Combined L194/L195 classification: `health-success-with-cleanup-recovery`.

## 3. Local paths

- Project: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-Brain`
- BuildTools: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools`
- Signed patched APK: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\casper-rikkahub-c2f2b-signed-20260824-035833\RikkaHub-Casper-2.4.9-arm64-v8a-signed.apk`
- Production keystore: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\signing\casper-rikkahub\casper-rikkahub-production.jks`
- Existing patched RikkaHub handoff README: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\casper-rikkahub-c2f2b-signed-20260824-035833\README.txt`

## 4. VPS paths

- VPS identity summary: `admin@47.251.255.218`
- SSH key path summary: `$HOME\.ssh\aliyun_codex_ed25519`
- Project root: `/srv/casper-ombre`
- Deployment directory: `/srv/casper-ombre/casper-deploy`
- Compose file: `/srv/casper-ombre/casper-deploy/compose.yaml`
- Runtime env path: `/srv/casper-ombre/casper-deploy/env/casper.runtime.env`
- Persistent data: `/srv/casper-ombre/data`
- Persistent state: `/srv/casper-ombre/state`
- Backup location: `/srv/casper-ombre/backups`

The runtime env path is recorded as non-secret metadata only. Do not read its contents without a separate explicit authorization. Do not SSH merely to recheck this index.

## 5. Public Gateway and model contract

- OpenAI-compatible base URL: `https://casper.ticktackticktack.com/v1`
- Models endpoint: `GET /v1/models`
- Chat endpoint: `POST /v1/chat/completions`
- External model ID: `casper-gpt-5.4`
- Upstream model: `openai/gpt-5.4`
- Authentication pattern, placeholder only: `Authorization: Bearer <CASPER_OMBRE_GATEWAY_TOKEN>`
- Session header name: `X-Ombre-Session-Id`

Never replace the placeholder in this document with a real Gateway token or real Authorization header.

## 6. RikkaHub patched configuration

- Application ID: `me.rerere.rikkahub.casper`
- Version: `2.4.9 (176)`
- ABI: `arm64-v8a`
- Provider type: `OpenAI-compatible / Custom OpenAI`
- Base URL: `https://casper.ticktackticktack.com/v1`
- Model ID: `casper-gpt-5.4`
- Custom Header: `X-Ombre-Session-Id={{conversation_id}}`
- Streaming: `True`

The client should need only the Casper Gateway token. The phone or client must not store the OpenRouter key, Cloudflare token, Nginx token, SSH key, or keystore password.

## 7. Ordinary RikkaHub fallback limitation

Ordinary RikkaHub 2.4.5 does not expand `{{conversation_id}}`; it sends the literal template value. Its temporary fallback header is:

`X-Ombre-Session-Id=casper-rikkahub-main`

This fallback is limited because all conversations share one Casper session. Patched RikkaHub 2.4.9 is the recommended production client.

## 8. Patched APK handoff artifact

- Artifact: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\casper-rikkahub-c2f2b-signed-20260824-035833\RikkaHub-Casper-2.4.9-arm64-v8a-signed.apk`
- SHA-256: `db09161d9da1bceb6d22ce4518f3544af921415be71f0e4130303ddc5c7d30ba`
- Size: `38916654` bytes
- Package: `me.rerere.rikkahub.casper`
- Version: `2.4.9 (176)`
- ABI: `arm64-v8a`
- Handoff README: `C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\casper-rikkahub-c2f2b-signed-20260824-035833\README.txt`

These metadata values were revalidated by C2G8J. This index does not re-sign, install, copy, upload, or modify the APK.

## 9. Production signing continuity

Future Casper RikkaHub APK updates must use the same production keystore:

`C:\Users\LENOVO\Documents\ChatGPT\Casper-Ombre-BuildTools\signing\casper-rikkahub\casper-rikkahub-production.jks`

Alias:

`casper_rikkahub_production`

Future `me.rerere.rikkahub.casper` APK updates must use the same production keystore and alias shown above. Do not use build-cache, debug, temporary, regenerated, ad-hoc, replacement, or any other non-production keystore for Casper RikkaHub production updates or restore workflows. Using a different keystore will break Android update continuity for `me.rerere.rikkahub.casper`.

## 10. Password-file handling rule

The keystore password file is a local secret. Do not print, dump, paste into chat, commit, log, screenshot, upload, or read aloud its contents. Documentation and inventory tasks may verify password-file existence and ACL only, without reading password contents. Only the user may use the password file locally in a safe signing context.

Do not copy the keystore password or password-file contents into plaintext notes, README files, handoff documents, chat messages, screenshots, logs, commits, tickets, cloud notes, or any other non-secret storage.

Codex and ChatGPT must not ask the user to paste, reveal, transcribe, summarize, screenshot, upload, or otherwise provide the keystore password or password-file contents.

Do not place the password, a password-derived value, or instructions containing the password in this index.

## 11. Backup and restore readiness

A safe backup set should preserve the production signed APK, production keystore, password file, and handoff README together. The backup should be stored in a user-controlled secure location, preferably encrypted and offline or otherwise access-restricted.

Actual backup execution requires a separate explicit task. Do not execute backup automatically. Do not upload secrets automatically. Do not expose raw passwords or tokens in plaintext notes.

To restore signing continuity, recover the same production keystore and corresponding password file, then sign future `me.rerere.rikkahub.casper` APK updates with alias `casper_rikkahub_production`. Do not substitute a debug, build-cache, regenerated, or temporary keystore. Before any future signing, verify the production keystore path, alias, and password-file handling rule.

Restore execution also requires a separate explicit task. This index records readiness requirements only and does not perform backup or restore.

## 12. Old Ombre absolute no-touch boundary

- Container: `ombre-brain`
- Container ID: `82d5728446c73909cf95a567f31c6d7a6fa8ed81b62013a4533f84a1603e3efa`
- StartedAt: `2026-07-16T07:47:33.068769789Z`
- RestartCount: `0`
- Old listen: `0.0.0.0:8000`
- Old route: `Cloudflare -> localhost:18080 -> Nginx /mcp -> 127.0.0.1:8000/mcp`

Do not stop, restart, rebuild, modify, migrate, inspect, or touch old Ombre. Do not modify `/opt/ombre-brain`.

The old service identity above is historical handoff metadata, not permission to inspect it.

## 13. Permanent forbidden operations

No Gateway token, OpenRouter key, Cloudflare token, SSH private key, keystore password, real Authorization header, runtime env content, token file content, or credentials JSON content may be printed or stored in this document.

Future tasks require separate, fresh, explicit authorization before any of the following actions:

- SSH, SCP, or SFTP.
- Docker build, up, down, restart, pull, or Compose restart.
- Gateway restart.
- Brain restart.
- Gradle or any APK build.
- APK signing or signature-changing operation.
- ADB installation or device operation.
- OpenRouter or other LLM API requests, with the paid request count bounded in advance.
- Cloudflare Tunnel, route, DNS, or Access changes.
- Nginx reload or restart.
- cloudflared reload or restart.
- Runtime env reads.
- Token-file reads.
- Password-file reads.
- Production keystore reads.
- Production keystore copying.
- Database inspection.
- Raw log inspection.
- Actual backup execution.
- Restore execution.
- Old Ombre inspection or modification.

The old Ombre no-touch boundary remains absolute by default. A recommendation, path listing, or prior verification never counts as authorization.

## 14. Next-stage rule

- This document authorizes no next stage.
- Each future task must have one main goal and one acceptance target.
- Build, signing, installation, deployment, migration, backup, restore, external API requests, and infrastructure operations require separate explicit authorization.
- Each authorized stage must stop immediately after its final report.
- Never execute a `NEXT_STAGE_RECOMMENDATION` automatically.
- Do not modify and retry after a failed stage unless a new task explicitly authorizes it.
- Paid requests must have a fixed maximum count before execution.
- Secrets must remain user-controlled and must not be printed, pasted into chat, logged, or stored in handoff documents.

## 15. C2G10 production application-layer invariants

- `OMBRE_INTERNAL_HOOK_TOKEN` must be configured through an external secret path before the patched Brain may be deployed. It has no documented literal default, its value must never be committed or printed, and it must not reuse the Gateway token.
- `OMBRE_DASHBOARD_SETUP_ENABLED` must be explicitly `false` in production. Setup may be enabled only in a separately authorized first-setup window, and existing password-hash, completion-lock, or pending-reservation state must keep setup closed.
- `OMBRE_MCP_AUTH_REQUIRED` must be explicitly `true` in production. An unconfigured authentication provider must fail closed.
- `OMBRE_MCP_MUTATIONS_ENABLED` must be explicitly `false` in production. Enabling MCP mutations requires a separate explicit authorization and must not add a write token to any tool argument.
- Private Docker networking, host filtering, and lack of a public route are defense-in-depth only; they do not replace application-layer authentication.
- Documentation and configuration may contain variable names, `SET/MISSING`, and explicit booleans only. They must contain no real credential values or real Authorization headers.
- This local source patch is not a deployed image identity. Production remains unpatched until a separately authorized credential, build, immutable-image, deployment, restart, and post-deploy verification chain completes.
- The old Ombre no-touch boundary remains mandatory throughout every future stage.
