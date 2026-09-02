# RikkaHub Casper production client policy

## Frozen identity and scope

The long-lived patched client is a separate application, not a replacement for
official RikkaHub:

- official package: `me.rerere.rikkahub`;
- validated private debug package: `me.rerere.rikkahub.debug`;
- Casper production package: `me.rerere.rikkahub.casper`;
- display name: `RikkaHub Casper`;
- private callback/shortcut URI scheme: `rikkahub-casper`.

The production package ID is distinct from both existing IDs. Android therefore
gives it separate private storage, and it can coexist with the official app by
design. The package ID is a permanent identity: after the first production
installation, upgrades must use this same ID and the same signing key.

The packaging artifact is
`casper-deploy/patches/rikkahub-casper-production-packaging.patch`, SHA-256
`af02a95fe468ef592c63601964b98ca3dd11bb43c627d594b76e8c4828eedaf2`.
It is based on RikkaHub
`8dc3ebce3f422a422013097447234e4a97db4210`, applies after the separately
frozen session patch, and changes seven packaging/runtime-integration files. It
does not duplicate or alter the conversation-session implementation.

## Packaging strategy

C2E selects the existing release variant with a dedicated, mandatory Casper
build-configuration patch. A product flavor would create a larger variant
matrix without adding isolation, while an ad-hoc command-line application ID
override would make identity too easy to omit. The patched tree itself therefore
cannot accidentally build the official package ID.

The patch changes only packaging integrations:

- production application ID and display name;
- the callback and shortcut URI scheme, avoiding chooser ambiguity with the
  official app;
- production signing inputs;
- Firebase Analytics/Crashlytics removal.

It was checked and applied to a clean frozen copy with zero offset and zero
fuzz. During C2F1, a real compile failure exposed one missing Analytics removal
in `ViewModelModule.kt`, and the original signing block exposed an unusable
empty release signing configuration. Both were corrected in the formal
packaging patch, its digest was re-frozen, and the complete strict locked
release build then passed from a second clean copy. With all signing variables
unset, Gradle now deliberately produces unsigned release APKs; it neither
creates nor substitutes a signing identity.

## Signing boundary

The production app must use one user-owned, long-lived Android signing key.
C2F1 did not create a keystore or any signing secret. A suitable future local
secret directory is:

