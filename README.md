# Kaggle Competitions MCP

**A practical repo for submitting Kaggle competitions with MCP from VS Code, chat-based MCP clients, and terminal helpers.**

![Kaggle Competitions MCP Banner](imgs/Gemini_Generated_Image_syylnzsyylnzsyyl.png)

This repository is the companion repo for my Medium article on Kaggle MCP submissions.

Article:

- [How to Submit to Kaggle Competitions Using MCP (VS Code)](https://medium.com/@ibrahim313/how-to-submit-to-kaggle-competitions-using-mcp-vs-code-9003bbb5af63)

The goal of this repo is simple:

1. show the easiest MCP workflow for a standard file-upload competition
2. show the correct MCP workflow for a notebook-based competition
3. keep the helper scripts in one place so you can test or extend them later

## What This Repo Covers

Kaggle competitions usually fall into two practical submission types:

### 1. Simple file-upload competitions

You generate a file like `submission.csv` locally and submit it.

Examples:

- Titanic
- House Prices
- many Playground competitions
- many community-hosted competitions

### 2. Notebook-based competitions

You run a Kaggle notebook, generate an output file such as `submission.json` inside `/kaggle/working/`, save the notebook version, and submit that notebook version.

Examples:

- ARC Prize 2026 - ARC-AGI-2
- AI Mathematical Olympiad style code competitions

That difference is the main thing you need to understand before using Kaggle MCP for submissions.

## Repo Contents

| File | Purpose |
|---|---|
| `.vscode/mcp.json` | Kaggle MCP configuration for VS Code |
| `titanic_submission.py` | Simple local baseline that creates `submission.csv` |
| `submit_competition_file.py` | Helper script for standard file-upload competitions |
| `arc_agi2_baseline.py` | Baseline notebook code for ARC-style competitions |
| `submit_code_competition_notebook.py` | Helper script for notebook-based competition submissions |
| `kaggle_mcp_call.ps1` | General PowerShell MCP caller |

## Quick Start

### Step 1: Generate a Kaggle token

Go to your Kaggle settings and generate a new token.

The token starts with:

```text
KGAT
```

Do not hardcode it into screenshots or public files.

### Step 2: Open the repo in VS Code

This repo already includes:

```text
.vscode/mcp.json
```

The config uses a secure prompt-based token input, so VS Code asks for the token when you start the server.

### Step 3: Start the Kaggle MCP server

In VS Code:

1. Press `Ctrl + Shift + P`
2. Run `MCP: List Servers`
3. Select `kaggle`
4. Click `Start Server`
5. Paste your Kaggle token when prompted

### Step 4: Test a simple competition flow

Put Titanic files in:

```text
data/train.csv
data/test.csv
```

Then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install pandas scikit-learn
python titanic_submission.py
```

This creates:

```text
submission.csv
```

Then use VS Code chat with:

```text
Use Kaggle MCP to upload and submit my local file submission.csv to the titanic competition with the description "Titanic MCP baseline from VS Code", then show me the submission status.
```

### Step 5: Test a notebook-based competition flow

For ARC-style competitions:

1. create or open your Kaggle notebook
2. attach the competition data source
3. make sure the notebook creates `submission.json` in `/kaggle/working/`
4. save and run the notebook
5. note the notebook version number

Then use VS Code chat with:

```text
Use Kaggle MCP create_code_competition_submission for competition "arc-prize-2026-arc-agi-2". Submit notebook owner "YOUR_KAGGLE_USERNAME", slug "YOUR_NOTEBOOK_SLUG", version YOUR_VERSION_NUMBER, file "submission.json", description "ARC MCP baseline from VS Code". Do not use the file-upload submission flow.
```

## Terminal Helpers

If you want to test MCP flows from the terminal, this repo includes helper scripts.

### Standard file-upload competition

```powershell
python .\submit_competition_file.py --competition titanic --file submission.csv --description "Titanic MCP baseline from terminal"
```

### Notebook-based competition

```powershell
python .\submit_code_competition_notebook.py --competition arc-prize-2026-arc-agi-2 --owner YOUR_KAGGLE_USERNAME --slug YOUR_NOTEBOOK_SLUG --kernel-version YOUR_VERSION_NUMBER --description "ARC MCP baseline from terminal"
```

### Generic MCP PowerShell caller

```powershell
.\kaggle_mcp_call.ps1 -ToolName get_competition -RequestJson '{"competitionName":"titanic"}'
```

## Why This Repo Exists

Most people will connect Kaggle MCP and stop there.

The useful part starts after setup.

This repo is meant to answer the practical question:

How do you actually use Kaggle MCP to submit to real competitions from your editor?

That is why the repo focuses on:

- one simple competition flow
- one notebook-based competition flow
- reusable helper scripts for extension or automation later

## Useful Links

- [Medium Article](https://medium.com/@ibrahim313/how-to-submit-to-kaggle-competitions-using-mcp-vs-code-9003bbb5af63)
- [Kaggle MCP Documentation](https://www.kaggle.com/docs/mcp)
- [Titanic Competition](https://www.kaggle.com/competitions/titanic)
- [ARC Prize 2026 - ARC-AGI-2](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2)
- [Kaggle Profile](https://www.kaggle.com/ibrahimqasimi)

## Author

**Muhammad Ibrahim Qasmi**

Youngest 3x Kaggle Grandmaster.

I write about Kaggle workflows, machine learning, MLOps, and practical developer tooling.
