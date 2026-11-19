from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

from supervisor.fakes.agent import Answer, FakeAgentExecutor


def build_fake_app(name: str, skill_id: str, url: str, answer: Answer) -> Starlette:
    skill = AgentSkill(
        id=skill_id,
        name=name,
        description=f'Fake {name}: answers with sample data for testing the supervisor.',
        input_modes=['application/json'],
        output_modes=['application/json'],
        tags=['fake'],
    )
    card = AgentCard(
        name=f'Fake {name}',
        description='Stand-in agent for building and testing the supervisor',
        version='0.0.1',
        default_input_modes=['application/json'],
        default_output_modes=['application/json'],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[AgentInterface(protocol_binding='JSONRPC', url=url, protocol_version='1.0')],
        skills=[skill],
    )
    handler = DefaultRequestHandler(
        agent_executor=FakeAgentExecutor(answer),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = []
    routes.extend(create_agent_card_routes(card))
    routes.extend(create_jsonrpc_routes(handler, '/'))
    return Starlette(routes=routes)
