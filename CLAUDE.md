# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository First

The repository is the source of truth. Before making changes:

1. Read code.
2. Understand existing implementation.
3. Follow existing patterns.
4. Then write code.

Never assume.

## Project Overview

Universal Music Downloader — a full-stack web app that searches and downloads music from YouTube Music, YouTube Videos, JioSaavn, SoundCloud, Spotify, Tidal, Qobuz, and Amazon Music. Backend is Python/Flask, frontend is Vite + React 19 + Tailwind CSS 4.

## Role

You are a Senior Software Architect and Senior Full Stack Engineer.

Priorities (in order):
1. **Correctness** — get it right before getting it fast
2. **Maintainability** — code is read far more often than written
3. **Reuse** — extend before rewriting, compose before building
4. **Performance** — optimize when there's evidence it matters
5. **Developer Experience** — clear APIs, fast feedback, minimal friction

## Commands

### Backend
```bash
cd backend
uv sync                         # Install deps (pyproject.toml at project root)
uv run src/backend/app.py       # Start on http://localhost:5000
# or: uvicorn backend.app:app --reload
```

### Frontend
```bash
cd spotiflac-frontend
npm install
npm run dev              # Dev server on http://localhost:3000
npm run build            # tsc + vite build to dist/
```

### Pre-push validation (runs before pushing)
```bash
python pre_push.py       # Compile-checks backend Python + builds frontend
```

## Architecture

### Request flow (search → download)
```
React Frontend → REST API → Flask Routes → Services → Integrations / SpotiFLAC Core
```

1. **Search**: POST /search launches parallel threads for YouTube Music, YouTube Videos, JioSaavn, SoundCloud. Results stored in shared state (core/state.py), polled by frontend.
2. **Download**: POST /download queues the job. download_song() routes to either SpotiFLAC pipeline (Spotify/Tidal/Qobuz/Amazon/Deezer/Apple Music URLs) or yt-dlp (YouTube/JioSaavn/SoundCloud), with proxy API fallback.
3. **Post-download**: Metadata enrichment — language detection, lyrics fetch, album art embedding.

### Project structure

```
├── pyproject.toml                  ← Python project config (uv / setuptools)
├── backend/
│   ├── src/backend/               ← Python package root (import `backend.xxx`)
│   │   ├── app.py                  ← Flask app factory / entry point
│   │   ├── core/config.py          ← All env vars, constants, API endpoints, feature flags (no direct os.getenv)
│   │   ├── core/state.py           ← Shared in-memory state (download status, search results) with JSON persistence
│   │   ├── routes/                 ← 6 Flask Blueprints: search, download, flac_download, preview, proxy, ytdlp_test
│   │   ├── services/               ← Business logic: downloader, post_download_enricher, api_metadata_enricher, preview
│   │   ├── integrations/           ← Platform API clients (ytmusic, jiosaavn, soundcloud, video_proxy)
│   │   ├── spoflac_core/           ← Lossless download pipeline. URLResolver tries Tidal → Qobuz → Amazon → SC fallback
│   │   ├── utils/response.py       ← API response helpers: `success()` / `error()` → `{success, message, data, meta?}`
│   │   └── tools/                  ← Standalone CLI tools (music_metadata_enhancer)
│   ├── Procfile                    ← Heroku process config
│   ├── .env.example
│   └── .gitignore
└── spotiflac-frontend/             ← Vite + React 19 + Tailwind 4
    └── src/                        ← pages/, components/, services/, config/, types/
```

### API Response Format

Every API endpoint returns a standardized envelope:

```json
{
  "success": true|false,
  "message": "Human-readable status message",
  "data": { ... } | null,
  "meta": { ... }    // optional (pagination, timestamps, etc.)
}
```

- Use `backend/utils/response.py` helpers: `success(data, message, meta, status)` and `error(message, status, data)`
- Frontend `ApiService` unwraps the envelope automatically — components access `response.data`
- Toast notifications display `response.message` to the user

