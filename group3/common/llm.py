"""Small structured Groq boundary shared by bounded agent decisions."""
import httpx
import asyncio
import re
import time
from dataclasses import dataclass
from pydantic import BaseModel, SecretStr


class GroqGenerationError(ValueError):
    """Provider could not produce schema-valid JSON; no upstream body/credential echo."""
    pass


async def wait_in_chunks(seconds):
    while seconds>0:
        chunk=min(seconds,60)
        await asyncio.sleep(chunk)
        seconds-=chunk


@dataclass
class TokenBudget:
    remaining: int | None = None
    reset_at: float = 0
    waits: int = 0
    http_attempts: int = 0

    def observe(self,headers):
        remaining=headers.get("x-ratelimit-remaining-tokens","")
        reset=headers.get("x-ratelimit-reset-tokens","")
        if remaining.lstrip("-").isdigit():
            self.remaining=int(remaining)
        matches=re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)",reset)
        if matches:
            seconds=sum(float(value)*{"ms":.001,"s":1,"m":60,"h":3600}[unit] for value,unit in matches)
            self.reset_at=time.monotonic()+seconds

    async def wait(self,estimated_tokens):
        remaining_time=self.reset_at-time.monotonic()
        if self.remaining is not None and estimated_tokens>self.remaining and remaining_time>0:
            if remaining_time>120:
                raise RuntimeError("Groq token budget requires a longer cooldown; retry after the provider reset")
            self.waits+=1
            await wait_in_chunks(remaining_time+1)
            self.remaining=None


async def structured_completion(client, key: SecretStr, model: str, schema: type[BaseModel], messages,
                                *, name: str, max_tokens=8192, budget=None):
    if not key.get_secret_value().strip():
        raise ValueError("GROQ_API_KEY is required")
    body = {"model":model,"temperature":0,"max_completion_tokens":max_tokens,"messages":messages,
        "response_format":{"type":"json_schema","json_schema":{"name":name,"strict":True,"schema":schema.model_json_schema()}}}
    if model.startswith("openai/gpt-oss-"):
        body["reasoning_effort"]="low"
    if budget is not None:
        import json
        await budget.wait(len(json.dumps(body,ensure_ascii=False).encode("utf-8"))//3+max_tokens)
    for attempt in range(2):
        if budget is not None:
            budget.http_attempts+=1
        try:
            response=await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":"Bearer "+key.get_secret_value()},json=body)
        except httpx.HTTPError as exc:
            raise RuntimeError("Groq transport failed: "+type(exc).__name__) from None
        if budget is not None:
            budget.observe(response.headers)
        wait=response.headers.get("Retry-After","")
        if response.status_code==429 and attempt==0 and re.fullmatch(r"\d+(?:\.\d+)?",wait) and float(wait)<=120:
            await wait_in_chunks(float(wait)+1)
            continue
        break
    if response.status_code>=400:
        budget=""
        error_code="unknown"
        try:
            value=response.json().get("error",{}).get("code","")
            if isinstance(value,str) and re.fullmatch(r"[a-z_]+",value):
                error_code=value
        except (ValueError,AttributeError):
            pass
        if response.status_code==400 and error_code in {"json_validate_failed","failed_generation"}:
            raise GroqGenerationError("Groq schema generation failed; regenerate a shorter schema-valid draft")
        if response.status_code==413:
            try:
                message=response.json().get("error",{}).get("message","")
                counts=re.search(r"Limit\s+(\d+).*Requested\s+(\d+)",message,re.S)
                if counts:
                    budget=f"; token limit={counts[1]}, requested={counts[2]}"
            except (ValueError,AttributeError):
                pass
        raise RuntimeError(f"Groq request failed (HTTP {response.status_code}; code={error_code}{budget})")
    choice=response.json()["choices"][0]
    if choice.get("finish_reason")!="stop" or not choice.get("message",{}).get("content"):
        raise ValueError("Groq response incomplete/refused")
    return schema.model_validate_json(choice["message"]["content"])
