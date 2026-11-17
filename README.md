# Group 3: Multi-Agent Paper Analysis

This repository contains Group 3's paper-retrieval and analysis components. It
does not implement Group 2's Reader or Supervisor. The Group 1/2 handoff and
A2A adapters in this repository are development integrations based on
provisional contracts; they are not a finalized team-wide protocol.

## What is included

| Component | Responsibility |
| --- | --- |
| Agent 1: Retrieval | Search for papers, rank candidates, retrieve and parse documents, and store paper metadata, sections, and references. |
| Agent 2: Common References | Identify references shared by selected papers, count distinct citing papers, and flag uncertain matches for review. |
| Agent 4: Writer | Produce a Markdown literature-review draft from supplied claims and evidence, check coverage, and allow one coverage revision. |
| Integration tools | Export/import paper-store bundles, validate Group 2 handoffs, assemble Writer input, and expose provisional A2A services. |

The default retrieval target is 8 papers, with 7 as the minimum. For an initial
smoke test, the commands below request 3 papers instead. Retrieval uses external
metadata and document services; results and availability depend on those
services.

## Requirements and installation

Use Python 3.12 or newer.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-build-isolation -e ".[test]"
cp .env.example .env
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e ".[test]"
Copy-Item .env.example .env
```

Keep API keys in the local `.env` file or environment variables. Never commit
real credentials. Retrieval and extractive Writer mode can be tested without a
Groq key. Groq-based retrieval planning or Writer generation requires
`GROQ_API_KEY` and makes external model requests.

## Run the agents from the command line

Run commands from the repository root with the virtual environment activated
(or use `.\.venv\Scripts\python.exe` in PowerShell).

### 1. Retrieve papers

```bash
python -m group3.cli \
  --topic "multi agent large language models" \
  --target 3 \
  --minimum 3 \
  --task-id demo3 \
  --result data/retrieval.json
```

The result includes a `run_id`. Keep it for the next command. Use the default
target and minimum (8 and 7) for a normal collection rather than the three-paper
smoke-test settings above.

### 2. Find common references

```bash
python -m group3.analysis_cli references \
  --task-id demo3 \
  --run-id YOUR_RUN_ID \
  --output data/references.json
```

Replace `YOUR_RUN_ID` with the `run_id` from the retrieval result. The command
reads the corresponding run from the configured paper store.

### 3. Write a report

The included Group 2 example is a fixture for checking the Writer input format;
it is not a completed or validated research analysis.

```bash
python -m group3.analysis_cli write \
  --input examples/group2-example.json \
  --mode extractive \
  --result data/writer.json
```

To request Groq-generated prose and review instead, use `--mode groq` and
configure `GROQ_API_KEY` locally:

```bash
python -m group3.analysis_cli write \
  --input examples/group2-example.json \
  --mode groq \
  --result data/writer-groq.json
```

Model output and structural checks do not establish that a report is factually
correct. Writer results remain subject to review; `coverage_incomplete` means
required inputs or coverage are missing.

## Group 2 handoff and integration

The integration utilities support a provisional handoff from Group 2:

```bash
# Inspect local integration prerequisites; this does not prove a remote service works.
python -m group3.integration.cli check

# Assemble a WriterRequest from a Group 2 output file and the local paper store.
python -m group3.integration.cli assemble-writer \
  --input path/to/group2-output.json \
  --topic "your research topic" \
  --output data/writer-ready.json

# Run the Writer on the assembled request.
python -m group3.analysis_cli write \
  --input data/writer-ready.json \
  --mode extractive \
  --result data/writer.json
```

The handoff schemas and adapters are provisional and require team agreement.
The readiness check reports configuration; it does not itself verify an
end-to-end connection. See [the integration handoff guide](docs/integration_handoff.md)
and [the contract notes](docs/contracts/README.md) before exchanging data.

The A2A service adapter is also a development integration and is not the Group
2 Reader or Supervisor. For example, start a Retrieval service with:

```bash
python -m group3.a2a.server --agent retrieval --port 8001
```

The supported agent names are `retrieval`, `references`, and `writer`. Consult
the A2A server and integration documentation for operation payloads and
provisional status behavior before connecting another group.

## Tests

Run the offline test suite:

```bash
python -m pytest -m "not live" -q
```

Live tests are excluded by default because they contact external services and
may require API keys or incur usage. Run them only when intentionally testing
those integrations. For the current implementation notes and known follow-up
items, see [Future Work](docs/meeting_future_work.md) and the
[development guide](Group3_MultiAgent_Development_Guide.md).
