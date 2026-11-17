# ScholarLens reader, connections, and evaluation

This project contains a Gemini paper reader, a SQLite-backed paper section
store, Agent 3 for cross-paper connections, and an LLM judge for literature
review reports.

## 1. Set up the environment

From this directory, create and activate a virtual environment and install
dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey).
Keep it private; do not commit it or paste it into source files. In each
terminal where you will run a Gemini-backed service or the judge, set the key
for that terminal session. In zsh, the following prompts for the key without
displaying it:

```zsh
read -s "GEMINI_API_KEY?Paste Gemini API key (hidden), then press Return: "
echo
export GEMINI_API_KEY
export GEMINI_MODEL="gemini-3.5-flash-lite"
```

Use a model ID available to your API key. `gemini-3.5-flash-lite` is the tested
default; override it with `GEMINI_MODEL` if necessary. A new terminal does not
inherit variables exported only in another terminal.

## 2. Run the automated tests

These tests use mocked Gemini responses, so no API key or running service is
needed:

```bash
python -m unittest discover -s tests -v
```

All tests should end with `OK`.

## 3. Test the paper reader

In terminal 1, activate the environment, set `GEMINI_API_KEY` and
`GEMINI_MODEL` as described above, then start the reader:

```bash
uvicorn reader_service:app --reload --port 8000
```

Keep the server running. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
to use the interactive API documentation.

### Store a sample paper

In Swagger UI, expand **PUT `/api/v1/papers/{paper_id}`**, click **Try it out**,
and fill in the path parameter and body separately:

- `paper_id`: `testpaper_01`
- Request body:

```json
{
  "title": "Test Paper",
  "sections": [
    "Abstract: This paper studies a sample research problem.",
    "Methods: The authors propose a sample method.",
    "Results: The method is evaluated on a sample dataset."
  ]
}
```

Click **Execute**. Expect HTTP `201` and `"status": "stored"`.

### Extract the paper template

Expand **POST `/api/v1/extract`**, click **Try it out**, and submit only:

```json
{
  "paper_id": "testpaper_01"
}
```

Expect HTTP `200` and a `PaperTemplate` containing the paper ID, title, problem,
method, datasets, findings, and limitations. Extraction calls Gemini twice:
once to select sections and once to fill the template, so it may take a little
while.

### Verify a claim

Expand **POST `/api/v1/verify`** (not `/api/v1/extract`), click **Try it out**,
and submit:

```json
{
  "paper_id": "testpaper_01",
  "evidence": {
    "claim": "The method is evaluated on a sample dataset.",
    "quote": "The method is evaluated on a sample dataset.",
    "section": "Results"
  }
}
```

Expect HTTP `200` and `"verified": true`.

The paper store defaults to `paper_store.sqlite3`; set `PAPER_STORE_DB_PATH` to
change its location. The reader also accepts title and sections directly in
`/api/v1/extract`, for compatibility with the supervisor. `/api/v1/verify`
accepts `paper_text` directly or loads sections from the store when omitted.

## 4. Team contract compatibility

The original `/api/v1/extract` and `/api/v1/connections` routes remain
available. For integration with the team repository's provisional
`group3.common` contracts, use the additional routes below. These routes accept
the team's `PaperDocument`, `ReaderResult`, `Evidence`, `Connection`, and
`Claim` field shapes. They do not read the teammate's JSON store by filesystem
path; send the stored `PaperDocument` JSON as the request body instead.

### Analyze a team PaperDocument

Send one complete `PaperDocument` JSON object (for example, the JSON file
produced by the retrieval agent) to `POST /api/v1/group3/read`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/group3/read \
  -H 'Content-Type: application/json' \
  --data-binary @path/to/paper-document.json