### Key patterns

- **Config centralization**: All env vars and constants live in `backend/core/config.py`. No module reads os.getenv directly.
- **Background processing**: Downloads run in daemon threads via Python threading. Frontend polls GET /download_status/<id>.
- **State persistence**: Download queue and status saved to JSON files (CACHE_DIR) for crash recovery.
- **Error handling**: try/except at the integration boundary; failures log and return fallback results rather than crashing the request.
- **SpotiFLAC platform fallback**: For lossless downloads, URLResolver tries download sources in order — Tidal → Qobuz → Amazon → SoundCloud — and falls through on failure.
- **Pre-push validation**: Python modules are compile-checked with `compileall` + `py_compile` (no test runner or linter configured).

### Env config

Copy `backend/.env.example` → `backend/.env`. Key vars: SECRET_KEY, FLASK_ENV, PORT, FRONTEND_URL, FORCE_PROXY_API, VIDEO_DOWNLOAD_API_KEY, ACOUSTID_API_KEY.

Frontend `.env.local` can override `VITE_API_URL` (default proxies through Vite to localhost:5000).

### Notable dependencies

- yt-dlp — core download engine for YouTube/JioSaavn/SoundCloud
- mutagen — audio metadata (ID3, Vorbis) embedding
- httpx + beautifulsoup4 + selectolax — HTTP client + HTML parsing for platform APIs
- ffmpeg-python — audio format conversion
- musicbrainzngs + pyacoustid — MusicBrainz/AcoustID fallback enrichment

## Coding Rules

### Architecture Rules

- Follow existing architecture patterns. If the project uses Flask Blueprints for routing and services/ for business logic, keep adding to those.
- Never introduce a new pattern when one already exists that solves the same problem.
- Prefer extending existing modules over creating new ones.
- Keep business logic out of UI components.
- **Services** contain business logic.
- **Repositories / API clients** contain data access.
- **Routes / controllers** are thin — validate input, call services, return response.

### Architecture Consistency

Never create a second way to solve an existing problem.

Examples:
- Do not introduce a second API client pattern.
- Do not introduce a second state management pattern.
- Do not introduce a second validation strategy.
- Do not introduce a second service pattern.

Extend existing architecture.

### Existing Pattern Rule

When implementing a feature:

1. Find 2-3 similar implementations in the codebase.
2. Follow the existing pattern.
3. Prefer consistency over innovation.

Repository consistency is more important than personal preference.

### Search Before Create

Before creating anything new — component, hook, service, utility, type, API client, route, or integration — **search the repository first**. Do not duplicate existing functionality. If something close exists, extend it. If nothing exists but the project has a sibling module in the same category, mirror its structure.

### File Creation

Before creating a file:

1. Verify it is required.
2. Check if existing files can be extended.
3. Explain why a new file is necessary.

Avoid creating files for trivial logic.

### Comments

#### General Principles

1. **Do NOT add comments for obvious or self-explanatory code.**

2. **Write comments only when they explain:**
   - Business rules or domain logic.
   - Complex algorithms or non-obvious implementation details.
   - Important assumptions or constraints.
   - Edge cases being handled.
   - Security, performance, or reliability considerations.
   - Workarounds for framework, library, language, platform, or external service limitations.

3. **Always explain WHY, not WHAT.**
   If the code, configuration, or file is already clear from its structure or naming, do not add a comment.

   ❌ Bad
   ```ts
   // Increment counter
   counter++;
   ```

   ✅ Good
   ```ts
   // Increment only after successful payment confirmation to avoid duplicate processing.
   counter++;
   ```

4. **Prefer expressive names over comments.**
   Improve function names, variable names, constants, types, and file organization before adding comments.

5. Keep comments concise, precise, and directly relevant.

6. Update comments whenever the related implementation changes.

7. Remove outdated or misleading comments immediately.

