# Contribution Guide

Thanks for contributing to SpotiFLAC Python.

## Project Structure

- `backend/` Flask API, download orchestration, metadata enrichment
- `spotiflac-frontend/` Vite + React frontend

## Prerequisites

- Python 3.12+
- Node.js 18+
- FFmpeg available in `PATH`
- (Optional for Picard fallback) `fpcalc` + `ACOUSTID_API_KEY`

## Local Setup

### Backend

1. `cd backend`
2. Create and activate virtualenv
   - Windows: `venv\Scripts\activate`
3. Install deps: `pip install -r requirements.txt`
4. Run: `python app.py`

### Frontend

1. `cd spotiflac-frontend`
2. Install deps: `npm install`
3. Run: `npm run dev`

## Environment

Create/update backend `.env` with at least:

- `SECRET_KEY=<your-secret>`
- `FLASK_ENV=production` (or `development` locally)
- `VIDEO_DOWNLOAD_API_KEY=<optional>`
- `ACOUSTID_API_KEY=<optional, for Picard fallback>`

## Coding Guidelines

- Keep changes focused and minimal.
- Preserve existing APIs unless refactor is required.
- Prefer root-cause fixes over UI/workaround-only changes.
- Do not add unrelated formatting-only edits.
- Add logs only when useful for debugging/ops.

## Testing Checklist

Before opening a PR:

- Backend starts without errors.
- Frontend starts and basic download flow works.
- Metadata enrichment flow works for at least one sample file.
- No new lint/syntax errors introduced.

## Pre-push Scripts

- Backend-only (recommended when deploying backend separately):
  - `cd backend && python pre_push_backend.py`
- Full monorepo (backend + frontend build):
  - `python pre_push.py`

## GitHub Actions

- CI workflow is in `.github/workflows/ci.yml`.
- It runs backend pre-push checks (`backend/pre_push_backend.py`) and frontend build on push/PR.

## Commit / PR Guidance

- Use clear commit messages describing _what_ and _why_.
- One logical change per PR when possible.
- Include:
  - Summary of change
  - Files touched
  - How to test
  - Any env/buildpack/deploy impact

## Deployment Notes (Heroku)

- `backend/app.json` contains buildpacks.
- `backend/Aptfile` is used by Heroku apt buildpack.
- If you change system dependencies, update both and document in PR.

## Need Help?

Open an issue with:

- Steps to reproduce
- Logs/errors
- Sample URL/input used
- Expected vs actual behavior
