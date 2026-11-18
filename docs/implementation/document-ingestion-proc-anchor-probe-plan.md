# Own-task descriptor after drop and fixed exec: feasibility probe

TEST-ONLY PLAN —18November2026. Review before source/execution; not the production leaf freeze. Implements only a synthetic kernel question from [proc anchor draft](document-ingestion-proc-anchor-contract.md): can a root-pinned own-task O_PATH directory remain usable after the same process drops privileges and execs, and does a forked child independently mismatch the pinned parent task? No production observer, authority object, registration, namespace attack test or readiness follows.

## Fixed scope and pre-code checks

One SSH stdin process under existing root authorisation, server timeout30s/kill-after2s; isolated existing /usr/bin/python3.12 -I -B, no optimisation, no package/file/service/user/group/DB/config/key/profile/policy change. Only owned anonymous memfd, owned fork/exec processes and pipes; numeric65534 applies inside a disposable child with no supplementary groups, never changes an existing account. Do not touch global mounts, unshare namespaces, systemd or live app credentials. Root parent reaps exact children; no unrelated PID/group signalling. Preserve current preview symlink/service before/after with read-only observations. Failure never authorises a host permission or package change.

Root child captures direct PID and robust stat-startticks (final right-parenthesis boundary) and task-directory device/inode from its exact /proc/<ownpid>. Open own-task O_PATH|O_DIRECTORY|O_NOFOLLOW descriptor and reserveFD4 before drop. Synthetic rootowned0400 sealed readonly recordFD3 contains only the initial PID/startticks and task dev/inode for this probe; this is NOT the production14-key record or an approved transport addition. Make onlyFD3/FD4 inheritable across one literal fixed exec; close all inheritedFD>2 except those handles without enumerating or printing their contents. Clear supplementarygroups; set real/effective/savedGID+UID65534. No rootcredential/socket is opened. Root-created record remains independently root-owned; task ownership is allowed to change.

Postexec fixed code sets CLOEXEC on both immediately, checks finalIDs/groups and CapEff/CapPrm/CapInh/CapAmb zero using bounded own-task status reads, exact descriptor access/type/seals and synthetic fixedrecord, task dev/inode continuity and direct ownPID/native-threadID/startticks equality. No claim of filesystem type/nsfs/openat2/no-cross-mount acceptance; these literal relative reads answer feasibility only. Attempt setuid0 must failEPERM. All reads are capped16384bytes+overflow byte; no values/PIDs/UUIDs/paths/rawproctext logged. Failures are fixed labels only.

Then fork exactly one intentionally inherited-handle child. It reads parenttask via FD4 but direct getpid/native-threadID must differ from recordedPID, proving why inherited handle possession is insufficient. Child closes owned handles and exits; parent waitpid reaps exactchild. A separate fixed secondexec check with close_fds=False proves CLOEXEC removesFD3/FD4; no arbitrary command/argv/environment, timeout5s. Keep subprocess isolated in the existing outer timeout group. Finally closeFD3/FD4 and exit; root parent waitpid exact originalchild. Only closed boolean/result labels plus interpreter/kernel versions may appear in public evidence. Source hash and actual result recorded; timeout fault not claimed unless actually triggered.

## Review/acceptance gates

- [x] Independent scenario/threat review accepts scope before executable source.
- [ ] Exact source review covers fixedexec/import/env, FD collision/reservation, private inheritedhandle closure, robuststatparse, readbounds, drop, fork/gettid, secondexec and owned timeout/reaping before VPS run.
- [ ] Actual isolated execution records real success/failure and preview before/after; no weakening on failure.

This is a feasibility experiment, not RED/GREEN production test or malicious proc/nsfs/mount/cgroup/systemd/SQL/realrole/credential custody acceptance. Actual kernel syscall ABI, hostile-view traversal, namespace handles, original-thread enforcement and Control commit/guard composition remain unfrozen. No new HMS user capability or app deployment is implied. The consumed production leaf must still wire its real startup path and pass independent literalRED/review/Linux/PostgreSQL/release gates.

Pre-source security review accepted this bounded experiment; secondexec must require EBADF specifically for both handles (not any error). Source/execution gates remain pending.

## Saved source / visibility hold

18November2026: independent scenario/security scope review accepted the bounded experiment, requiring explicitEBADF for both secondexec handles. Ignored local source saved with finalSHA2561f92c72849e6b05f2fd2078710f8e96e3950b9d7ea66f9df553471acb7744966; allthree literal source layers syntax parsed/compiled only. Final source review is PENDING (agent pending_init interrupted at usage visibility hold), including added fixed preview before/after read-only comparison. No VPS execution/probe result/deployment. Two new authenticated snapshots expose only duration10080 used0 and no300window; pause substantial phases, do not invent fivehour recovery or a new330minute deadline. [Checkpoint](../operations/document-proc-anchor-probe-checkpoint-2026-11-18.json). Resume exactsource review before the test, not repeated design or completed checker.
