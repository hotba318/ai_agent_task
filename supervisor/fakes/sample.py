from functools import cache
from pathlib import Path

from group3.common.analysis_schemas import WriterRequest

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples'


@cache
def sample_input() -> WriterRequest:
    """Junkyung's sample writer input: 8 real papers with sections, reader results and evidence."""
    return WriterRequest.model_validate_json((EXAMPLES / 'writer-input.json').read_text(encoding='utf-8'))


@cache
def sample_report() -> str:
    """Junkyung's sample report in Markdown."""
    return (EXAMPLES / 'report.md').read_text(encoding='utf-8')
