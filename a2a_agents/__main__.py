import argparse
import asyncio
from urllib.parse import urlparse
import uvicorn
from a2a_agents import agents
from a2a_agents.server import build_agent_app
from supervisor.config import SupervisorSettings

AGENTS = {
    'retrieval': ('Retrieval Agent', 'retrieve_papers',
                  'Finds the newest on-topic arXiv papers and saves them in the paper store.', 'retrieval_url', agents.retrieval),
    'reader': ('Paper Reader', 'read_paper',
               'Reads one paper with Gemini, or checks one claim against its quote.', 'reader_url', agents.reader),
    'references': ('Common References', 'common_references',
                   'Finds the references cited by at least two of the papers.', 'references_url', agents.references),
    'connections': ('Connections', 'find_connections',
                    'Finds connections and research gaps between the papers.', 'connections_url', agents.connections),
    'writer': ('Writer', 'write_report',
               'Writes the literature review report, and revises it once for coverage.', 'writer_url', agents.writer),
}


async def serve(names: list[str]) -> None:
    """Start the named agents, each as its own A2A service on the address the supervisor expects."""
    settings = SupervisorSettings()
    servers = []
    for name in names:
        title, skill_id, description, setting, handle = AGENTS[name]
        url = getattr(settings, setting)
        address = urlparse(url)
        app = build_agent_app(title, skill_id, description, url, handle)
        servers.append(uvicorn.Server(uvicorn.Config(app, host=address.hostname, port=address.port, log_level='warning')))
        print(f'{title} on {url}', flush=True)
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:
    parser = argparse.ArgumentParser(description='Start the A2A wrappers for the team agents.')
    parser.add_argument('names', nargs='*', choices=list(AGENTS), help='the agents to start (default: all five)')
    args = parser.parse_args()
    asyncio.run(serve(args.names or list(AGENTS)))


if __name__ == '__main__':
    main()