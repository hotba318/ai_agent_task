import time
import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest, TaskState
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from supervisor.conversation import describe_request, describe_result, show, subject

async def call_agent(url: str, request: dict, timeout: float) -> dict:
    """Send one JSON request to an A2A agent and return the JSON result from its artifact; each step is printed."""
    who = subject(url, request)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as http:
            card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
            show('Supervisor', f"read agent card '{card.name}' ({AGENT_CARD_WELL_KNOWN_PATH})")
            who = subject(card.name, request)
            skill_id = card.skills[0].id if card.skills else ''
            client = await create_client(agent=card, client_config=ClientConfig(streaming=False, httpx_client=http))
            try:
                message = new_data_message(request, media_type='application/json', role=Role.ROLE_USER)
                show('Supervisor', f'→ {who}: {describe_request(skill_id, request)}')
                started = time.monotonic()
                async for response in client.send_message(SendMessageRequest(message=message)):
                    task = response.task
                    if task.status.state != TaskState.TASK_STATE_COMPLETED:
                        raise RuntimeError(f'{card.name} ended in state {TaskState.Name(task.status.state)}')
                    result = get_data_parts(task.artifacts[-1].parts)[0]
                    show('Supervisor', f'← {who}: {describe_result(skill_id, result)}, task {task.id[:8]}, '
                                       f'COMPLETED ({time.monotonic() - started:.1f} s)')
                    return result
            finally:
                await client.close()
        raise RuntimeError(f'{card.name} sent no answer')
    except Exception as error:
        show('Supervisor', f'← {who}: failed: {type(error).__name__}: {str(error)[:100]}')
        raise
    