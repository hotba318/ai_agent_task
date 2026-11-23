import argparse
import asyncio
import sys
from supervisor.config import SupervisorSettings
from supervisor.flow import RunStopped, run
from supervisor.memory import RunMemory
from supervisor.validation import UnverifiedClaim
from supervisor.review import keep_hint, keep_question, parse_keep_answer
from supervisor.terminal import read_line

async def _print_progress(message: str) -> None:
    """Show each progress message in the terminal as the run goes."""
    print(message, flush=True)


async def _ask_in_terminal(claims: list[UnverifiedClaim]) -> set[str]:
    """Ask in the terminal which claims to keep, until the answer can be understood."""
    print(keep_question(claims))
    while True:
        answer = await read_line('> ')
        chosen = parse_keep_answer(answer, claims)
        if chosen is not None:
            print(f'Keeping {len(chosen)} claim(s).', flush=True)
            return chosen
        print(keep_hint(claims))
        

async def _run_once(topic: str, settings: SupervisorSettings):
    """Prepare the memory, then run the supervisor once."""
    memory = RunMemory(settings.memory_path)
    await memory.create_tables()
    return await run(topic, settings, memory, _print_progress, _ask_in_terminal)


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the supervisor once for a research topic.')
    parser.add_argument('--topic', required=True, help='the research topic, for example "multi-agent llms"')
    args = parser.parse_args()
    try:
        output = asyncio.run(_run_once(args.topic, SupervisorSettings()))
    except RunStopped as stop:
        print(f'Run stopped: {stop}')
        return 1
    draft = output.draft
    print(f'Task {output.task_id}: draft {draft.report_id} (revision {draft.revision}, {draft.status})')
    print(f'{len(output.papers)} papers, {len(output.evidence)} evidence quotes, '
          f'{len(output.references.common_references)} common references, {len(output.connections)} connection(s)')
    for warning in output.warnings:
        print(f'Warning: {warning}')
    print(f'{len(output.unverified)} claim(s) Unable to Verify')
    for item in output.unverified:
        print(f'  {item.claim.claim_id}: {item.reason}')
        for passage in item.closest:
            print(f'    closest: {passage.section_id} | {passage.text[:80]}')
    print(f'Report saved by the writer at: {draft.markdown_path}')
    print(f'Final report (with the supervisor review) saved at: {output.report_path}')
    print('--- first lines of the report ---')
    print('\n'.join(draft.markdown.splitlines()[:15]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
