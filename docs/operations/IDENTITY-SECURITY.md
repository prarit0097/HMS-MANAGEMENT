# Identity security operations — source design and release gates

This runbook accompanies [the identity security contract](../implementation/identity-security-contract.md). Authenticator/source implementation is checkpointed WIP with236actualPostgreSQL/25subtests and64frontend-agent tests, but known proof-age-after-lock and scenario coverage/final review remain; these instructions do not claim deployment or account enrollment. Existing Hostinger preview47b3618uses its original password/session controls. Do not add real hospital data until full release gates pass.

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

## Verification before a future deployment

- [ ] Pin/install dependencies in an isolated candidate runtime; validate OpenAPI and migration drift.
- [ ] Run API/component tests and actual PostgreSQL races for factor/code consumption, challenge generation, first-profile creation and revoke/write ordering.
- [ ] Provision a private dedicated keyring and prove correct-key/wrong-key/retained-key recovery in staging without exposing material.
- [ ] Confirm HTTPS/cookies/CSRF/trusted-IP policy and shared limits on actual deployment paths; complete authenticated browser/staff walkthroughs.
- [ ] Test isolated encrypted database/key restoration, document human recovery and incident ownership, approve migration/rollback and deployment separately.

These unchecked deployment gates cannot be inferred from source tests or a GitHub push. Update this runbook with actual evidence when performed.


Checkpoint coordinator repeat: frontend63passed/1failed (resource-administration stale-bed-edit test could not find Edit bed101 within timed wait); agent earlier64passed. Coordinator typecheck/build still passed. Affected test isolated rerun is recorded in ledger/handoff; this does not establish a repaired full suite. No source changes after stop. Investigate/repeat full suite after cooldown before marking identity delivered.
