# Ingestion profile and supervisor projection: bounded data contract

**DRAFT — 17 November 2026, Asia/Calcutta.** Candidate data contract for independent review; not frozen, implemented, provisioned or accepted as launch authority. Read with [OS access profile](document-ingestion-os-access-profile.md), [launch record](document-ingestion-launch-proof-draft.md) and [publisher boundary](document-ingestion-publisher-db-boundary.md). Scope is one root-profile data shape and one AVCTL-only projection shape. No parser/helper, schema file, account, unit, role, endpoint or runtime setting is supplied here. Existing 14-key launch record and 50 implemented HTTP operations remain unchanged.

## Scope and canonical bytes

The root file is exactly `/etc/hms-ingest/access-profile.json`, root:root0600 inside root:root0700 ancestry. The sole projection in this slice is exactly `profiles/hms-ingest-avctl.json` in the approved image, root:root0444 with root:root0555 ancestry. Other service projections and the decoder/child-launch mechanism remain unfrozen; do not create seven persistent service units from this identity catalogue.

Each file is one canonical ASCII JSON object, sorted keys, compact comma/colon separators, no BOM, indentation, whitespace, final newline, duplicate/unknown/missing keys or alternative escaped spellings. Decoding and canonical re-encoding must reproduce the original bytes. Root bytes are 1..8192; AVCTL projection bytes are 1..2048. No path, command, environment, secret, arbitrary role, writable loader option or own/runtime-manifest hash is accepted as an extra field. No fallback, numeric coercion, NSS expansion or automatic boot refresh.

Common scalar domains: `version` is strict nonboolean integer exactly1; UID/GID is strict nonboolean integer1..4294967294; namespace inode is strict nonboolean integer1..18446744073709551615. UUID is exactly36 lowercase ASCII characters in canonical8-4-4-4-12 hex form and not the nil UUID; SHA256 is exactly64 lowercase ASCII hex characters. Integer lexical spelling excludes fractions, exponents and negative zero, even if mathematically integral. GID arrays are strictly increasing unique numeric lists. All objects below have exactly their listed keys; no nullable member is supplied.

`host` has exactly `{boot_id,namespaces}`. `namespaces` has exactly `{user,pid,cgroup}` using the namespace-inode domain. These are the per-boot host anchors established by the reviewed root installation, not invented fixture values or evidence from a caller's proc view. The static profile does not predict a future unit-private mount-namespace inode; the unchanged launch record's `namespaces.mnt` captures that separately at root launch.

## Exact root-profile shape

Exactly six top-level keys: `version`, `installation_id`, `host`, `groups`, `services`, `execution`.

| Key | Exact value shape |
|---|---|
| `version` | Common version1. |
| `installation_id` | Common nonnil UUID, matching the independently retained guard/installation. Restore epoch stays in the external guard/launch/Control contracts; it is not added to this file. |
| `host` | Closed host object above. New boot or required host-anchor mismatch denies; manual closed-maintenance profile/projection/manifest refresh is required. |
| `groups` | Closed object of exactly the twelve group names below, each mapping directly to a common GID. |
| `services` | Closed object of exactly the seven service names below. Each value has exactly `{uid,primary_gid,supplementary_gids}`. |
| `execution` | Closed object of exactly `hms-ingest-avctl` and `hms-ingest-av`; exact unit/cgroup records below. No decoder/worker/other persistent unit is invented by this map. |

The seven service/private-primary-group names are `hms-preview`, `hms-ingest-bytes`, `hms-ingest-work`, `hms-ingest-avctl`, `hms-ingest-av`, `hms-ingest-image`, `hms-ingest-update`. The five resource-group names are `hms-ingest-guard-read`, `hms-ingest-object-read`, `hms-ingest-scan-ipc`, `hms-ingest-av-ipc`, `hms-ingest-signature-read`. These twelve names are the entire `groups` key set.

