# Run the app in Visual Studio Code

A step-by-step guide for anyone who wants to download the Learning Journey
Assistant and run it on their own computer. No experience with the project
needed. Takes about 10 minutes the first time.

> **Just want to look at it?** Open the live demo instead — nothing to install:
> https://learning-journey-assistant.onrender.com (the first load can take up to a minute).

---

## 1. Install three things (one time only)

| Install | Where | Notes |
|---|---|---|
| **Python 3.11 or newer** | https://www.python.org/downloads/ | **Windows:** on the first installer screen, tick **"Add python.exe to PATH"**. |
| **Git** | https://git-scm.com/downloads | Accept the defaults. |
| **Visual Studio Code** | https://code.visualstudio.com/ | Accept the defaults. |

Then open VS Code, go to **Extensions** (`Ctrl+Shift+X`, Mac `Cmd+Shift+X`),
search **Python**, and install the one published by **Microsoft**.

Check Python works: in VS Code open **Terminal → New Terminal** and type:

```bash
python --version
```

You should see `Python 3.11.x` or higher. (On Mac/Linux, use `python3` everywhere this guide says `python`.)

---

## 2. Download the code

1. In VS Code, press `Ctrl+Shift+P` (Mac `Cmd+Shift+P`) and run **Git: Clone**.
2. Paste this address and press Enter:
   ```
   https://github.com/Kartik0219/learning-journey-assistant.git
   ```
3. Pick a folder to save it in. **Use a short path outside OneDrive**, such as
   `C:\Projects` (Mac: `~/Projects`). Deep or synced folders can hit Windows'
   path-length limit and stop the app from starting.
4. When asked, click **Open** to open the project.

<details>
<summary>Prefer the terminal?</summary>

```bash
git clone https://github.com/Kartik0219/learning-journey-assistant.git
cd learning-journey-assistant
code .
```
</details>

---

## 3. Create the project's Python environment

This keeps the app's packages separate from anything else on your computer.

1. Press `Ctrl+Shift+P` and run **Python: Create Environment**.
2. Choose **Venv**.
3. Choose your Python 3.11+ interpreter.
4. When it asks about dependencies, **tick `requirements.txt`** and click **OK**.

VS Code creates a `.venv` folder and installs everything. Wait for the
notification to finish (1–3 minutes).

<details>
<summary>Prefer the terminal?</summary>

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
</details>

Now open a **new** terminal (**Terminal → New Terminal**). Its prompt should
start with `(.venv)`. If it doesn't, see [Troubleshooting](#troubleshooting).

---

## 4. Build the database

In that `(.venv)` terminal:

```bash
python -m src.pipeline
```

This reads the data, finds each student's skill gaps, and calculates mastery
scores. It finishes with `Pipeline complete.`

No setup file is needed — with nothing configured, the app uses the small
sample dataset included in the repository.

---

## 5. Start the app

```bash
python -m src.deliver.app
```

Leave this terminal running, then open **http://127.0.0.1:5000** in your browser.

**Sign in with:**

| Student number | Password |
|---|---|
| `DEMO0001` | `DEMO0001` |

The app is student-only — there are no staff or admin accounts. On the
150-student dataset, sign in as `STU0001` / `STU0001` instead (see step 6).

To stop the app, click in the terminal and press `Ctrl+C`.

**Next time** you only need step 5 (and step 4 again if the data changed).

---

## 6. Optional: use the 150-student dataset

The live demo runs on the subject's anonymised 150-student workbook, and it
is already in the project at `data/dataset/CSE_results_150_students_3_Subjects.xlsx`.
To run your local copy on it, set the path in the `(.venv)` terminal and
rebuild with a separate database:

**Windows (PowerShell):**
```powershell
$env:HISTORICAL_DATASET_PATH = "data/dataset/CSE_results_150_students_3_Subjects.xlsx"
$env:DATABASE_URL = "sqlite:///./ljas_real.db"
python -m src.pipeline
python -m src.deliver.app
```

**Mac / Linux:**
```bash
export HISTORICAL_DATASET_PATH=data/dataset/CSE_results_150_students_3_Subjects.xlsx
export DATABASE_URL=sqlite:///./ljas_real.db
python -m src.pipeline
python -m src.deliver.app
```

The pipeline takes about 2 minutes on this dataset. Sign in as any student
from **`STU0001` to `STU0150`**, using the student number as the password
(e.g. `STU0001` / `STU0001`). `DEMO0001` does not exist in this dataset.

These settings only last for that terminal window. To make them permanent,
copy `.env.example` to a new file named `.env` and fill in the two values there.
**Never commit `.env`.**

---

## 7. Optional: run the tests

**Terminal:**
```bash
python -m pytest -q
```

**Or in VS Code:** click the **Testing** (flask) icon in the left bar →
**Configure Python Tests** → **pytest** → folder **`tests`**, then press ▶ Run All.

All tests should pass in about 90 seconds. They use the sample data and need
no internet or API key.

---

## 8. Optional: start the app with F5

Create a file `.vscode/launch.json` in the project (it isn't in the repository,
so each person makes their own) with:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Build database",
      "type": "debugpy",
      "request": "launch",
      "module": "src.pipeline",
      "console": "integratedTerminal"
    },
    {
      "name": "Run app",
      "type": "debugpy",
      "request": "launch",
      "module": "src.deliver.app",
      "console": "integratedTerminal"
    }
  ]
}
```

Then open **Run and Debug** (`Ctrl+Shift+D`), pick **Build database** or
**Run app**, and press **F5**. Breakpoints work in both.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognised | Python isn't on PATH. Re-run the Python installer, choose **Modify**, and tick **Add Python to environment variables**. Restart VS Code. On Mac/Linux use `python3`. |
| **Windows:** `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, answer `Y`, then open a new terminal. |
| Terminal prompt doesn't show `(.venv)` | `Ctrl+Shift+P` → **Python: Select Interpreter** → pick the one with `.venv` in its path. Then open a new terminal. |
| `ModuleNotFoundError: No module named 'flask'` (or similar) | The environment isn't active or packages didn't install. Activate it (step 3) and run `pip install -r requirements.txt`. |
| **Windows:** `DLL load failed ... The filename or extension is too long` | The project folder path is too long (often inside OneDrive). Clone it again into a short folder such as `C:\Projects` and redo steps 3–5. |
| `ModuleNotFoundError: No module named 'src'` | You're in the wrong folder. The terminal must be in the project root — the folder that contains `requirements.txt`. |
| `Address already in use` / port 5000 busy | Another app is using port 5000 (on Mac, often AirPlay Receiver). Stop it, or turn off AirPlay Receiver in System Settings → General → AirDrop & Handoff. |
| Login says the password is incorrect | Run `python -m src.pipeline` first — it creates the accounts. On the 150-student data use `STU0001`, not `DEMO0001`. |
| The **AI Insight** page says AI isn't configured | Expected. It's optional and needs an API key in `.env` — see `.env.example`. Everything else works without it. |
| The page at `/app/` says the React app isn't built | Run `git pull` to get the latest code, which includes the built files. |

Still stuck? See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) for more detail, or
[SYSTEM_MAINTENANCE.md](SYSTEM_MAINTENANCE.md) for how the system fits together.
