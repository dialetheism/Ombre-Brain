# RikkaHub per-conversation Ombre session patch

## Frozen base and scope

- official repository: https://github.com/rikkahub/rikkahub.git
- audited upstream SHA: `8dc3ebce3f422a422013097447234e4a97db4210`
- patch: `casper-deploy/patches/rikkahub-conversation-session-header.patch`
- database migration: none
- UI change: none
- provider-specific HTTP-client change: none
- C2C1 build: targeted tests, Kotlin compile, and debug APK assembly passed;
- C2D2B device test: conversation stability, isolation, restart persistence,
  static-header preservation, and no-header absence passed

The upstream checkout remains untouched. C2C1 fetched the exact frozen commit
into an external build copy, initialized the parent-locked Material Color
Utilities submodule, applied the patch with zero offset/fuzz, and verified that
exactly the two expected production files changed. The patched-file digests
matched `PATCH-MANIFEST.yaml`.

The portable build used Temurin JDK 17.0.20 to launch Gradle. The frozen Gradle
daemon criteria then selected JetBrains JBR 21.0.10, while Java/Kotlin bytecode
remained targeted at 17. It also used Gradle wrapper 9.5.0, Android platform 37,
Build Tools 36.0.0, NDK 28.2.13676358, and CMake 3.22.1. The official repository
ignores `google-services.json`, so the external debug copy used a non-production
placeholder file containing no real credential. It is not part of this patch.

## Why this layer owns the identity

`Conversation.id` is a `kotlin.uuid.Uuid`, defaults to `Uuid.random()`, and is
stored as the primary-key string in `ConversationEntity`. Reloading the app
reconstructs the same UUID. `ChatService` keys its in-memory
`ConversationSession` by that UUID, and a fork explicitly creates a new random
conversation UUID. Message text, model credentials, timestamps, and user PII
do not participate in this identity.

At the audited SHA the UUID reaches `ChatService.handleMessageComplete`, but
is lost at the call to `GenerationHandler.generateText`. The generated
`TextGenerationParams` contains only literal assistant/model custom headers;
the OpenAI provider later applies those values verbatim.

## Minimal data-flow change

Before:

```text
Conversation.id -> ChatService
                X GenerationHandler -> literal customHeaders -> provider HTTP
```

After:

```text
Conversation.id
  -> ChatService
  -> GenerationHandler.generateText(conversationId)
  -> generateInternal(conversationId)
  -> resolve configured custom-header templates
  -> TextGenerationParams.customHeaders
  -> existing provider HTTP path
```

The patch touches only:

1. `app/src/main/java/me/rerere/rikkahub/service/ChatService.kt`
2. `app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt`

No request body, model choice, database schema, UUID generator, provider
implementation, or common HTTP client is changed.

## Header behavior

RikkaHub must be explicitly configured with this custom header:

```text
X-Ombre-Session-Id = {{conversation_id}}
```

Only an exact full-value `{{conversation_id}}` is replaced. Existing static
custom-header values pass through unchanged. A value that is exactly another
`{{variable_name}}` fails closed with a non-secret error instead of being sent
unexpanded. Embedded braces in an otherwise static value are not treated as a
template.

The patch never adds `X-Ombre-Session-Id` implicitly. A provider/model without
that user-configured header emits no Ombre session header, so unrelated OpenAI
or OpenRouter providers are not polluted with an Ombre-specific field.

The resulting value is the existing UUID string with no prefix. Therefore:

- the same conversation and every tool-loop step use the same value;
- a different or forked conversation uses a different value;
- an app restart preserves the value through the existing Room row; and
- concurrent conversations do not share mutable global session state.

## C2C1 build result and C2D2B device result

C2C1 re-traced the patched source and called the compiled private resolver from
10 targeted JVM tests. All 10 passed with no failure or skip. The explicit
`:app:compileDebugKotlin` task and `:app:assembleDebug` task also passed.

The selected arm64 artifact is traceable as follows:

- upstream SHA: `8dc3ebce3f422a422013097447234e4a97db4210`;
- patch SHA-256:
  `d878ff5ff0a4641c4cc4c64a15a8b687189392c752994d9b7db5154dcdf05264`;
- APK application ID: `me.rerere.rikkahub.debug`;
- APK version: `2.4.9` (`176`);
- APK SHA-256:
  `6572928a7fad57cf8bf119a8daf910f37fcdc9966d6cf0d0b80ba4b57a383e27`;
- signature: verified Android Debug signature.

The debug package ID differs from the release ID `me.rerere.rikkahub`, so it
installed in parallel without replacing the user's release app. C2D2B then
validated the patched request path against a localhost-only fake OpenAI server
on a private Android device. No raw conversation UUID, UUID hash, message body,
authorization value, or device serial was persisted or reported.

| Case | C2D2B result |
|---|---|
| conversation A, five turns | one stable ephemeral session label |
| conversation B, three turns | one different stable ephemeral session label |
| app force-stop/relaunch | both prior labels remained stable |
| fastest legal A/B switch | no cross-session value reuse |
| existing static custom header | preserved on all eight dynamic-session requests |
| no dynamic header configured | `X-Ombre-Session-Id` was absent |
| exact `{{conversation_id}}` | expanded before the final request |

This resolves the session-identity technical blocker. It does not make the
debug-signed APK a production client. C2E separately freezes those packaging,
signing, Firebase, upgrade/rebase, and migration decisions in
`RIKKAHUB-PRODUCTION-CLIENT.md`; the signed production build and smoke test are
still pending.

## Build, upgrade, and rollback implications

The patch must be applied only to the audited SHA after its SHA-256 is checked.
Any context offset, apply failure, unexpected target file, or extra source diff
is a hard failure. C2C1 built only a debug APK with a local placeholder Firebase
configuration; C2D used that distinct debug package privately, but did not
publish or release-sign it.

For a RikkaHub upgrade:

1. freeze and audit the new upstream SHA;
2. re-trace `Conversation -> ChatService -> GenerationHandler -> provider`;
3. try exact application of both the session and production-packaging patches;
4. regenerate the minimum affected patch if either is no longer exact;
5. rerun targeted tests, compile, production build, and essential device smoke;
6. retain `me.rerere.rikkahub.casper` and the same user-owned signing key; and
7. record every new patch and APK digest before an in-place Casper-app upgrade.

Rollback means a previously retained, correctly signed Casper build only when
its Android version and data schema permit it. It never means uninstalling,
overwriting, or copying the official app. If session propagation is absent,
Casper production traffic must remain disabled; a shared default session is
never an acceptable rollback mode.