```

The response has two fields: `reader_result` and `evidence`. Claims use the
team's `claim_id`, `text`, and `evidence_ids` fields; evidence uses
`evidence_id`, `paper_id`, `section_id`, and `quote`. The reader rejects quotes
that are not exact substrings of the referenced source section, unknown
section IDs, cross-paper evidence, or invalid claim/evidence links.

Keep the original `PaperDocument` for the writer's `papers` field. Collect
each response's `reader_result` into `reader_results` and all `evidence`
records into the writer's `evidence` field.

### Generate team-format connections

With Agent 3 running on port 8001, send at least two `reader_results` and their
combined evidence to `POST /api/v1/group3/connections`. Its response contains
`connections` and `research_gaps`, shaped for the matching `WriterRequest`
fields. Connection kinds are `similarity`, `difference`, and `conflict`;
claims cite the supplied evidence IDs. The service rejects unknown evidence
references and connections that are not supported across at least two papers.

Combine the Agent 3 response with the original papers, reader results,
evidence, common references, and topic to assemble the team's `WriterRequest`.
The contracts in the teammate repository are marked provisional, so confirm
schema changes with the team before relying on them as a final shared API.

## 5. Test Agent 3

Keep the reader running in terminal 1. Open a second terminal, activate the
same virtual environment, and set `GEMINI_API_KEY` and `GEMINI_MODEL` in that
terminal too. Start Agent 3:

```bash
uvicorn connections_service:app --reload --port 8001
```

Open [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs), expand **POST
`/api/v1/connections`**, and submit two or more paper templates. Example:

```json
{
  "papers": [
    {
      "paper_id": "testpaper_01",
      "title": "Test Paper",
      "core_problem": "This paper studies a sample research problem.",
      "proposed_method": "The authors propose a sample method.",
      "datasets": ["sample dataset"],
      "key_findings": ["The method is evaluated on a sample dataset."],
      "limitations": []
    },
    {
      "paper_id": "testpaper_02",
      "title": "Second Test Paper",
      "core_problem": "This paper studies a related sample research problem.",
      "proposed_method": "The authors use a sample method.",
      "datasets": ["sample dataset"],
      "key_findings": ["The sample method is evaluated on a different task."],
      "limitations": ["This is synthetic test data."]
    }
  ]
}
```

Expect HTTP `200` with relations, a cross-paper synthesis, and research gaps.
These example templates are synthetic test data, not real research findings.

## 6. Run the LLM-judge evaluation

The 12 test topics and their expected coverage points are in
[`evaluation/topics.json`](./evaluation/topics.json). The example report input
is [`evaluation/sample_reports.json`](./evaluation/sample_reports.json). With
the virtual environment active and a Gemini key exported in the current
terminal, run the judge as a module from the project directory:

```bash
python -m evaluation.llm_judge --reports evaluation/sample_reports.json
```

Use `--output PATH` to choose a different results file and `--model MODEL_ID`
to select another model ID available to your API key. Do not type the literal
placeholder `MODEL_ID`; replace it with a real model ID or omit `--model` to
use the configured default.

Scores are printed and saved to `evaluation/results.json`. The judge scores
accuracy, coverage, synthesis, evidence quality, and overall quality from 1
to 5, and lists missing coverage and unsupported claims. The sample report is
only a placeholder, so low scores are expected. Replace it with actual reports
for a meaningful evaluation. LLM-judge scores are an evaluation aid, not a
substitute for human review.

Use `python -m evaluation.llm_judge`, not
`python evaluation/llm_judge.py`; module execution is needed for package
imports.

## Troubleshooting

- **404 at `/` or `/favicon.ico`:** expected; open `/docs` for the API UI.
- **422 Unprocessable Entity:** check that you submitted the JSON body for the
  selected endpoint. In particular, send `evidence` to `/api/v1/verify`, not
  `/api/v1/extract`.
- **502 from a Gemini call:** read the response `detail`. A temporary
  `503 UNAVAILABLE` from Gemini can be retried later. An invalid API-key error
  means the key must be checked in Google AI Studio. A model-not-found error
  means choose a model available to the key and set `GEMINI_MODEL`.
- **Address already in use:** stop the existing Uvicorn process with
  Control+C before restarting it on that port.
