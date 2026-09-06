# System design for a store app

Answer every question here in `docs/ARCHITECTURE.md` before the first `/dev-framework-rl` episode. A question with no answer is an `open` row in `docs/LAUNCH.md`, never a blank. Read `~/.claude/docs/infra-inventory.md` first: the answer to most "where does X live" questions is an existing account.

## 1. Data

- Every table, its owner, and its retention. Audio, images and transcripts name the day they are deleted.
- Every field that identifies a person, marked. This list feeds the privacy labels in stage 5 word for word, so it is the single source of truth for both.
- Migrations run from the app, forward and backward, and a rollback has been run once against a copy.
- Backup: where the copy goes, how often, and the command that restores it. A restore that has never been run is a hope.

## 2. Auth

- One auth model, named: key per user, magic link, OAuth, or a vendor. Mobile needs a way in that a reviewer can use in under a minute, so a pasted key or a demo account exists.
- Every route lists its auth requirement. Dev-only routes are gated by an env flag that production never sets.
- Rate limit on sign-in and on every endpoint that costs money to call.

## 3. Secrets

- A named list of every secret, in `docs/ARCHITECTURE.md`, names only. Values live in the platform's secret store and in a gitignored `.dev.vars` or `.env`.
- Each secret has an owner and a rotation command. A secret that reached chat or a log is rotated the same day.
- A test user's credentials never appear in the repo; the review notes field carries them.

## 4. Pipeline

- Every background stage (transcribe, summarise, deliver, sync) is idempotent and retried with a cap. Name the queue or the scheduler.
- Each stage writes a status row the UI can read, so a user sees "writing up" instead of a spinner.
- Failure lands in a dead-letter state with the error text, and a person can requeue it from a command.
- Vendor calls carry a timeout and a per-user daily cap.

## 5. Alerts

The alert reaches a phone or it does not exist. Sentry is already in the inventory; Telegram is the channel every other project here uses.

- Uncaught error rate, pipeline dead-letter count, and vendor 4xx/5xx each have a threshold and a message that names the app.
- One health endpoint, checked from outside on a schedule; the check's failure alerts.
- Cost alert on every metered vendor and on the platform bill, set at the ceiling in section 6.
- The alert channel and the human who reads it are named in `docs/ARCHITECTURE.md`.

The native shell reports its own crashes too. Sentry's Capacitor SDK, or the store consoles' crash reports at minimum, with the crash-free rate readable on day one. A backend with alerts and a shell with none is half an app.

## 5b. The metric

The PRD's success metric needs an event, a table and a query, named here, before any code. Eaves shipped with no analytics, so its 30-day review has nothing to read. Privacy-label the event's data in section 7, keep it first-party, and write the query in `docs/LAUNCH.md` so the 30-day line is one command.

## 6. Cost

- A monthly ceiling in pounds, and the per-user cost at 10, 100 and 1,000 users, computed from vendor prices read this session.
- The kill switch: the env var or flag that turns off the expensive path without a deploy.

## 7. Privacy flow

- A diagram or table: each kind of user data, every third party that sees it, and why. This is the privacy policy's content and the store labels' content, so it is written once here and copied out.
- The deletion path: what a user does to delete their account and data, and the command that proves the rows are gone.

## 8. Post-deploy

- The 7-day check: what to look at (errors, dead letters, cost, reviews) and the date. `/dev-framework-rl` finalize schedules its own; the app's check is in addition and lives in `docs/LAUNCH.md`.
- Rollback: the command that puts the previous build back for the backend, and the store mechanism for the app (phased rollout halt, or a hotfix build number).