| Exact service key | `primary_gid` semantic equality | `supplementary_gids`: exact named set, then sorted numeric values |
|---|---|---|
| `hms-preview` | `groups[service]` | guard-read (1 item) |
| `hms-ingest-bytes` | `groups[service]` | guard-read, object-read (2) |
| `hms-ingest-work` | `groups[service]` | guard-read, object-read, scan-ipc (3) |
| `hms-ingest-avctl` | `groups[service]` | guard-read, scan-ipc, av-ipc, signature-read (4) |
| `hms-ingest-av` | `groups[service]` | av-ipc, signature-read (2) |
| `hms-ingest-image` | `groups[service]` | empty (0) |
| `hms-ingest-update` | `groups[service]` | empty (0) |

Resource names in the last column abbreviate their full `hms-ingest-` names. Each `uid` uses the common UID domain. All seven role UIDs must differ. All twelve named GIDs must differ, including private primary groups versus resource groups, so primary-GID aliasing cannot create hidden resource membership. UID numbers may equal GID numbers because those are separate namespaces. Every `primary_gid` must equal its same-named group value; every supplementary list must equal the precise sorted mapped set, never merely have the right cardinality. Numeric IDs come only from future collision-checked allocation; no real installation values are proposed.

Each `execution` value has exactly `{unit,cgroup,mount_policy}`. The AVCTL values are exactly `hms-ingest-avctl.service`, `/system.slice/hms-ingest-avctl.service`, `unit-private`; the AV daemon values are exactly `hms-ingest-clamd.service`, `/system.slice/hms-ingest-clamd.service`, `unit-private`. The mount-policy label is a closed design requirement, not a systemd directive, namespace implementation or proof that isolation exists. Existing fixed daemon-broker and child-launch acceptance gates remain separate.

## Exact AVCTL own-projection shape

Exactly eight top-level keys: `version`, `service`, `source_profile_sha256`, `installation_id`, `host`, `identity`, `peer_uids`, `execution`.

| Key | Exact value and required source equality |
|---|---|
| `version` | Common version1. |
| `service` | Literal `hms-ingest-avctl`; another service's projection is unsupported by this slice. |
| `source_profile_sha256` | SHA256 of the exact canonical root-profile bytes, not a hash of reparsed or normalised data. |
| `installation_id`, `host` | Exact detached values copied from the validated root profile. |
| `identity` | Exactly `{uid,primary_gid,supplementary_gids}`, equal to `services.hms-ingest-avctl` in the validated root profile. Four strict, sorted unique supplementary GIDs. All three real/effective/saved live UID/GID values must match the respective scalar during future OS checks. |
| `peer_uids` | Exactly `{hms-ingest-work,hms-ingest-av}`, each a common UID equal to that service's root-profile UID. No key for an updater, decoder, other app or general client. The peers must differ from each other and from the supervisor UID. |
| `execution` | Exact root-profile `execution.hms-ingest-avctl` record above. |

Define the deterministic projection `ProjectAvctl(P,B)` from validated root object `P` and its exact canonical bytes `B`: version=1, service=`hms-ingest-avctl`, source_profile_sha256=SHA256(B), installation_id=P.installation_id, host=P.host, identity=P.services.hms-ingest-avctl, peer_uids={hms-ingest-work:P.services.hms-ingest-work.uid,hms-ingest-av:P.services.hms-ingest-av.uid}, execution=P.execution.hms-ingest-avctl. Its output bytes use the canonical encoding above. This is a data mapping specification, not a supplied helper.

The root file contains no projection hashes. Generate its bytes first, then the deterministic AVCTL projection. Before approving or using the manifest, root must recompute `ProjectAvctl(P,B)` and require byte-for-byte equality with the supplied projection; independently hashing two inconsistent files is insufficient. The approved runtime manifest contains the independent raw root-profile hash, raw AVCTL-projection hash and relative immutable image/import-closure entries; neither data file includes the manifest hash. The separately protected fixed unit anchors the approved manifest digest. This avoids profile↔projection↔manifest cycles. A record-supplied hash never chooses a code path or another projection.

