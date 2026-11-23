import argparse
import asyncio
import sys
import httpx
from a2a.client import A2ACardResolver, AgentCardResolutionError, ClientConfig, create_client
from a2a.helpers import get_data_parts, get_message_text, new_text_message
from a2a.types import Role, SendMessageRequest, TaskState
from supervisor.config import SupervisorSettings
from supervisor.terminal import read_line

def _show_summary(summary: dict) -> None:
    """Print the counts and warnings from the report's JSON summary."""
    print(f"{int(summary['papers'])} papers, {int(summary['claims'])} claims, "
          f"{int(summary['unable_to_verify'])} Unable to Verify, {int(summary['kept_by_user'])} kept by you")
    for warning in summary['warnings']:
        print(f'Warning: {warning}')


async def _send(client, text: str, task_id: str | None, context_id: str | None):
    """Send one message, print the progress that streams back, and return the task IDs, its last state and message."""
    message = new_text_message(text, role=Role.ROLE_USER, task_id=task_id, context_id=context_id)
    state, last = TaskState.TASK_STATE_UNSPECIFIED, ''
    async for event in client.send_message(SendMessageRequest(message=message)):
        kind = event.WhichOneof('payload')
        if kind == 'task':
            task_id, context_id = event.task.id, event.task.context_id
        elif kind == 'status_update':
            state = event.status_update.status.state
            last = get_message_text(event.status_update.status.message)
            if state == TaskState.TASK_STATE_WORKING:
                print(last, flush=True)
        elif kind == 'artifact_update':
            _show_summary(get_data_parts(event.artifact_update.artifact.parts)[0])
    return task_id, context_id, state, last

async def ask(topic: str, url: str) -> int:
    """Ask the supervisor service for a review of the topic; answer its questions in the terminal. Returns the exit code."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
        client = await create_client(agent=card, client_config=ClientConfig(streaming=True, httpx_client=http))
        try:
            task_id, context_id, state, last = await _send(client, topic, None, None)
            while state == TaskState.TASK_STATE_INPUT_REQUIRED:
                print(last)
                answer = await read_line( '> ')
                task_id, context_id, state, last = await _send(client, answer, task_id, context_id)
        finally:
            await client.close()
    print(last or f'The task ended in state {TaskState.Name(state)}.')
    return 0 if state == TaskState.TASK_STATE_COMPLETED else 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Ask the supervisor A2A service for a literature review.')
    parser.add_argument('--topic', required=True, help='the research topic, for example "multi-agent llms"')
    parser.add_argument('--url', default=SupervisorSettings().service_url, help='the supervisor service address')
    args = parser.parse_args()
    try:
        return asyncio.run(ask(args.topic, args.url))
    except AgentCardResolutionError:
        print(f'Cannot reach the supervisor at {args.url}. Is "python -m supervisor.service" running?')
        return 1


if __name__ == '__main__':
    sys.exit(main())