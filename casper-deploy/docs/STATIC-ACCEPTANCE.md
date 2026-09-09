# C2F1 reproducible-build supply-chain and unsigned-release acceptance record

Date: 2026-08-16 Asia/Shanghai

Scope:

- Ombre main worktree remained at `284c9c7b0e51a0ba0032c7028f705d72458cb304`;
- official RikkaHub source remained frozen at
  `8dc3ebce3f422a422013097447234e4a97db4210` in an external build copy;
- the formal RikkaHub patch digest remained
  `d878ff5ff0a4641c4cc4c64a15a8b687189392c752994d9b7db5154dcdf05264`;
- no VPS, Cloudflare, Docker, model API, Android device, APK install, or real
  credential was used;
- the JDK, Android SDK, Gradle cache, RikkaHub sources, test outputs, and APK
  remained outside this repository.

C2F1 added no device contact, ADB command, APK installation, signing key, real
secret, model request, VPS contact, or Cloudflare contact.

## Production-client packaging acceptance

- recommended application ID: `me.rerere.rikkahub.casper`;
- official/debug IDs retained: `me.rerere.rikkahub` and
  `me.rerere.rikkahub.debug`;
- display name: `RikkaHub Casper`;
- collision-free private URI scheme: `rikkahub-casper`;
- packaging patch SHA-256:
  `af02a95fe468ef592c63601964b98ca3dd11bb43c627d594b76e8c4828eedaf2`;
- expected changed files: 7;
- clean frozen-copy patch check/apply: PASS exact, offset 0, fuzz 0;
- Gradle configuration parsing: PASS;
- production signing inputs: four environment variables, all-or-none, no real
  keystore created;
- strict locked release compile/resource/manifest/package: PASS;
- unsigned arm64 release APK SHA-256:
  `a58ecc6f8485504883d65c686d3d7654bfc34732d691e8746dd0fcc37035ea6b`;
- artifact identity: `me.rerere.rikkahub.casper`, version `2.4.9` (`176`),
  min/target SDK `26` / `37`, and `apksigner` confirms it is unsigned.

The final evidence build was run once in a second clean copy after exact
application of all three RikkaHub patches. An earlier evidence attempt was
discarded because two local Gradle commands briefly overlapped and contended
for the same CMake/Kotlin output directory; it was not treated as a code or
patch failure.

## Reproducibility acceptance

- reproducibility patch SHA-256:
  `81eb44e39a9fc8a099016870ff382980c459b1510cecb6334fb9281c0f388293`;
- changed files: 19;
- exact apply: PASS, offset 0, fuzz 0;
- Gradle 9.5.0 wrapper binary checksum frozen to official SHA-256
  `553c78f50dafcd54d65b9a444649057857469edf836431389695608536d6b746`;
- Gradle strict locking: PASS, ten module lock files plus one settings lock;
- unlocked production configurations reached by `:app:packageRelease`: 0;
- `mavenLocal()` removed; required dependency usage: false;
- sqlite coordinate frozen to
  `com.github.rikkahub:sqlite-android:80cedc8888df2fe1d22d7f9bf8d9287f621624be`;
- sqlite AAR SHA-256:
  `e3e571e470dd76bc13fa2c7d89e7b80d3c63396e5a1235c8bd89dd261d407980`;
- dynamic dependency selectors: 46 before, 0 after;
- pnpm lock supply-chain policy: PASS, 608 resolved packages reused from the
  content-addressable store;
- Gradle binary artifact SHA verification: PASS.

This resolves the identified mutable-input blocker for the validated release
graph. It does not assert byte-for-byte APK output reproducibility across
different machines or timestamps.

The packaging patch removes direct Firebase Analytics/Crashlytics plugins,
dependencies, Koin bindings, and chat-event calls. Core chat does not require a
Firebase project, and the debug placeholder is not production acceptable or
copied. Transitive ML Kit utility artifacts whose Maven names include
`firebase-components`/`firebase-encoders` may remain; that does not re-enable
Analytics, Crashlytics, or a Firebase project.

RikkaHub has no safe selective full-backup import for providers only. Its full
backup is an unencrypted ZIP that can include private settings and database
content. Per-provider QR/text sharing excludes models and conversations but is
secret-bearing Base64 JSON. The accepted initial policy is manual minimum
provider setup, with any provider share treated as a separate controlled secret
transfer. Official private database copying is forbidden and unnecessary.

## Portable build toolchain