Root pre-exec setup validates both files and recomputes the complete canonical projection bytes/equalities before sensitive setup; hashes alone cannot replace this derivation. After drop, the trusted supervisor reads only its fixed manifest-bound projection and approved image policy; it never reopens the root0600 file. Runtime compares projection host anchors/IDs/group set/peers/unit/cgroup to the approved live context, and the unchanged root-owned launch FD separately binds dynamic mount identity plus the same approved manifest. Projection readability supplies metadata only, no key/DB/group/launch grant.

## Three distinct validation layers

1. **Structural schema:** closed keys, exact fixed strings, scalar bounds, nonnil UUID/hash spelling, array cardinality/uniqueness and nested object shape. Candidate machine-readable schemas can check only these claims. Use full-string patterns, not a regex end anchor that also accepts a final newline.
2. **Canonical bytes and semantic consistency:** raw byte caps/ASCII/duplicate-key rejection/canonical lexical integers/re-encode equality, sorted arrays, seven-UID/twelve-GID uniqueness, primary/resource equality, exact supplementary sets, projection/source hash/copy/peer equality and current manifest equality. These remain mandatory even when structural validation accepts an instance. JSON Schema's mathematical `integer` may accept `1.0`; it cannot supply strict wire typing or general dynamic cross-object equality.
3. **Authority and operating-system acceptance:** real allocation/NSS/ownership/ACL/mount/syscall/namespace/procfs/nsfs integrity, trusted root creation and FD custody, current external guard and locked Control/permissions, full irreversible drop, peer process identity, child isolation and postcommit freshness. Schema/data equality proves none of these. No patient projection, registration, readiness or file access follows merely from valid JSON.

## Required independent tests before data-slice freeze

- Structural positives: one synthetic complete root profile, one exact AVCTL projection, minimum/maximum permitted scalar boundary objects; no installed IDs, credentials, patient data or host anchors.
- Structural negatives: every missing/extra key at each level, unknown role/group/peer, wrong fixed unit/cgroup/mount label, nil/uppercase/malformed UUID/hash, booleans/null/strings/zero/overflow numbers, wrong group cardinality/duplicate arrays and nested-array/object substitution.
- Explicit schema-limit counterexamples: integral JSON fractions/exponents, unsorted unique arrays, two equal role UIDs, two named GIDs aliasing, wrong mapped supplementary set with correct size, incorrect peer/source/copy equality, and forged but shape-valid host/OS facts. Include an unchanged source_profile_sha256 with the wrong peer UID even if a candidate manifest hashes that inconsistent projection: root derivation equality must reject it. Do not mislabel schema acceptance as a security success.
- Canonical/semantic future negatives: reordered/escaped/duplicate keys, BOM/non-ASCII/whitespace/newline/8192–8193 and2048–2049 byte edges; every equality/membership/hash/provenance mismatch above.

No executable test or passing result is claimed here. After scoped independent review, coordinator may select this planning contract to create documentation-only schemas/fixtures and run their literal RED/validation checks. "Data-slice freeze" means acceptance of those bounded contract artifacts after the checks, not permission to write a production parser or assert authority. Production parser, real profiles/provisioning, child launch, Control SQL/schema and parent API/native/runtime freeze remain out of scope and open.

## Structural artifact verification —17 November2026

The bounded DOCdata/schema-fixture slice was selected after independent reviews, then verified RED-to-GREEN as recorded in the [execution plan](document-ingestion-profile-shape-plan.md). The [schema](schemas/ingestion-profile-data-v1.schema.json) and [synthetic catalogue](fixtures/ingestion-profile-data-v1.json) assert shape only. This does not freeze/implement the canonical parser, semantic equalities, real profile, OS authority, SQL or parent ingestion. Deterministic projection checks are normative future requirements; schema hashes alone do not prove derivation.
