import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest, TaskState


async def call_agent(url: str, request: dict, timeout: float) -> dict:
    """Send one JSON request to an A2A agent and return the JSON result from its artifact."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
        client = await create_client(agent=card, client_config=ClientConfig(streaming=False, httpx_client=http))
        try:
            message = new_data_message(request, media_type='application/json', role=Role.ROLE_USER)
            async for response in client.send_message(SendMessageRequest(message=message)):
                task = response.task
                if task.status.state != TaskState.TASK_STATE_COMPLETED:
                    raise RuntimeError(f'{card.name} ended in state {TaskState.Name(task.status.state)}')
                return get_data_parts(task.artifacts[-1].parts)[0]
        finally:
            await client.close()
    raise RuntimeError(f'{card.name} sent no answer')
