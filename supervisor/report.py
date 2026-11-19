from pathlib import Path
from group3.agents.writer.renderer import text
from group3.common.schemas import PaperDocument
from supervisor.validation import UnverifiedClaim


def section_link(paper: PaperDocument, section_id: str) -> str:
    """A link to one section: the paper's page, plus the section's anchor when the page is arXiv HTML."""
    section = next(section for section in paper.sections if section.section_id == section_id)
    url = str(section.source_url)
    return f'{url}#{section_id}' if paper.parse_method == 'arxiv_html' else url


def supervisor_section(
    read_papers: list[PaperDocument], papers_kept: int, claims_kept: int, corrected: int,
    unverified: list[UnverifiedClaim], kept: list[UnverifiedClaim], warnings: list[str],
) -> str:
    """The supervisor's part of the final report: evidence-check summary, Unable to Verify list, kept claims, run warnings."""
    papers = {paper.paper_id: paper for paper in read_papers}
    parts = [
        '## 9. Supervisor Review',
        '### Evidence check',
        f'- Papers read: {len(read_papers)}; kept after the check: {papers_kept}\n'
        f'- Claims kept: {claims_kept} (corrected by their reader: {corrected})\n'
        f'- Claims removed as Unable to Verify: {len(unverified)}\n'
        f'- Claims kept by the user without verification: {len(kept)}',
        '### Unable to Verify',
    ]
    for item in unverified:
        paper = papers[item.paper_id]
        section_ids = dict.fromkeys(passage.section_id for passage in item.closest)
        links = ', '.join(f'[{text(section_id)}]({section_link(paper, section_id)})' for section_id in section_ids)
        parts.append(f'- {text(item.claim.text)} ({text(paper.title)})\n'
                     f'  - Reason: {text(item.reason)}\n'
                     f'  - Closest sections: {links or "none found"}')
    if not unverified:
        parts.append('None.')
    parts.append('### Kept by the user without verification')
    parts.append('\n'.join(f'- {text(item.claim.text)} ({text(papers[item.paper_id].title)})\n'
                           f'  - Not verified because: {text(item.reason)}' for item in kept) or 'None.')
    parts.append('### Run warnings')
    parts.append('\n'.join(f'- {text(warning)}' for warning in warnings) or 'None.')
    return '\n\n'.join(parts) + '\n'


def save_report(markdown: str, folder: Path, task_id: str) -> Path:
    """Save the final report as <task_id>.md in the reports folder and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{task_id}.md'
    path.write_text(markdown, encoding='utf-8')
    return path