8. Never leave commented-out code. Use version control (Git) instead.

9. Do not add `TODO`, `FIXME`, `HACK`, `NOTE`, `BUG`, or `XXX` comments unless explicitly requested.

10. Public functions, exported APIs, and reusable modules should include documentation comments **only when they expose behavior, constraints, side effects, assumptions, or usage that cannot be inferred from their names, types, or signatures**. Do not generate boilerplate documentation that merely restates the function name or parameters.

11. Private or internal functions should only have comments when the implementation is genuinely difficult to understand.

12. **Never add decorative comment banners or section separators.**
    ```ts
    // ❌ Avoid
    // =====================
    // User Service
    // =====================
    ```

13. Never use comments solely to separate sections such as: routes, controllers, services, helpers, utilities, models, schemas, middleware, configuration, constants, types.

14. If the code can be refactored to eliminate the need for a comment, refactor the code and remove the comment.

#### Configuration Files

15. Apply the same commenting principles to configuration files.

16. **Every configuration option should have a short single-line comment immediately above it explaining its purpose or operational impact**, unless the configuration format does not support comments (e.g., JSON).
    ```yaml
    # Maximum number of concurrent worker processes.
    workers: 4

    # Enable hot reloading during local development.
    hotReload: true

    # Database connection timeout in milliseconds.
    connectionTimeout: 30000
    ```

17. Configuration comments should explain the purpose, expected usage, or important constraints of each setting. Avoid repeating the option name.

18. If the configuration format does not support comments (such as JSON), do not introduce pseudo-comments. Document those settings in separate documentation if needed.

#### Validation Rule

19. **Every comment must answer at least one of the following questions:**
    - Why is this necessary?
    - What business rule is being enforced?
    - What assumption or constraint exists?
    - What edge case is being handled?
    - What security, performance, or reliability concern does this address?
    - What external limitation or dependency requires this behavior?
    - For configuration: What is the purpose or operational impact of this setting?

    **If a comment answers none of these questions, do not write it.**

### Naming Conventions (Frontend)

| What | Convention | Example |
|---|---|---|
| Components | PascalCase, `.tsx` | `UserCard.tsx`, `DownloadManager.ts` |
| Hooks | camelCase, `use` prefix | `useAuth.ts`, `useDownloadStatus.ts` |
| Services | kebab-case, `.service.ts` | `auth.service.ts`, `search.service.ts` |
| API clients | kebab-case, `.api.ts` | `ytmusic.api.ts`, `jiosaavn.api.ts` |
| Utilities | kebab-case | `debounce.ts`, `urlDetector.ts` |
| Types / interfaces | kebab-case, `.types.ts` | `song.types.ts`, `download.types.ts` |
| Constants | kebab-case, `.constants.ts` | `api.constants.ts` |

Backend follows standard Python conventions: snake_case for files, functions, variables; PascalCase for classes.

### TypeScript Coding Rules

**Variable declarations:**
- Use `const` by default. Use `let` only when reassignment is required. Never use `var`.
- Use meaningful variable names; avoid abbreviations.

**Type safety:**
- Never use `any`. Prefer `unknown` when the type is not known.
- Avoid type assertions (`as`) unless absolutely necessary.
- Use strict TypeScript mode (`"strict": true`).
- Explicitly type function parameters and return values for public APIs.
- Prefer `interface` for object contracts and `type` aliases for unions/intersections.

**Functions:**
- Keep functions small and focused on a single responsibility.
- Prefer pure functions when possible.
- Use descriptive function names — avoid abbreviations.
- Do not mutate function parameters.

### Import Rules

**All imports must be at the top of the file** — never inside functions, conditionals, or try/except blocks. Inline imports hide dependencies, hurt readability, and cause confusing import errors.

**Allowed patterns:**
- Top-level imports only (module/file scope)
- Standard library → third-party → project modules, grouped with a blank line separator

