# Learning Journey Assistant — Frontend

Single-page web app for the Learning Journey Assistant. It lets a student review
their subject results, drill into an assessment breakdown, and generate an
AI-assisted study plan mapped to SILOs.

Built with **React 19 + TypeScript + Vite**. All data is currently served from
local fixtures in `src/data/` — there is no live backend to run alongside it yet.

## Tech stack

| Concern        | Choice                                             |
| -------------- | ------------------------------------------------- |
| Build / dev    | [Vite 8](https://vite.dev)                        |
| UI             | React 19, `react-router-dom` 7                    |
| Charts         | `recharts`                                        |
| Icons          | `lucide-react`                                    |
| HTTP client    | `axios` (wired for future API integration)        |
| Linting        | [`oxlint`](https://oxc.rs)                        |
| Language       | TypeScript (strict, project references)           |

## Prerequisites

- **Node.js 20.19+ or 22.12+** (Vite 8 requirement; repo is developed on Node 24)
- **npm 10+** (bundled with recent Node)

Check your versions:

```bash
node -v
npm -v
```

## Quick start (from a fresh clone/download)

```bash
# 1. Get the code
git clone <repo-url>
cd learning-journey-assistant/frontend
#   (or, if you downloaded a ZIP: extract it, then cd into <extracted>/frontend)

# 2. Install dependencies (creates node_modules/, uses package-lock.json)
npm install

# 3. Start the dev server
npm run dev
```

`npm run dev` prints a local URL — open it in your browser:

```
  ➜  Local:   http://localhost:5173/
```

The app loads on the Dashboard route (`/`). Edits to files under `src/` hot-reload
automatically. Press `Ctrl+C` in the terminal to stop the server.

> All data is bundled as local fixtures in `src/data/`, so nothing else needs to
> be running — no backend, no database, no `.env` file.

## Install

From this `frontend/` directory:

```bash
npm install
```

Re-run this whenever `package.json` changes (e.g. after a `git pull`).

## Run

### Development server (hot reload)

```bash
npm run dev
```

Vite prints a local URL (default <http://localhost:5173>). The app opens on the
Dashboard route (`/`). If port 5173 is taken, Vite picks the next free port and
prints it.

### Production build

```bash
npm run build
```

Runs `tsc -b` for type-checking, then emits an optimized bundle to `dist/`.

### Preview the production build

```bash
npm run preview
```

Serves the contents of `dist/` locally so you can smoke-test the built output.

### Lint

```bash
npm run lint
```

## Available scripts

| Script            | What it does                                         |
| ----------------- | -------------------------------------------------- |
| `npm run dev`     | Start the Vite dev server with HMR                  |
| `npm run build`   | Type-check (`tsc -b`) and build to `dist/`          |
| `npm run preview` | Serve the `dist/` build locally                     |
| `npm run lint`    | Run `oxlint` over the project                       |

## Project structure

```
frontend/
├── index.html              # Vite entry HTML, mounts #root
├── vite.config.ts          # Vite + @vitejs/plugin-react config
├── tsconfig*.json          # TS project references (app + node)
├── .oxlintrc.json          # Lint rules
├── public/                 # Static assets served as-is (favicon, icons)
├── dist/                   # Build output (generated)
└── src/
    ├── main.tsx            # App bootstrap: React root + <BrowserRouter>
    ├── App.tsx             # App shell: top bar, nav, route definitions
    ├── App.css / index.css # Global styles
    ├── studentContext.tsx  # <StudentProvider> — currently-selected student
    ├── StudentPicker.tsx   # Student selector in the top bar
    ├── Dropdown.tsx        # Shared dropdown control
    ├── pages/
    │   ├── DashboardPage.tsx        # Route "/"  — subject/mastery overview
    │   ├── ResultsOverviewPage.tsx  # Route "/results" — results table
    │   └── StudyPlanPage.tsx        # Route "/study-plan" — AI study plan
    ├── data/               # Mock fixtures + in-memory stores
    │   ├── students.ts
    │   ├── dashboard.ts / studentDashboard.ts
    │   ├── studentAssessments.ts
    │   └── studyPlan.ts / studyPlanStore.ts
    └── assets/             # Images imported by components
```

### Routes

| Path          | Page                   | Purpose                                    |
| ------------- | ---------------------- | ---------------------------------------- |
| `/`           | `DashboardPage`        | Per-subject results and mastery status    |
| `/results`    | `ResultsOverviewPage`  | Detailed results / assessment breakdown   |
| `/study-plan` | `StudyPlanPage`        | AI-assisted study plan grouped by SILO    |
| `*`           | —                      | Redirects to `/`                          |

## Notes

- **No authentication yet.** "Log off" simply returns to `/` (planned for a later phase).
- **No backend calls yet.** `axios` is installed for the eventual API layer; today
  every page reads from `src/data/`.
- The Python service in the repo root (`../src/`) is a separate project and is
  **not** required to run this frontend.
