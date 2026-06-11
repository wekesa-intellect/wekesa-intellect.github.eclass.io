# TODO - Railway deploy + password reset emails

## Step 1: Fix production settings
- [ ] Update `eclass_project/settings.py`:
  - Read `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from environment.
  - Switch DB to `DATABASE_URL` (Postgres).
  - Configure SMTP email backend using env vars (SendGrid) so password reset emails reach real users.

## Step 2: Create Railway-ready config
- [ ] Ensure `requirements.txt` includes `gunicorn`.
- [ ] (If needed) add Railway start command via Procfile or render.json equivalent.

## Step 3: Database migration
- [ ] Run migrations on Railway Postgres.

## Step 4: Static files
- [ ] Run `collectstatic`.

## Step 5: Verify password reset
- [ ] Create a user + request password reset.
- [ ] Confirm email is sent to user inbox.