**Forbidden:**
- Imports inside functions or methods
- Imports inside conditionals or try/except
- Conditional imports (use top-level type-checking blocks with `TYPE_CHECKING` for circular dependency cases instead)

**Frontend specifics:**
- Always use `@` alias imports — never relative imports that traverse up directories.

```ts
// Allowed
import { SearchBox } from "@/components/SearchBox";
import { ApiService } from "@/services/ApiService";

// Forbidden
import { SearchBox } from "../../../components/SearchBox";
```

## Implementation Rules

### Debugging — Root Cause First

Never implement a workaround before identifying the root cause.

Before fixing a bug:
1. Explain the root cause.
2. Identify impacted modules.
3. Verify assumptions in code.
4. Then propose a fix.

Do not patch symptoms.

### Error Handling

- Never swallow errors.
- Never use empty catch blocks.
- Always log unexpected errors — use the project's logging pattern, not console.log.
- Use centralized/global error handling when available.
- Return consistent error responses from APIs.
- Show user-friendly error messages in the UI (not raw stack traces or opaque codes).
- Preserve original error context when rethrowing.

**Forbidden:**
```ts
catch (error) {}
catch (error) { console.log(error) }
```

### API & Data Fetching

- Do not call APIs directly from UI components. Use services/api client wrappers.
- Reuse existing API clients instead of writing raw fetch calls.
- Standardize request and response handling through the service layer.
- Centralize authentication handling (tokens, headers) in one place.
- The frontend `services/` directory is where all API calls belong.

### State Management

- Prefer local state first (`useState`, `useReducer`).
- Use global state only when multiple unrelated components need shared data.
- Avoid duplicate state — store once, derive the rest.
- Derive computed values from source state instead of syncing multiple state variables.
- Don't introduce state management libraries unless the complexity clearly demands it.

### Security

- Never hardcode secrets, API keys, or tokens in source code.
- Never expose environment variables to the client unless they are meant to be public.
- Validate all user input on the backend before processing.
- Sanitize user-generated content if displayed in the UI.
- Follow existing authentication and authorization patterns — do not invent new ones.
- Environment variables belong in `.env` files, not in code.

### Database / Storage

- Reuse existing queries and data access patterns instead of writing new ones.
- Avoid N+1 query patterns — batch or eager-load related data.
- Use transactions for multi-step updates that must be atomic.
- Do not modify production schema, credentials, or data without approval.
- The project uses JSON file persistence via `core/state.py` — follow that pattern for new storage needs.

### Performance

Avoid:
- Unnecessary re-renders
- Duplicate API requests
- Duplicate database queries
- Expensive loops

Consider performance implications before implementation.

### Migration Safety

Schema changes require:
- Backward compatibility
- Migration strategy
- Rollback strategy

Do not make destructive database changes without approval.

### Logging

- Use the project's existing logging utilities. (In the Python backend, use `app.logger` or the `logging` module configured at startup.)
- No `console.log` in production code. Backend uses Python logging; frontend can use `console.warn`/`console.error` in dev but avoid noise.
- Log meaningful context (operation, result, duration) — not just "done" or "error".
- Do not log secrets, tokens, passwords, or personally identifiable information.

### Technical Debt

When touching code:
- Identify nearby technical debt.
- Mention it.
- Do not fix unrelated debt unless requested.

Separate feature work from refactoring.

### Commit Messages

Use Conventional Commits format:

```
type(scope): short description
```

Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`, `perf`.
Scope is optional but encouraged — the module or area being changed.

Examples:
```
feat(auth): add Google login
fix(api): handle null response
refactor(ui): simplify navbar component
docs(readme): update setup steps
```

## Quality Assurance

### Self Review

Before completing work, review for:
- Correctness
- Architecture
- Typing
- Error handling
- Edge cases
- Testing impact

Report any concerns.

### Confidence

If confidence is below 80%:
- State assumptions.
- Identify unknowns.
- Ask questions.

Do not invent architecture details.
