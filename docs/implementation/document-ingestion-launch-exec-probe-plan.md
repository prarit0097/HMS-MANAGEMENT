# Root-owned descriptor across privilege drop and exec: feasibility probe

TEST-ONLY PLAN —15 November2026. Not a production launcher, implementation freeze or authorisation to enable any runtime service. Scope: one ephemeral synthetic forked process under root SSH and server timeout30s/kill-after2s, system /usr/bin/python3.12 (3.12.3, root-owned0755) -I -B, no packages/files/DB/config/service/user creation or app credentials. Only procfs reads, anonymous memfd, owned pipe/process and child-local uid/gid changes. No existing service user is changed. Use numeric65534 only within the disposable child, never launch a daemon. Root parent remains coordinator/reaper.

## Exact scenario and checks before code

Root child constructs only bounded synthetic JSON containing its PID, kernel start ticks and boot UUID. Write it into anonymous root-owned memfd; chmod0400; seal WRITE/GROW/SHRINK/SEAL. Open an O_RDONLY duplicate via fixed /proc/self/fd/<ownedfd>, close writable descriptor. Preserve only the read-only synthetic FD across one exec; no app/DB/key FDs are opened by this probe. Child clears supplementary groups, sets gid/uid65534, then execs the exact pinned Python with isolated/no-bytecode flags and fixed literal verification code under a minimal environment. FD number is an internal argument from fixed probe code, not network input.

After exec assert real/effective IDs65534, supplementarygroups empty and CapEff0; descriptor rootowner/mode0400/O_RDONLY/exactseals/boundedJSON; live self PID/startticks/boot equality. Attempt setuid0 and require EPERM. A newly created sealed synthetic memfd is owned65534 and cannot be fchowned0 (EPERM); this demonstrates why seal+shape alone cannot satisfy a rootowner check. Do not print identity values or system environment; only fixed boolean/result labels. Finally close only owned descriptors and exit. Parent waits exact child, records exit0, closes own resources. Timeout may terminate only the owned probe group on a hang.

## Review gate and limits

Independent review before execution must inspect exact source: procstat comm parsing, root-only actions before drop, Python flags/minimal env, inherited descriptor custody, error cleanup/reaping and no privileged external commands. Do not run with -O or assertions disabled. A failure is recorded, never fixed through shared settings/package/user changes.

This tests root ownership, immutability, FD custody, fixed exec identity preservation and child privilege loss only. It cannot prove full launch authenticity, safe production Python import paths, systemd/cgroup membership/cessation, PID reuse/reboot behavior, real app descriptor isolation, authorised expected-instance install, PostgreSQL commit or arbitrary same-UID compromise resistance. No launcher/guard/scanner/ingestion capability is delivered. Full external-guard/manifest/Control/currentauthority contracts and frozen production leaf remain separate.

Safety amendments before execution: verify getresuid/getresgid real/effective/saved all65534; CapEff/CapPrm/CapInh/CapAmb allzero (bounding set is not a sandbox claim). Explicitly close inherited FD>2 except the synthetic read-only FD before exec; preserve timeout process group. Parse process-stat comm using final right-parenthesis boundary. O_RDONLY is checked separately from seals. Exact-script independent review is required before run.

## Reviewed execution result

At2026-11-15T08:01:40Z the exact source reviewed by an independent specialist ran once with server timeout30s/kill-after2s and isolated non-optimised systemPython3.12.3. Six child assertions/result groups plus parent exact-child reaping were true, exit0; preview service active afterwards. [Evidence](../operations/document-launch-exec-evidence-2026-11-15.json) records scriptSHA256 and scope. Rootowner/O_RDONLY/seals survived uid/gid65534 exec, process PID/start/boot matched and the unprivileged child could neither regainroot nor make its own sealed copy rootowned. Selected FD deliberately remains inheritable after exec; this does not demonstrate safe future-child custody. No full launcher/authenticity/cgroup/SQL/app isolation or release gate is passed by this probe.
