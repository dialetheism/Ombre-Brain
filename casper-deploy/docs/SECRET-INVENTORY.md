# Secret inventory

The populated secret file is future state, not part of this bundle. Its planned
path is /etc/casper-ombre/casper.env, owned by root:root with mode 0600.
Do not print it, commit it, include it in ordinary source backups, or paste its
values into chat.

| Deployment variable | Container/source variable | Consumer | Initial status | Purpose | Rotation impact |
|---|---|---|---|---|---|
| CASPER_OMBRE_GATEWAY_TOKEN | OMBRE_GATEWAY_TOKEN | Gateway only | Required | Bearer auth for RikkaHub/OpenAI-compatible clients | Update Gateway env and client together using a controlled overlap plan |
| CASPER_OPENROUTER_API_KEY | CASPER_OPENROUTER_API_KEY | Gateway only | Required | OpenRouter chat upstream | Gateway-only restart/recreate; no Brain data migration |
| CASPER_DEHYDRATION_API_KEY | OMBRE_API_KEY | Brain and Gateway | Required | Compression, merge, tagging, memory helper chat calls | Both services receive it; validate manual write paths after rotation |
| CASPER_EMBEDDING_API_KEY | OMBRE_EMBEDDING_API_KEY | Brain and Gateway | Required | Remote embeddings | Both services receive it; verify query and write embeddings |
| CASPER_RERANKER_API_KEY | OMBRE_RERANKER_API_KEY | Brain and Gateway | Optional, disabled | Remote /rerank API | Enable only with matching base URL/model and then recreate both |
| CASPER_PERSONA_API_KEY | OMBRE_PERSONA_API_KEY | Primarily Gateway; Brain can inspect/administer state | Required | Minimal post-reply relationship/session-affect evaluation | Recreate both; verify state continuity without exposing event content |
| CASPER_REFLECTION_API_KEY | OMBRE_REFLECTION_API_KEY | Brain worker | Optional, disabled | Reflection/daily impression | No effect until separately enabled |
| CASPER_PORTRAIT_API_KEY | OMBRE_PORTRAIT_API_KEY | Brain worker | Optional, manual-only | Explicitly invoked Portrait maintenance; background generation remains disabled | No effect until a separately authorized manual generation; never needed for per-turn injection |
| CASPER_DREAM_API_KEY | OMBRE_DREAM_API_KEY | Brain/Gateway Dream engine | Optional, disabled | Dream generation | No effect until separately enabled |
| CASPER_DASHBOARD_PASSWORD | OMBRE_DASHBOARD_PASSWORD | Brain Dashboard | Optional, unexposed | Dashboard API login | Brain-only restart/recreate; never route Dashboard first |
| CASPER_CHATGPT_OAUTH_CLIENT_SECRET | OMBRE_CHATGPT_OAUTH_CLIENT_SECRET | Brain MCP OAuth | Optional, disabled | OAuth client authentication | Coordinate provider/client and Brain; no partial activation |
| CASPER_CHATGPT_OAUTH_ACCESS_TOKEN | OMBRE_CHATGPT_OAUTH_ACCESS_TOKEN | Brain MCP OAuth | Optional, disabled | OAuth bearer validation | Rotate with future MCP clients |
| CASPER_CHATGPT_OAUTH_REFRESH_TOKEN | OMBRE_CHATGPT_OAUTH_REFRESH_TOKEN | Brain MCP OAuth | Optional, disabled | OAuth refresh flow | Rotate with access token/client configuration |

Non-secret provider selectors live in the same env file for operational
convenience:

- CASPER_DEHYDRATION_BASE_URL and CASPER_DEHYDRATION_MODEL
- CASPER_EMBEDDING_BASE_URL and CASPER_EMBEDDING_MODEL
- CASPER_RERANKER_BASE_URL and CASPER_RERANKER_MODEL
- CASPER_PERSONA_BASE_URL and CASPER_PERSONA_MODEL
- disabled Reflection/Dream and manual-only Portrait base URLs and models
- OAuth client ID, public base URL, and protected hosts

The OpenRouter chat model is frozen in the secret-free config as
openai/gpt-5.4. It is not an environment variable and is not a credential.

Provider credentials are deliberately separate. Reuse is technically possible
only when one provider and credential is authorized for multiple APIs, but it
must be an explicit user decision rather than the deployment default.

Brain and Gateway receive only the variables their current source can consume.
Docker stores injected environment values in container configuration visible to
root/Docker administrators; root access remains a credential boundary.

Brain deliberately does not receive the Gateway client credential. Therefore
the initial Dashboard-to-Gateway admin bridge is disabled rather than silently
sharing that secret.

## Android production-signing secrets

The following variables are build-time inputs for the separate RikkaHub Casper
Android client. They do not belong in `/etc/casper-ombre/casper.env`, Compose,
either Ombre container, or the VPS:

| Build variable | Consumer | Status | Purpose | Rotation impact |
|---|---|---|---|---|
| CASPER_RIKKAHUB_KEYSTORE_PATH | Local Android release build only | Future required | Path to the user-owned long-lived keystore | Moving the file is safe if the key is unchanged; losing it prevents in-place upgrades |
| CASPER_RIKKAHUB_KEYSTORE_PASSWORD | Local Android release build only | Future required | Open the keystore | Secret rotation must preserve access to the same signing identity |
| CASPER_RIKKAHUB_KEY_ALIAS | Local Android release build only | Future required | Select the signing key | Changing to a different key breaks upgrade compatibility |
| CASPER_RIKKAHUB_KEY_PASSWORD | Local Android release build only | Future required | Use the selected signing key | Secret rotation must preserve the same signing identity |

C2E created none of these values or files. The recommended future secret root
is `C:\Users\LENOVO\Documents\ChatGPT\Casper-RikkaHub-Secrets\`, outside this
repository. Values are injected only into the authorized local build process
and must not appear in command-line arguments, build logs, Git, the bundle,
chat output, or backups that leave the user's control.

RikkaHub per-provider QR/text export is also secret-bearing because its Base64
payload can contain API keys and custom headers. Base64 is not encryption. Such
an export is never a general backup artifact and requires a separate,
user-controlled migration step.
