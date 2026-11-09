"""Real loopback HTTP SDK smoke; optional live arXiv retrieval. Never calls Groq."""
import argparse
import asyncio
import json
import os
import socket
import threading
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn

from group3.a2a.server import create_app
from group3.common.config import Settings
from scripts.build_group2_example import build


@contextmanager
def running(agent):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(create_app(agent, base + "/"), log_level="error"))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline or not thread.is_alive():
                raise RuntimeError("local A2A server failed to start")
            time.sleep(.05)
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


async def send(client, base, operation, payload):
    response = await client.post(base + "/", json={"jsonrpc":"2.0", "id":uuid4().hex, "method":"message/send",
        "params":{"message":{"kind":"message","messageId":uuid4().hex,"role":"user","parts":[
            {"kind":"data","data":{"operation":operation,"payload":payload}}]},"configuration":{"blocking":True}}})
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(body["error"])
    task = body["result"]
    results = [a["parts"][0]["data"] for a in task.get("artifacts",[]) if a["name"] == "result.json"]
    if not results:
        raise RuntimeError("A2A task returned no result: " + json.dumps(task, ensure_ascii=False))
    return task, results[-1]


async def run(args):
    # Explicit example/extractive mode; actual Groq is not part of this smoke.
    os.environ["GROUP3_WRITER_MODE"] = "extractive"
    with ExitStack() as stack:
        bases = {name: stack.enter_context(running(name)) for name in ("retrieval","references","writer")}
        async with httpx.AsyncClient(timeout=700) as client:
            cards = {name:(await client.get(base+"/.well-known/agent-card.json")).json()["protocolVersion"] for name,base in bases.items()}
            retrieval = None
            task_id, run_id = args.task_id, args.run_id
            if args.retrieve:
                print(f"Starting real arXiv retrieval through A2A: target {args.target}, minimum {args.minimum}", flush=True)
                task, retrieval = await send(client, bases["retrieval"], "retrieve", {"task_id":task_id,"topic":"multi agent large language models","target_papers":args.target,"minimum_papers":args.minimum})
                assert retrieval["status"] == "completed", retrieval
                run_id = retrieval["run_id"]
                print(f"Retrieved {retrieval['selected_count']} real papers; analyzing references", flush=True)
            if not run_id:
                raise ValueError("provide --run-id or --retrieve")
            ref_task, refs = await send(client, bases["references"], "references", {"task_id":task_id,"run_id":run_id})
            folder = Settings().store_root.resolve() / task_id / run_id
            example = build(folder, task_id)
            examples = Path("examples")
            examples.mkdir(exist_ok=True)
            (examples / "group2-example.json").write_text(example.model_dump_json(indent=2), encoding="utf-8")
            writer_task, written = await send(client, bases["writer"], "write", example.model_dump(mode="json"))
            revision_task, revised = await send(client, bases["writer"], "revise", {"report_id":written["report_id"],"feedback":{"missing_sections":["research_gaps"],"note":"Check missing source inputs; do not invent research gaps."}})
            (examples / "report.md").write_text(revised["markdown"], encoding="utf-8")
            record = {"test_kind":"real_loopback_http_with_real_stored_papers_and_example_group2_inputs", "groq_called":False,
                "cards":cards, "retrieval":retrieval, "store_task_id":task_id, "store_run_id":run_id,
                "references_a2a_state":ref_task["status"]["state"], "references":refs,
                "writer_a2a_state":writer_task["status"]["state"], "writer":written,
                "revision_a2a_state":revision_task["status"]["state"], "revision":revised}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"A2A loopback success. Common refs: {len(refs['common_references'])}; Writer: {written['status']}; revision: {revised['revision']}", flush=True)
            print(f"Record: {args.output}; sample: examples/report.md", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieve", action="store_true", help="download actual papers using Retrieval A2A service")
    parser.add_argument("--task-id", default="a2a-live")
    parser.add_argument("--run-id")
    parser.add_argument("--target", type=int, default=8)
    parser.add_argument("--minimum", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("docs/test-results/a2a-loopback.json"))
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
