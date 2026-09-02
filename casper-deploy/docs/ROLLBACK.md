# Backup, restore, and rollback design

This document is a static plan. C2B performs no backup, restore, stop, start,
build, APK install, or VPS write.

## What must be protected together

A Casper recovery set must contain:

- /srv/casper-ombre/data
- /srv/casper-ombre/state
- secret-free config/config.yaml
- compose.yaml and Dockerfile.production
- manifest.yaml, PATCH-MANIFEST.yaml, both patch artifacts, and their SHA-256
- the upstream source SHA plus the patched image digest
- a secret inventory/reference, never copied secret values

/data and /state are one logical consistency boundary. /data holds buckets,
Gateway state, embedding/dehydration caches, and other durable indexes. /state
holds raw_events.sqlite, Persona, reminders, memory graph/node state, Portrait,
Dream, and config.runtime.yaml.

Restoring only one path can create a split timeline and is forbidden.

## Consistency policy

Copying live SQLite files with ordinary cp is not a proven consistent backup.
SQLite online backup can create a consistent copy of one database, but it does
not by itself make all SQLite databases plus bucket files globally atomic.

The preferred full recovery point is:

1. stop or quiesce only the explicitly authorized Casper service set; the
   C2G10L candidate contract permits Brain only and never Gateway;
2. confirm no Casper process is writing /data or /state;
3. capture both directory trees in the same backup transaction/window;
4. record the source SHA, config, compose, and manifest;
5. start and validate only Casper.

The old Ombre container, data, Nginx route, cloudflared connector, and hostname
must not be stopped or modified.

If a future online-backup design is required, every SQLite database must use its
online backup API and the plan must separately solve cross-database/bucket-file
consistency. Until then, a Casper-only quiesce is the safer full backup.

## Restore gates

Before restore:

- verify the target namespace is casper-ombre only;
- verify source SHA 284c9c7b0e51a0ba0032c7028f705d72458cb304;
- verify the required Ombre patch SHA-256 and patched source file digests match
  the frozen PATCH-MANIFEST;
- verify the backup contains a matched /data and /state timestamp/set;
- verify that the external root-only credential reference still exists; do not
  copy its values into the /data+/state recovery set;
- verify old Ombre paths are not among restore targets.

After restore:

- verify only the presence and safe metadata of config.runtime.yaml because it
  overrides static config; reading its content requires a separate recovery
  authorization and is not part of the candidate rollback contract;
- verify file ownership for container UID/GID 10001;
- perform no migration until its exact source/target schema is reviewed;
- start only the specifically authorized Casper service; the C2G10L candidate
  contract permits Brain only and leaves Gateway untouched;
- defer health and continuity checks to separately authorized status-only gates
  that discard bodies and do not read raw events, memory, data, databases, logs,
  or state content.

## Configuration-only rollback

For a config/image regression with compatible data:

- retain a secret-free copy of the prior compose/config/manifest;
- select the previously recorded immutable image identity for that recovery
  point; do not rebuild during rollback, and do not treat an OCI revision label
  alone as content proof;
- do not roll back credentials to revoked values;
- quiesce only Casper if the change can affect writers;
- restore the prior config/runtime pair only under its separate recovery
  authorization and restart only the explicitly authorized Brain service;
  Gateway is outside the C2G10L candidate rollback target.

For a schema or data migration regression, restore the matched /data and /state
recovery set. Never combine a new /data with old /state or vice versa.

## Patch rollback boundary

The upstream SHA and each patch digest are separate provenance inputs. A patch
must be removed by rebuilding from the intended clean source/patch set; never
reverse-edit a live container or reuse a mutable tag.

That sentence describes a separately authorized historical source-level
recovery path only. It is not the frozen C2G10L candidate rollback path: the
candidate deployment and rollback contracts forbid rebuilding on the target.

Rolling RikkaHub back to an unpatched trusted APK also removes reliable
per-conversation Ombre session propagation. Casper production access must then
be disabled until an equivalent session path is available; falling back to the
shared Gateway default is forbidden.

Rolling Ombre back to the unpatched upstream restores automatic 30-day resolve
for eligible low-importance dynamic memories. Do not use that image with
Casper data unless the behavior is explicitly accepted. Prefer a reviewed
roll-forward patch; if a runtime defect forces image rollback, quiesce Casper
and restore a matching safe image/config plus the paired /data and /state
recovery point when data semantics require it. Old Ombre remains out of scope.

## Roll-forward preference

When data has advanced after a deployment, prefer a reviewed roll-forward fix.
A destructive data rollback requires explicit user approval and a clear
statement of which Casper-only events would be lost.

## C2G10 hardened Brain rollback boundary

Dashboard setup state is part of the Casper `/state` recovery boundary:

- `.dashboard_auth.json` contains password-hash state and must not be read
  during ordinary rollback checks.
- `.dashboard_setup.complete` is the persistent completion lock.
- `.dashboard_setup.pending` is the exclusive setup reservation.

Rollback, restore, or image replacement must preserve all three paths unless a
separately authorized manual recovery stage names one exact action. No rollback
procedure may automatically delete, truncate, replace, or recreate any of them
to reopen setup. A corrupt or partial auth file remains fail-closed and is a
recovery blocker, not permission to reset credentials.

Rolling Brain back to an image from before the C2G10E hardening patch reopens
the documented internal application-layer gap for memory hooks, first-run
setup, and MCP boundaries until a reviewed hardened image is restored. Private
network placement remains defense-in-depth only. Such a rollback requires an
explicit risk decision and must continue to respect the paired `/data` and
`/state` consistency boundary.

Post-rollback boundary checks must be status-only and discard response bodies.
They must not print credentials, Authorization headers, database or log data,
raw memory, real memory content, or response bodies, and they must not call
chat-completion, memory-returning, mutation, or admin endpoints. Old Ombre
remains outside every restore, rollback, inspection, restart, and fallback
target.

## C2G10L7 frozen Brain-only rollback evidence contract

This is a local documentation contract only. Rollback is never automatic and
requires a new, explicit authorization after the triggering evidence is
reviewed. This document does not authorize Docker, SSH, production access,
deployment, restart, rollback execution, Gateway mutation, old Ombre access, or
C2G10M.

Before any candidate deployment, record only these rollback evidence fields:

- previous Casper Brain container name, or `ABSENT`;
- previous Casper Brain image tag and image ID, if present;
- immediate pre-deploy Compose SHA-256;
- previous Brain service configuration safe metadata digest;
- previous network name;
- previous mount source, target, and read-only metadata only, with no content;
- the separately authorized rollback command contract; and
- evidence that no image, container, file, volume, or tag was deleted, pruned,
  or overwritten.

The rollback/no-interference rules are:

1. Target only `casper-ombre-brain` and only the previously recorded Brain
   identity.
2. Do not rebuild, start dependencies, or issue broad Compose down, up, build,
   restart, or recreate commands.
3. Do not change, rebuild, restart, inspect, or health-check Gateway; do not read
   its logs, environment, tokens, configuration, ports, or mounts.
4. Do not inspect, stop, restart, read, status-check, or use old Ombre as
   fallback, and make no shared-resource or routing assumptions about it.
5. Do not read data, logs, databases, state, memory, or secret content.
6. Do not delete, prune, overwrite, retag, truncate, or recreate images,
   containers, files, volumes, state markers, or credentials.
7. Preserve the paired `/data` and `/state` consistency boundary and all
   dashboard setup state; a mismatch is a hard stop, not permission to repair.
8. Execute no rollback command until its exact Brain-only scope receives a
   separate authorization.
