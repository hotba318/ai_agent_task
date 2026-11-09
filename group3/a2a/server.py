"""Replaceable A2A 0.3 adapter (SDK 0.3.22), pending Group 1 agreement."""
import argparse
import asyncio
import json
from typing import Awaitable, Callable

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (AgentCapabilities, AgentCard, AgentSkill, DataPart, Part,
                       TaskNotCancelableError, TaskState, TextPart)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from pydantic import ValidationError

from group3.common.analysis_schemas import ReferencesRequest, RevisionRequest, WriterRequest
from group3.common.config import AnalysisSettings, Settings
from group3.common.schemas import RetrievalRequest
from group3.agents.writer.state import RevisionLimitError


async def dispatch(agent: str, operation: str, payload: dict):
    from group3.cli import retrieve
    from group3.services import analyze_references, write_report
    if agent == "retrieval" and operation == "retrieve":
        return await retrieve(RetrievalRequest.model_validate(payload), Settings())
    if agent == "references" and operation == "references":
        return await asyncio.to_thread(analyze_references, ReferencesRequest.model_validate(payload), Settings())
    if agent == "writer" and operation in {"write", "revise"}:
        model = WriterRequest if operation == "write" else RevisionRequest
        return await write_report(model.model_validate(payload), AnalysisSettings())
    raise ValueError("operation is not supported by this agent")


class Group3Executor(AgentExecutor):
    def __init__(self, agent, handler: Callable[[str, str, dict], Awaitable] = dispatch, timeout=600):
        self.agent, self.handler, self.timeout = agent, handler, timeout
        # Retrieval requests serialize in this service instance. No uncoordinated downloads.
        self.retrieval_lock = asyncio.Lock()
        self.retrieval_finished = None

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task = context.current_task
        if task is None:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        try:
            values = [part.root.data for part in context.message.parts if isinstance(part.root, DataPart)]
            if values:
                if len(values) != 1 or len(context.message.parts) != 1:
                    raise ValueError("send exactly one DataPart")
                envelope = values[0]
            else:
                envelope = json.loads(context.get_user_input())
            if not isinstance(envelope, dict) or set(envelope) != {"operation", "payload"} or not isinstance(envelope["payload"], dict):
                raise ValueError("expected operation/payload envelope")
            async def invoke():
                if self.agent == "retrieval":
                    async with self.retrieval_lock:
                        if self.retrieval_finished is not None:
                            await asyncio.sleep(max(0, 15 - (asyncio.get_running_loop().time() - self.retrieval_finished)))
                        try:
                            return await self.handler(self.agent, envelope["operation"], envelope["payload"])
                        finally:
                            self.retrieval_finished = asyncio.get_running_loop().time()
                return await self.handler(self.agent, envelope["operation"], envelope["payload"])
            result = await asyncio.wait_for(invoke(), timeout=self.timeout)
            data = result.model_dump(mode="json")
            await updater.add_artifact([Part(root=DataPart(data=data))], name="result.json")
            if self.agent == "writer":
                await updater.add_artifact([Part(root=TextPart(text=result.markdown))], name="report.md")
            status = data.get("status")
            if status in {"insufficient_papers", "coverage_incomplete"} or data.get("review_required"):
                await updater.requires_input(new_agent_text_message("Provisional policy: review missing inputs in result artifact; provide corrected input or one Writer revision."), final=True)
            elif status == "failed":
                await updater.failed(new_agent_text_message("Agent failed; inspect result artifact failures."))
            else:
                await updater.complete()
        except Exception as exc:
            code = "revision_limit" if isinstance(exc, RevisionLimitError) else "invalid_input" if isinstance(exc, (ValidationError, ValueError, json.JSONDecodeError)) else "timeout" if isinstance(exc, TimeoutError) else "not_found" if isinstance(exc, FileNotFoundError) else "execution_error"
            # Only safe error classes expose details; never return credentials/upstream bodies.
            detail = str(exc) if isinstance(exc, RevisionLimitError) else "Check input fields and evidence references." if code == "invalid_input" else "Configured task deadline exceeded." if code == "timeout" else "Requested stored resource was not found." if code == "not_found" else "Agent execution failed; check local service configuration."
            await updater.add_artifact([Part(root=DataPart(data={"error": {"code": code, "detail": detail}}))], name="error.json")
            await updater.failed(new_agent_text_message(detail))

    async def cancel(self, context, event_queue):
        raise ServerError(error=TaskNotCancelableError())


def create_app(agent: str, base_url: str, *, handler=dispatch, timeout=600):
    if agent not in {"retrieval", "references", "writer"}:
        raise ValueError("unknown agent")
    card = AgentCard(name=f"Group3 {agent}", description="Provisional Group 3 service. SDK 0.3.22 / protocol 0.3.0; team contract pending.",
        url=base_url, version="0.1.0", protocol_version="0.3.0",
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["application/json"], default_output_modes=["application/json", "text/markdown"],
        skills=[AgentSkill(id=agent, name=agent, description="See README for operation/payload contracts.", tags=["papers", agent])])
    executor = Group3Executor(agent, handler, timeout)
    request_handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=card, http_handler=request_handler).build()


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="Group 3 A2A service (provisional SDK pin)")
    parser.add_argument("--agent", choices=["retrieval", "references", "writer"], required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--public-url")
    args = parser.parse_args()
    app = create_app(args.agent, args.public_url or f"http://{args.host}:{args.port}/", timeout=AnalysisSettings().task_timeout_seconds)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
