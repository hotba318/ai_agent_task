from collections.abc import Callable
from typing import Any

from a2a.helpers import get_data_parts, new_data_part, new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState

Answer = Callable[[dict[str, Any]], dict[str, Any]]


class FakeAgentExecutor(AgentExecutor):
    """Answers every request with sample data in the contract shape."""

    def __init__(self, answer: Answer) -> None:
        self.answer = answer

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(state=TaskState.TASK_STATE_WORKING, message=new_text_message('Working (fake)'))

        request = get_data_parts(context.message.parts)[0]
        result = self.answer(request)

        await updater.add_artifact(parts=[new_data_part(result, media_type='application/json')])
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, message=new_text_message('Done (fake)'))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancel is not supported.')