- wrapper launcher JDK: Eclipse Temurin `17.0.20`, portable archive;
- Gradle daemon JDK: JetBrains JBR `21.0.10`, required by the frozen
  `gradle/gradle-daemon-jvm.properties` (`toolchainVersion=21`,
  `toolchainVendor=JETBRAINS`) and downloaded into the isolated Gradle home;
- Java/Kotlin bytecode target: `17`;
- Gradle wrapper: `9.5.0`, repository-owned `gradlew.bat`, always
  `--no-daemon`;
- AGP/Kotlin: `9.3.1` / `2.4.10` from the frozen build;
- Android platform: `platforms;android-37.0`;
- Android Build Tools: `36.0.0`;
- platform tools: `37.0.1`, installed by the real task graph;
- NDK: `28.2.13676358`, required by the frozen `workspace` module;
- CMake: `3.22.1`, required by the frozen native debug build;
- all SDK components were contained under the portable toolchain root;
- no system PATH, JAVA_HOME, ANDROID_HOME, registry, Android Studio, winget,
or Chocolatey change was made.

The Gradle daemon JDK archive SHA-256 is
`37f8cd307f79283392d1eef9eb4782838c2b5688cdc35ec26c029cf0fd82fbcb`.
The frozen Web UI task also used its lockfile and the host's existing pnpm
content-addressable store; it did not install or upgrade pnpm globally.

The user accepted the Android SDK license interactively. Package inventory and
the required files (`android.jar`, aapt2, d8, zipalign, and apksigner) were then
verified before Gradle ran.

The official repository intentionally ignores `app/google-services.json`.
Debug compilation therefore used a local-build-only Google Services file with
non-production placeholder values in the external build copy. It was not added
to the patch or bundle and contains no real Firebase credential. The resulting
APK is for private validation only, not publication.

## RikkaHub patch and tests

- exact patch check: PASS;
- offset count: 0;
- fuzz count: 0;
- changed production files: exactly `GenerationHandler.kt` and
  `ChatService.kt`;
- frozen Material Color Utilities submodule commit:
  `6fd88eb3e95ba1d457842e2a2bf847d06b3a018a`;
- targeted JVM tests: PASS, 10 executed, 0 failed, 0 skipped;
- explicit Kotlin compile task: `:app:compileDebugKotlin`, PASS;
- debug APK task: `:app:assembleDebug`, PASS.

The tests called the compiled patched resolver and covered static headers,
exact `{{conversation_id}}` expansion, same/different conversation behavior,
no-header behavior, unrelated static text, unknown variables, multiple
headers, exact UUID formatting, and absent conversation context.

## Debug APK

- selected private-device artifact: `app-arm64-v8a-debug.apk` in the external
  build copy;
- application ID: `me.rerere.rikkahub.debug`;
- release application ID: `me.rerere.rikkahub`;
- version: `2.4.9` (`176`);
- min/target SDK: `26` / `37`;
- signature: verified Android Debug signature;
- size: `81069347` bytes;
- SHA-256:
  `6572928a7fad57cf8bf119a8daf910f37fcdc9966d6cf0d0b80ba4b57a383e27`.

The `.debug` application ID is distinct from the release package. C2D2A then
installed it in parallel on the private test device without replacing the
release package, and C2D2B used only the debug package for runtime validation.

## Ombre policies retained

- `decay.lambda=0`;
- `decay.threshold=0`;
- `decay.auto_resolve_enabled=false`;
- auto-resolve blocker: resolved by the earlier D1-D7 real local fixture;
- freshness policy:
  `ACCEPT_RECENCY_RANKING_WITH_NO_DESTRUCTIVE_MEMORY_MUTATION`;
- freshness blocker: resolved as an accepted ranking-only behavior, not a
  claim that old memories retain a percentage of their content or importance;
- session patch runtime: validated on a private device using only a
  localhost-only fake OpenAI endpoint; five A turns and three B turns remained
  stable and isolated across return navigation, app restart, and the fastest
  legal client-limited switch;
- session technical blocker: resolved; the debug APK remains unsuitable as a
  long-term production client until packaging, signing, upgrade, and migration
  policy is frozen.

## Bundle validation

The standard-library validator parses the bundle without importing Ombre's
runtime config loader. It verifies frozen source/model/patch digests, the
recorded build and private-device runtime facts, fail-closed production-client
state, conservative memory policy,
paths, Compose structure, env references, no local large model, and no secret
material. YAML parsing, Python compile, Git Bash shell syntax, patch scan, and
repository contamination checks all remain mandatory.

