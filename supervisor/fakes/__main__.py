import asyncio
from urllib.parse import urlparse

import uvicorn

from supervisor.config import SupervisorSettings
from supervisor.fakes.answers import (
    answer_connections,
    answer_reader,
    answer_references,
    answer_retrieval,
    answer_writer,
)
from supervisor.fakes.server import build_fake_app


async def main() -> None:
    settings = SupervisorSettings()
    fakes = [
        ('Retrieval', 'retrieve_papers', settings.retrieval_url, answer_retrieval),
        ('Paper Reader', 'read_paper', settings.reader_url, answer_reader),
        ('Common References', 'common_references', settings.references_url, answer_references),
        ('Connections', 'find_connections', settings.connections_url, answer_connections),
        ('Writer', 'write_report', settings.writer_url, answer_writer),
    ]
    servers = []
    for name, skill_id, url, answer in fakes:
        address = urlparse(url)
        app = build_fake_app(name, skill_id, url, answer)
        config = uvicorn.Config(app, host=address.hostname, port=address.port, log_level='warning')
        servers.append(uvicorn.Server(config))
        print(f'Fake {name} on {url}')
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == '__main__':
    asyncio.run(main())
