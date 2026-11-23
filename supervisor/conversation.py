"""One-line summaries of the A2A messages between the supervisor and the agents, to watch a run live."""
from datetime import datetime

NO_SUMMARY = '(no summary)'
CLAIM_FIELDS = ('overview', 'methods', 'datasets', 'results', 'limitations')

def show(name: str, text: str) -> None:
    """Print one line of the conversation: the time, who it is about, and what happened."""
    print(f'[{datetime.now():%H:%M:%S}] {name} {text}', flush=True)


def subject(name: str, request: dict) -> str:
    """The agent's name, plus the paper's ID when the request is about one paper (the readers run at the same time)."""
    return f'{name} [{request["paper_id"]}]' if 'paper_id' in request else name

def _claims(reader_result: dict) -> int:
    return sum(len(reader_result.get(field, [])) for field in CLAIM_FIELDS)

REQUESTS = {
    'retrieve_papers': lambda r: f'find papers on "{r["topic"]}" (target {int(r["target_papers"])}, minimum {int(r["minimum_papers"])})',
    'read_paper': lambda r: 'check one claim' if 'evidence' in r else 'read paper',
    'common_references': lambda r: f'find common references of {len(r["paper_ids"])} papers',
    'find_connections': lambda r: f'compare {len(r["reader_results"])} papers ({len(r["evidence"])} evidence)',
    'write_report': lambda r: (f'revise report {r["report_id"][:8]}' if 'feedback' in r
                               else f'write report on "{r["topic"]}" ({len(r["papers"])} papers)'),
}

RESULTS = {
    'retrieve_papers': lambda r: f'{len(r["paper_ids"])} papers',
    'read_paper': lambda r: (f'verified: {"yes" if r["verified"] else "no"}' if 'verified' in r
                             else f'{_claims(r["reader_result"])} claims, {len(r["evidence"])} evidence'),
    'common_references': lambda r: f'{len(r["common_references"])} common reference(s)',
    'find_connections': lambda r: f'{len(r["connections"])} connection(s), {len(r["research_gaps"])} research gap(s)',
    'write_report': lambda r: f'report {r["report_id"][:8]}, revision {int(r["revision"])}, {r["status"]}',
}

def _describe(table: dict, skill_id: str, message: dict) -> str:
    """Look up the summary for this skill; any problem gives NO_SUMMARY, so printing can never break a run."""
    try:
        return table[skill_id](message)
    except Exception:
        return NO_SUMMARY


def describe_request(skill_id: str, request: dict) -> str:
    """A short summary of what the supervisor asks an agent to do."""
    return _describe(REQUESTS, skill_id, request)


def describe_result(skill_id: str, result: dict) -> str:
    """A short summary of what an agent sent back."""
    return _describe(RESULTS, skill_id, result)
