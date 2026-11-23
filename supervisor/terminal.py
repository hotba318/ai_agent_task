"""Reading the user's answers in a terminal."""
import asyncio
import threading


async def read_line(prompt: str) -> str:
    """input() in a daemon thread, so Ctrl+C ends the program at once instead of waiting for Enter."""
    loop = asyncio.get_running_loop()
    answer = loop.create_future()

    def read() -> None:
        try:
            line = input(prompt)
        except EOFError as error:
            loop.call_soon_threadsafe(answer.set_exception, error)
        else:
            loop.call_soon_threadsafe(answer.set_result, line)

    threading.Thread(target=read, daemon=True).start()
    return await answer