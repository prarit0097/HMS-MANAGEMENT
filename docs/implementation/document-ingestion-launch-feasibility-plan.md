# Launch primitive feasibility probe

Status: bounded TEST-ONLY probe plan, 15 November2026 IST; no production implementation or parent freeze.

Purpose: test standard Linux primitives on the existing pinned host before selecting launch provenance. Authorised scope is a short isolated synthetic Python process via root SSH; no files, DB, key, patient data, network listener, unit, service or config mutation. Root credentials stay in SSH. Anonymous memfd holds only literal synthetic bytes; one direct child reads inherited FD and exits. No package install or persistent resource. Reuse neither app settings nor live secrets.

Preflight read-only actual host: Linux6.8.0-90-generic, systemd255 (255.4-1ubuntu8.18), pinned Python3.12.3, cgroup2fs. Existing preview symlink e7ab28f and hms-preview.service active observed. This is platform inventory only, not full release attestation.

## Assertions before execution

1. Create anonymous memfd using MFD_ALLOW_SEALING and CLOEXEC; write only fixed synthetic bytes. Add WRITE/GROW/SHRINK/SEAL seals, read them back and require equality. Literal write and truncate must fail with EPERM. Seal checks establish immutability, not trusted-root provenance.
2. Open pidfd for self, require descriptor is non-inheritable, and close it in finally. This tests syscall availability, not task reaping/cessation or executable attestation.
3. Fork one child, observe its PID differs from parent while it can read the same inherited bytes. Explicitly demonstrate descriptor possession alone does NOT identify the approved process. Child reports fixed bounded PASS/FAIL via exit code, exits with os._exit, parent waits exact PID in finally. No exec, cgroup mutation or background daemon. Exceptional timeout may terminate only the owned probe process group.
4. Require memfd non-inheritable across exec flag and close it in finally. This flag does not prevent fork inheritance. Do not claim descriptor custody across exec/fork or arbitrary same-UID compromise is solved.

## Review and stop conditions

Independent review must check scope, child cleanup/reaping, no secret/content output, bounded output and failures before run. Use server-side `timeout --kill-after=2s 30s <pinned-python> -I -B -` without `-O` to bound the owned process group and preserve assertions; client SSH connect timeout alone does not bound execution. root script must catch child failure and still wait exact child. No service probing beyond initial active status. Run once; any failure stays a recorded feasibility failure, not a reason to install dependencies or change host settings. After run check service still active. Record exact result and limitations; this is not RED/GREEN for a production module and cannot authorise readiness/launch/bootstrap/schema/ingestion.

Remaining gates: root descriptor provenance/launch handshake, process lifetime versus scanner generation mapping, publisher DB privilege enforcement, actual stopped child/exec/PID namespace/race/cessation behavior, cross-contract schema/API agreement. These probes prove no access-control property.

Pre-execution independent safety review accepted the synthetic script subject to server-side group timeout, isolated non-optimised Python and the exceptional-owned-signal clarification above. Root applied those conditions before execution. No production code is authorised by this review.

## Executed result

The reviewed exact synthetic script (SHA256 in [evidence](../operations/document-launch-primitive-evidence-2026-11-15.json)) ran once through pinned Python under the server-side owned-process-group timeout. All seven reported checks were true, exit0; service active before/after. This positively demonstrates sealed-memory mutation denial and negatively demonstrates fork possession is not instance identity. No launcher/provenance/DB/production acceptance follows. See [memfd_create](https://man7.org/linux/man-pages/man2/memfd_create.2.html) and [Python3.12 os](https://docs.python.org/3.12/library/os.html#os.pidfd_open).
