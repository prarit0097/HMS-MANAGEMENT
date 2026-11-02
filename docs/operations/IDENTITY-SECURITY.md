# Identity security operations — source design and release gates

This runbook accompanies [the identity security contract](../implementation/identity-security-contract.md). The original259PostgreSQL/25subtests and64frontend results describe its bounded source slice. Identity controls were deployed26October and remain included in recorded833ffc67/core0009, verified1November: enrolled-owner password/TOTP challenge, pending-session denial, secure session/CSRF/logout and actual database+retained-key restoration passed. See [latest preview evidence](document-admission-preview-evidence-2026-11-01.json). This2November MD review adds no runtime test. Browser/keyboard/staff, owner phone authenticator import, reviewed human recovery and full hospital release remain open; do not enter real data.

## Dedicated encryption material

HMS_MFA_ENCRYPTION_KEYS is a comma-separated Fernet keyring, first key for encryption, retained keys for decryption. Generate cryptographically random Fernet keys using the pinned cryptography runtime in the intended private environment. Do not use Django SECRET_KEY, a password, a committed development constant or an automatically regenerated startup key. Keep values in the deployment's private secret store/environment, out of shell history, logs, Git and screenshots. Test settings generate fixture keys in memory; they are not deployment credentials.

Encrypted payloads bind version/purpose/user/device or enrollment identity, preventing ciphertext moved to another row from validating. A missing/incorrect key fails closed503; it must not disable MFA, accept a password-only login or count as an incorrect user proof. Storage outages likewise require operator investigation. A successful health check alone does not prove usable factor keys. Authenticate a private synthetic account in staging and verify enrollment, login and replacement with actual configured keys before cutover.

Back up encryption keys separately from database backups with restricted, documented recovery ownership. A database copy alone cannot recover factors; a key without the database is not a backup. Test isolated restoration with synthetic factors. Existing root-only local plaintext Hostinger dumps do not provide encrypted off-host disaster recovery and must not be represented as a complete recovery strategy.

## Rotation and loss

Retain old keys while old ciphertext exists. Provision a new primary key plus old decryption keys; verify decryption, new enrollment and old-account login in staging. A bulk re-encryption command is not delivered by this slice. Do not remove old keys until every active and pending encrypted record is deliberately migrated or expired and an isolated restoration has been tested. Never edit encrypted database fields by hand to remove a second factor. If keys are lost, preserve database/backups and stop privileged changes; a reviewed out-of-band recovery process is a hospital-release prerequisite.

## Individual use

Staff first sign in with an individual account, open Account security, confirm current password and configure their authenticator using the locally displayed setup key. The secret is shown only during setup; never send it to an external QR generator. Enter a current six-digit code to confirm. Save the ten one-use recovery codes privately before acknowledging the result. App/browser storage does not retain these plaintext codes. Losing the response does not make it replayable; regenerate with fresh proofs when authorised.

After enrollment a correct password reaches only a short-lived second-factor challenge. Authenticator and unused recovery code are supported; the same accepted authenticator time step cannot authorise another action. Staff may need to wait for the next code before a further sensitive action. A challenge expires after five minutes and is bound to its browser session; starting a new login invalidates the earlier challenge. Cancel/back signs out the pending session. Recovery codes are single use and always require a password stage or current-password confirmation.

Replacing/disabling a factor, changing password, rotating codes and revoking sessions require current proofs. A master administrator cannot bypass a colleague's factor through the staff-access panel. Organisation suspension removes that hospital's grants but does not globally disable an identity in another organisation. Individual session revocation and organisation grant suspension are separate operations.

## Policies and limitations

HMS_REQUIRE_ADMIN_MFA defaults true outside development. Privileged configuration/staff writes require active enrollment and proof no older than fifteen minutes in addition to current permissions, network policy and CSRF. Self setup/step-up remains accessible. Development optout supports synthetic tests and is not a safe hospital production default. Do not weaken IP rules or expose the origin to resolve an MFA failure.

Account/challenge/shared trusted-IP limits protect second-factor attempts across workers. A new challenge does not clear account failure history. Wait the reported interval after429; do not reset credits, clear counters or forge forwarded headers as a workaround. Operator monitoring/retention/cleanup remains separate work; never log raw passwords, factor codes, recovery codes, secret URIs or encrypted key values.

Session epochs invalidate prior sessions/challenges after sensitive changes. Locked security/platform writes serialize with revocation; ordinary requests already in flight may finish. This is not universal instantaneous cancellation. TOTP is susceptible to phishing; WebAuthn/federated identity, reviewed human recovery, immutable read auditing, notification delivery and real staff acceptance are separate release gates. No breach-proof or full production-readiness assurance is made.

## Completed restricted-preview verification and remaining release gates

- [x] Bounded source negative/lifecycle/race tests and dependency/schema/drift checks recorded; latest full source CI1530PG/6SQLite-onlyskips/168subtests and132frontend passed.
- [x] Dedicated private preview keyring provisioned; genuine enrolled-owner password/TOTP/session checks and actual retained-key factor decryption after isolated restore verified in the latest receipt.
- [x] Actual HTTPS/cookies/CSRF/trusted-network enforcement, shared identity attempt controls and logout checked on the restricted preview.
- [x] Operator database+key restore and source-only rollback compatibility rehearsed; separate keys retained privately. No claim of encrypted off-host backup follows.
- [ ] Actual live browser/keyboard/staff walkthrough and owner phone authenticator import.
- [ ] Reviewed human recovery/incident ownership, key rotation/loss drill and encrypted off-host disaster recovery.
- [ ] Comprehensive read/immutable audit, broader independent security/load/usability review and hospital cutover approval.

Completed items are backed by dated runtime/source receipts, not inferred from GitHub push. Future deployments must recheck current configuration, keys and state; do not replay enrollment or consume recovery codes merely to reproduce an old receipt.
