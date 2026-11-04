# Investigation playbook

Use this exercise to triage a synthetic finding, record your decision as an analyst, and verify it as a viewer. The tracker records investigation decisions. The exercise uses fabricated evidence and performs no cloud actions.

## Set up the exercise

1. Start the [local Compose application](../README.md#start-the-local-application) and create the analyst account. For the expected starting state, use a fresh synthetic database. Seeding again preserves any existing notes and status changes.
2. Create a viewer from the repository root. Enter a distinct local password when prompted.

   ```text
   docker compose exec api flask --app tracker:create_app create-user viewer --role viewer
   ```

3. Open <http://localhost:5173>, sign in as the analyst, and confirm the **Synthetic data** badge is visible.

## Triage repeated console sign-in failures

1. In **Findings**, select **New** for Status, **Critical** for Severity, and `cloudtrail` for Source. Open **Repeated failed console sign-ins**. Confirm the source event is `synthetic-event-001` and the region is `ap-southeast-1`. The [seed record](../database/seed/findings.json) describes 23 failures across three fabricated addresses in eight minutes.
2. Under **Update status**, set **Move to** to **Investigating** and select **Save status**. If the row disappears from the list after you close the details, clear the **New** filter or switch it to **Investigating**.
3. In **Investigation notes**, add the note below. It separates the observed failures from the question of whether an account was accessed.

   > Synthetic triage: 23 failed console sign-ins in eight minutes across three fabricated addresses. The finding records failures only. In this exercise, check for a successful sign-in or account changes in the surrounding window before closing the case.

4. The seeded finding supports keeping the case **Investigating** while those checks are outstanding. To practice closure, use this additional exercise assumption: a simulated identity review found zero successful sign-ins and zero account changes in that window, and the exercise owner closed the case. Move to **Resolved**, enter the reason below, and select **Save status**.

   > Synthetic exercise: the simulated review found no successful sign-ins or account changes in the reviewed window. The exercise owner closed the case.

Use **Dismissed** when the finding should be excluded from active investigation and record the reason. If new evidence changes the decision, move a resolved or dismissed finding back to **Investigating** and add a note explaining what changed. Notes are append-only through the app, so record corrections in a new note.

## Review the record as a viewer

1. Check **Activity history** in order. A fresh run with closure shows a status change to investigating, a note addition, and a status change to resolved. Each entry identifies the actor and timestamp. The note body appears under **Investigation notes**.
2. Sign out and sign in as the viewer. Find the same row with the **Resolved** filter, or use **Investigating** if you left the case open. Verify the note and history are visible and the note section says **Viewer access is read-only**. Status and note editing controls are absent.
3. For a developer review, the API tests check viewer write rejection and verify a failed audit write rolls back the note. The [API contract](api-contract.md#pagination-for-notes-and-history) describes the note ID and request ID available in audit responses.

## Recover from common failures

| Symptom | What to check |
|---|---|
| The session expires | Sign in again and reopen the finding. Verify the current state and notes before retrying a write. |
| The finding changed while you had it open | The app reloads the details after a conflict. Review the latest status and history before deciding whether to try again. |
| A request returns 403 | Use the analyst account for changes. If already signed in as an analyst, reload to refresh the session and CSRF token, then retry if the change is still needed. |
| The dashboard cannot reach the API | Check `http://localhost:5000/api/v1/health/live` and `http://localhost:5000/api/v1/health/ready`. If liveness succeeds but readiness returns 503, check the local database and migrations with `docker compose ps` and `docker compose logs api db`. |

For unexpected API errors, use the response's `X-Request-ID` to find the corresponding application log entry. Share the request ID and synthetic finding ID when needed. Keep passwords, cookies, and request bodies out of support notes or screenshots. See the [threat model](threat-model.md#data-handling-rules) for the logging policy.
