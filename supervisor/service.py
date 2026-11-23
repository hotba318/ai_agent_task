import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlparse
import uvicorn
from a2a.helpers import get_message_text, new_data_part, new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from starlette.applications import Starlette
from supervisor.config import SupervisorSettings
from supervisor.conversation import show
from supervisor.flow import (RunState, RunStopped, apply_decision, ask_about_claims,
                             complete_run, keepable_claims, prepare_run)
from supervisor.memory import RunMemory
from supervisor.review import keep_hint, keep_question, parse_keep_answer
from supervisor.validation import all_claims


class SupervisorExecutor(AgentExecutor):
    """Runs the supervisor for a topic over A2A, and asks the user about keepable claims when there are any."""

    def __init__(self, settings: SupervisorSettings, memory: RunMemory) -> None:
        self.settings = settings
        self.memory = memory
        self.waiting: dict[str, RunState] = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)

        def message(text: str):
            return updater.new_agent_message([new_text_part(text)])

        async def progress(text: str) -> None:
            show('Supervisor', text)
            await updater.update_status(TaskState.TASK_STATE_WORKING, message=message(text))

        text = get_message_text(context.message).strip()
        try:
            state = self.waiting.get(task.id)
            kind = 'topic' if state is None else 'answer'
            show('Supervisor', f'← User: {kind} "{text}"   task {task.id[:8]}')
            if state is None:
                if not text:
                    show('Supervisor', '→ User: no topic was sent  task state: FAILED')
                    await updater.failed(message('Please send a research topic as text.'))
                    return
                state = await prepare_run(text, self.settings, self.memory, progress)
                if keepable_claims(state):
                    self.waiting[task.id] = state
                    keepable = await ask_about_claims(state, self.memory)
                    show('Supervisor', f'→ User: {len(keepable)} claim(s) to keep or drop  task state: INPUT_REQUIRED')
                    await updater.requires_input(message(keep_question(keepable)))
                    return
            else:
                keepable = keepable_claims(state)
                chosen = parse_keep_answer(text, keepable)
                if chosen is None:
                    show('Supervisor', '→ User: answer not understood, asking again  task state: INPUT_REQUIRED')
                    await updater.requires_input(message(keep_hint(keepable)))
                    return
                del self.waiting[task.id]
                state = await apply_decision(state, chosen, self.memory)
            output = await complete_run(state, self.settings, self.memory, progress)
        except RunStopped as stopped:
            self.waiting.pop(task.id, None)
            show('Supervisor', f'→ User: run stopped ({stopped})  task state: FAILED')
            await updater.failed(message(f'Run stopped: {stopped}'))
            return
        summary = {
            'task_id': output.task_id,
            'report_path': str(output.report_path),
            'papers': len(output.papers),
            'claims': sum(len(all_claims(result)) for result in output.reader_results),
            'unable_to_verify': len(output.unverified),
            'kept_by_user': len(state.kept),
            'warnings': output.warnings,
        }
        await updater.add_artifact(
            parts=[new_text_part(output.final_report, media_type='text/markdown'),
                   new_data_part(summary, media_type='application/json')],
            name='final-report',
        )
        show('Supervisor', '→ User: final report  task state: COMPLETED')
        await updater.complete(message(f'Done. Report saved at {output.report_path}'))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancel is not supported.')

    async def interrupt_waiting(self) -> None:
        """Record the runs still waiting for the user's answer as interrupted; called when the service stops."""
        for state in self.waiting.values():
            await self.memory.finish_run(state.task_id, 'interrupted')
        self.waiting.clear()
        
def build_app(settings: SupervisorSettings, memory: RunMemory) -> Starlette:
    """The supervisor as an A2A agent: its card and its JSON-RPC endpoint."""
    skill = AgentSkill(
        id='literature_review',
        name='Literature review',
        description='Finds recent arXiv papers on a topic, compares them, checks every claim against its quote, '
                    'and returns a report.',
        input_modes=['text/plain'],
        output_modes=['text/markdown', 'application/json'],
        tags=['research', 'literature review'],
        examples=['multi-agent llms'],
    )
    card = AgentCard(
        name='ScholarLens Supervisor',
        description='Plans a literature review, calls the ScholarLens agents over A2A, and validates the report.',
        version='0.1.0',
        default_input_modes=['text/plain'],
        default_output_modes=['text/markdown', 'application/json'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[AgentInterface(protocol_binding='JSONRPC', url=settings.service_url, protocol_version='1.0')],
        skills=[skill],
    )
    executor = SupervisorExecutor(settings, memory)
    @asynccontextmanager
    async def lifespan(app: Starlette):
        yield
        await executor.interrupt_waiting()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = []
    routes.extend(create_agent_card_routes(card))
    routes.extend(create_jsonrpc_routes(handler, '/'))
    return Starlette(routes=routes, lifespan=lifespan)

async def main() -> None:
    settings = SupervisorSettings()
    memory = RunMemory(settings.memory_path)
    await memory.create_tables()
    address = urlparse(settings.service_url)
    config = uvicorn.Config(build_app(settings, memory), host=address.hostname, port=address.port, log_level='warning')
    print(f'ScholarLens supervisor on {settings.service_url}')
    await uvicorn.Server(config).serve()


if __name__ == '__main__':
    asyncio.run(main())