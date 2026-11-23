# ScholarLens: how to run

ScholarLens writes a literature review on a research topic. A **supervisor** coordinates five agents over A2A: it sends each agent a request, checks every answer, and decides what goes next.

| Agent | Runs as | Address |
|---|---|---|
| Supervisor | `python -m supervisor.service` (or `python -m supervisor`) | 127.0.0.1:9100 |
| Retrieval (Agent 1) | A2A wrapper around `group3` | 127.0.0.1:9101 |
| Paper Reader | A2A wrapper → reader service in `group2` | 127.0.0.1:9102 → 8000 |
| Common References (Agent 2) | A2A wrapper around `group3` | 127.0.0.1:9103 |
| Connections (Agent 3) | A2A wrapper → Agent 3 service in `group2` | 127.0.0.1:9104 → 8001 |
| Writer (Agent 4) | A2A wrapper around `group3` | 127.0.0.1:9105 |

## 1. Setup (once)

Run from the `ai_agent_task` folder.

Linux / macOS:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
pip install --no-build-isolation -e ".[a2a,supervisor,group2]"
cp .env.example .env
```

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
pip install --no-build-isolation -e ".[a2a,supervisor,group2]"
Copy-Item .env.example .env
```

Then put your keys in `.env`:

- `GROQ_API_KEY=` is used by the supervisor's claim judge and the writer.
- `GEMINI_API_KEY=` is used by the paper reader and Agent 3. **`.env.example` has no line for it, so add it yourself.**

`.env` is git-ignored. Never commit keys, and never paste them into chats, issues or screenshots.

## 2. In every terminal

Activate the environment, and run every command from the `ai_agent_task` folder, because settings and keys are read from `.env` there:

- Linux / macOS: `source .venv/bin/activate`
- Windows: `.\.venv\Scripts\Activate.ps1`

## 3. Demo: one terminal per agent

Each terminal shows its side of the A2A conversation. Start them in this order:

| # | Terminal | Command |
|---|---|---|
| 1 | Reader service | `cd group2` then `uvicorn reader_service:app --port 8000 --env-file ../.env` |
| 2 | Agent 3 service | `cd group2` then `uvicorn connections_service:app --port 8001 --env-file ../.env` |
| 3 | Retrieval | `python -m a2a_agents retrieval` |
| 4 | Paper Reader | `python -m a2a_agents reader` |
| 5 | Common References | `python -m a2a_agents references` |
| 6 | Connections | `python -m a2a_agents connections` |
| 7 | Writer | `python -m a2a_agents writer` |
| 8 | Supervisor | `python -m supervisor.service` |
| 9 | User (start last) | `python -m supervisor.ask --topic "agent identity"` |

Terminals 1 and 2 must run inside `group2/`, because that code imports its modules by name. They can stay off screen; terminals 3 and 4 show their side of the conversation.

What you will see:

- **Agent terminals:** for each request, `← Supervisor: …`, `task state: SUBMITTED → WORKING`, `artifact added: …`, `task state: COMPLETED (… s)`, or `error: …`. Reader lines name their paper, because the papers are read at the same time.
- **Supervisor:** the step lines, plus for every call `read agent card '…'`, `→ <agent>: …` and `← <agent>: …, task …, COMPLETED`, and its conversation with the user (`← User: …`, `→ User: … task state: INPUT_REQUIRED`).
- **User:** progress, then possibly the keep/drop question (see 5), then a summary and the report's path.

## 4. Quick run: four terminals

Terminals 1 and 2 as above, then:

| # | Terminal | Command |
|---|---|---|
| 3 | All five agents | `python -m a2a_agents` |
| 4 | Supervisor and user | `python -m supervisor --topic "agent identity"` |

Don't run `python -m a2a_agents` (all five) together with the single-agent terminals of section 3: they use the same ports.

## 5. The keep/drop question

Some claims cannot be verified even though their quotes are real (found word for word in the paper). For those, the run pauses and lists each claim with the closest passages from the paper. Reply with the numbers to keep (for example `1 3`), or `none` (or just Enter) to drop them all. An answer that can't be understood is asked again.

## 6. Where the results go

| What | Where |
|---|---|
| Final report, with the Supervisor Review section | `data/supervisor/reports/<task_id>.md` |
| The writer's own report | `data/reports/<report_id>/revision-<n>/report.md` |
| Downloaded papers | `data/papers/<task_id>/<run_id>/` |
| Run memory | `data/supervisor/memory.db` |

In the memory, each run ends as one of:
- `completed`
- `stopped`: the run could not continue, for example with too few papers
- `failed`: an error
- `interrupted`: stopped with Ctrl+C

`data/` is git-ignored.

## 7. Settings (in `.env`)

| Setting | Default | Meaning |
|---|---|---|
| `SUPERVISOR_TARGET_PAPERS` | `5` | papers Retrieval tries to find |
| `SUPERVISOR_MINIMUM_PAPERS` | `4` | Retrieval's minimum; fewer counts as too few |
| `SUPERVISOR_AGENT_TIMEOUT_SECONDS` | `600` | how long to wait for one agent's answer |
| `SUPERVISOR_SERVICE_URL`, `SUPERVISOR_RETRIEVAL_URL`, `SUPERVISOR_READER_URL`, `SUPERVISOR_REFERENCES_URL`, `SUPERVISOR_CONNECTIONS_URL`, `SUPERVISOR_WRITER_URL` | ports 9100–9105 | where the supervisor and the agents listen |
| `A2A_AGENTS_GROUP2_READER_URL`, `A2A_AGENTS_GROUP2_CONNECTIONS_URL` | `http://127.0.0.1:8000`, `http://127.0.0.1:8001` | where the wrappers find the two `group2` services; change these if you start them on other ports |

## 8. Stopping

Press Ctrl+C in each terminal. A run stopped this way is recorded as `interrupted` in the memory.

## 9. Common problems

| You see | Cause | Fix |
|---|---|---|
| `address already in use` | a terminal from section 3 or 4 is already running | stop the old one |
| `All connection attempts failed` in the reader or connections terminal | the `group2` service isn't running, or is on another port | start it (section 3), or set the `A2A_AGENTS_…_URL` setting |
| `Cannot reach the supervisor at http://127.0.0.1:9100` | the supervisor service isn't running | start `python -m supervisor.service` first |
| `GEMINI_API_KEY must be configured …` | the key is missing, or the service was started without `--env-file ../.env` | add the key to `.env` and restart the service |
| warning `The judge could not check …` (`GROQ_API_KEY is not set`) | the Groq key is missing | add `GROQ_API_KEY` to `.env` |