The bundle-validation pass described above did not invoke Docker or Docker
Compose. Separately authorized C2G10L194/L195 local evidence is recorded below;
it does not convert this static acceptance record into production or deployment
readiness. C2D2B adds private-device proof of same-conversation stability,
cross-conversation isolation, restart persistence, no-header absence, and
static-header compatibility. It does not mean the debug APK is a production
client, nor does it establish real-provider, VPS, or production deployment
readiness.

## Gateway local baked-config health-smoke evidence

The bounded local status is
`GATEWAY_LOCAL_HEALTH_SMOKE=HEALTH_OK_WITH_CLEANUP_RECOVERY_LOCAL_ONLY`.

C2G10L194 directly started the exact local Gateway candidate image without
Compose, host ports, bind mounts, production paths, or external networking.
The baked-config static contract and image identity matched. Command-defined
dummy environment values and tmpfs paths `/data`, `/state`, and `/tmp` were
used. One container-internal `GET /health` returned HTTP `200` with
`status=ok`; provider requests, OpenRouter contacts, and paid requests were `0`.

L194 nevertheless ended as `ABORT_L194_CLEANUP_STOP_FAILED`, so it is not a
clean single-pass PASS. C2G10L195 subsequently confirmed that the exact
temporary container was already absent and reported
`PASS_CLEANUP_ALREADY_ABSENT`. The combined classification is
`health-success-with-cleanup-recovery`.

The ignored host config was not read or bound. This evidence does not validate
the baked config's content or secret-freedom, production configuration,
Gateway readiness, authentication, model listing, chat, streaming, tools,
providers, persistence, Compose, deployment, restart, or production.

## Remaining deployment blockers

- user-owned long-lived Android signing key, signed production release build,
  certificate/provenance inspection, and a minimal non-destructive
  production-package smoke test;
- user-controlled minimal provider setup or separately authorized per-provider
  secret transfer into the independent Casper package;
- all real credentials and remote helper providers;
- OpenRouter streaming, tools, request fields, and prompt-cache E2E behavior;
- future Casper Gateway hostname and reverse-proxy path policy;
- VPS Docker Compose validation and live RAM/disk headroom;
- fresh registry digest validation, fresh Docker build, dependency install, and
  Docker ignore behavior validation;
- image push `NOT_PUSHED` and deploy `NOT_DEPLOYED`; local Gateway evidence is
  limited to `HEALTH_OK_WITH_CLEANUP_RECOVERY_LOCAL_ONLY`, with no full runtime
  verification;
- final old Ombre baseline revalidation immediately before any VPS mutation.

The current static bundle records a pinned Python base-image digest, a
hash-complete platform dependency lock at
`requirements.production.linux-amd64-py312.lock.txt`, and the current
constraint filename `constraints.production.txt`. Those are static/frozen
provenance only. They do not prove fresh registry state, fresh Docker build
success, dependency-install success, Docker ignore behavior, Gateway runtime
readiness, production readiness, or old-Ombre safety.
## Restart Coverage Boundary Note

For restart-coverage ledger purposes, this document records static expectations only. Preflight and healthcheck references are bounded operator checks that require separate authorization before execution. Restart-coverage validation does not execute scripts, tests, Docker, Gateway, network calls, or runtime services, and does not claim preflight success, healthcheck success, static-acceptance execution success, build success, Docker success, restart success, Gateway runtime readiness, production readiness, deployment readiness, or old Ombre safety. Secret and environment values must remain outside Git and must not be read or printed during static validation.

## Source Identity and Static Gap Note

The active local construction source for this Casper line is
`https://github.com/Yinglianchun/Ombre-Brain.git`, as recorded by the local
repository origin and the committed C2G10 bundle metadata.
`https://github.com/Yinglianchun/Haven-Ombre` exists and appears related,
likely as a mirror, old name, or display variant, but it is not the sole
installed baseline for this line unless future evidence proves that.
`https://github.com/P0luz/Ombre-Brain` remains the historical upstream/original
reference only.

C2G10 contains static handoff/deployment artifacts plus one bounded local
Gateway health observation with cleanup recovery. It does not validate runtime
restart success, full Gateway readiness, production or deployment readiness,
provider/model behavior, dependency-install freshness, or an upstream
merge/chase path.

Future work must not directly pull or merge the P0luz upstream into this line.
Upstream changes require a separate read-only impact audit before any minimal
patch plan. Push authorization remains separate and must name the remote,
branch or ref, and push-only scope before any push is attempted.
