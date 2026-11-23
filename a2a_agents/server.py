import time
from collections.abc import Awaitable, Callable
from typing import Any
from a2a.helpers import get_data_parts, new_data_part, new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from starlette.applications import Starlette
from supervisor.conversation import describe_request, describe_result, show, subject


Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class AgentWrapper(AgentExecutor):
    """Runs one agent per A2A request: the JSON request goes in, the agent's JSON result comes back as an artifact.

    Each A2A step is printed in this agent's terminal, so a run can be watched live.
    """
    
    def __init__(self, name: str, skill_id: str, handle: Handler) -> None:
        self.name = name
        self.skill_id = skill_id
        self.handle = handle

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        request = get_data_parts(context.message.parts)[0]
        who = subject(self.name, request)
        started = time.monotonic()
        show(who, f'← Supervisor: {describe_request(self.skill_id, request)}   task {task.id[:8]}')
        await updater.update_status(TaskState.TASK_STATE_WORKING, message=updater.new_agent_message([new_text_part('Working')]))
        show(who, '  task state: SUBMITTED → WORKING')
        try:
            result = await self.handle(request)
        except Exception as error:
            show(who, f'  error: {type(error).__name__}: {str(error)[:100]}')
            raise
        await updater.add_artifact(parts=[new_data_part(result, media_type='application/json')])
        show(who, f'  artifact added: {describe_result(self.skill_id, result)}')
        await updater.complete()
        show(who, f'  task state: COMPLETED ({time.monotonic() - started:.1f} s)')


    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancel is not supported.')


def build_agent_app(name: str, skill_id: str, description: str, url: str, handle: Handler) -> Starlette:
    """One agent as an A2A service: its card and its JSON-RPC endpoint."""
    skill = AgentSkill(
        id=skill_id,
        name=name,
        description=description,
        input_modes=['application/json'],
        output_modes=['application/json'],
        tags=['scholarlens'],
    )
    card = AgentCard(
        name=name,
        description=description,
        version='0.1.0',
        default_input_modes=['application/json'],
        default_output_modes=['application/json'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[AgentInterface(protocol_binding='JSONRPC', url=url, protocol_version='1.0')],
        skills=[skill],
    )
    handler = DefaultRequestHandler(agent_executor=AgentWrapper(name, skill_id, handle), task_store=InMemoryTaskStore(), agent_card=card)
    routes = []
    routes.extend(create_agent_card_routes(card))
    routes.extend(create_jsonrpc_routes(handler, '/'))
    return Starlette(routes=routes)