`C:\Users\LENOVO\Documents\ChatGPT\Casper-RikkaHub-Secrets\`

That directory, its backups, and all passwords remain outside Git, this bundle,
VPS storage, chat output, and ordinary source archives. The packaging patch
accepts exactly four process-environment inputs:

- `CASPER_RIKKAHUB_KEYSTORE_PATH`;
- `CASPER_RIKKAHUB_KEYSTORE_PASSWORD`;
- `CASPER_RIKKAHUB_KEY_ALIAS`;
- `CASPER_RIKKAHUB_KEY_PASSWORD`.

All four must be set together for a signed production build. A partial set is a
hard configuration error, and the keystore path must resolve to a regular file.
No secret value belongs in `local.properties`, the patch manifest, build logs,
or command-line arguments. Losing this key prevents in-place upgrades; changing
it requires a new application identity and is not an acceptable routine update.

## Firebase policy

Frozen source used the Google Services and Crashlytics plugins, direct Firebase
Analytics/Crashlytics dependencies, Koin registrations, and a small number of
chat-event analytics calls. No Firebase Messaging, Remote Config, or Firebase
Auth use was found. Analytics and crash reporting are not required for core
provider, model, conversation, or OpenAI-compatible request behavior.

Casper production policy is therefore no Firebase project and no Firebase
Analytics/Crashlytics telemetry. The packaging patch removes the app-level
plugins, direct dependencies, registrations, and event calls. The root plugin
aliases may remain unapplied, so they do not enter the app. ML Kit barcode
scanning still has transitive utility artifacts whose coordinates contain
`firebase-components` or `firebase-encoders`; these are ML Kit transport/support
libraries, not approval to initialize Analytics/Crashlytics or use a third-party
Firebase project.

The old debug placeholder is not production acceptable and is not copied into
the Casper package. With the packaging patch, core chat no longer needs that
placeholder, and its absence is intentional rather than a runtime fallback.

## Provider migration

RikkaHub's full backup is an ordinary, unencrypted ZIP. It always contains a
serialized settings document and can include the database, files, conversations,
prompts, and other personal data. It is not a provider-only migration and must
not be used as a casual bridge between the official and Casper packages.

Source does provide per-provider text/QR sharing. That payload excludes models
and conversations but includes provider configuration such as API keys, base
URLs, and custom headers. It is Base64-encoded JSON, not encryption. It is safe
only as an explicit, user-controlled secret transfer followed by recreating the
required models in the Casper app.

Initial recommendation is to manually create only the minimum Casper provider
and model. For many providers, a later separately authorized migration may use
one-provider-at-a-time sharing with secret-handling controls. Direct copies of
the official app's private database, `run-as`, root access, or ADB data export
are forbidden and unnecessary.

## Upgrade and rebase policy

Never build `master`, `latest`, or an unrecorded checkout automatically. For
each official upgrade:

1. freeze the new upstream commit SHA;
2. re-audit whether upstream now supplies equivalent conversation-scoped
   header expansion;
3. verify both patches with exact apply and reject every offset or fuzz;
4. if either patch is no longer exact, regenerate the smallest reviewed patch
   instead of forcing or fuzzing it;
5. rerun header tests, Kotlin compile, production APK build, artifact inspection,
   and the essential same-conversation/different-conversation device smoke test;
6. retain `me.rerere.rikkahub.casper` and the same user-owned signing key; and
7. record the new APK digest before an in-place Casper-app upgrade.

Rolling back means installing a previously retained, correctly signed Casper
version only when Android version rules and its data schema permit it. It never
means changing or uninstalling the official app.

## Provenance and reproducibility

Every production artifact record must bind together:

- RikkaHub upstream SHA;
- session patch SHA-256;
- packaging patch SHA-256;
- reproducibility patch SHA-256;
- Gradle, AGP, Kotlin, JDK, Android SDK/Build Tools, NDK, and CMake versions;
- production APK SHA-256 and package metadata; and
- signing-key identity by a non-secret certificate fingerprint recorded during
  C2F2, never by private-key material.

C2F1 adds
`casper-deploy/patches/rikkahub-casper-build-reproducibility.patch`, SHA-256
`81eb44e39a9fc8a099016870ff382980c459b1510cecb6334fb9281c0f388293`.
It freezes the production graph with Gradle strict dependency locking (ten
module lock files plus the settings lock), removes `mavenLocal()` from
resolution, and pins the Gradle 9.5.0 binary distribution to official SHA-256
`553c78f50dafcd54d65b9a444649057857469edf836431389695608536d6b746`.

The mutable `com.github.rikkahub:sqlite-android:-SNAPSHOT` selector is replaced
by full upstream commit
`80cedc8888df2fe1d22d7f9bf8d9287f621624be`. The resolved AAR is additionally
verified as
`e3e571e470dd76bc13fa2c7d89e7b80d3c63396e5a1235c8bd89dd261d407980`.
The old short snapshot resolution and the full-commit artifact were byte-for-
byte equal during the audit, so this freezes the selected implementation
without an unsolicited library upgrade.

The Web UI had 45 top-level semver range selectors; together with the sqlite
snapshot, the pre-freeze dynamic count was 46. Package versions are now exact,
pnpm 11.19.0 is pinned with strict package-manager enforcement, and the frozen
pnpm lock passed the local supply-chain policy check. The post-freeze dynamic
count is zero. Gradle artifact verification checks JAR/AAR binaries by SHA-256;
metadata hashes are intentionally not required, while strict locks freeze the
selected metadata graph.

A clean-copy `:app:packageRelease` completed successfully under strict locks
and verification. The arm64 unsigned APK is stored only in the external
BuildTools tree and has SHA-256
`a58ecc6f8485504883d65c686d3d7654bfc34732d691e8746dd0fcc37035ea6b`.
This resolves dependency-input drift for the validated graph; it is not a claim
of byte-for-byte APK reproducibility across machines or timestamps. A signed
production artifact and user-owned key remain C2F2 work.

## Session compatibility

The session patch operates on persisted `Conversation.id` and model/provider
custom-header resolution. Application ID, signing key, Firebase removal, and
the release variant do not participate in that data flow. It is therefore
compatible with the production variant by design, while the first production
APK still requires a minimal local/device smoke test before it becomes the
long-term client.
