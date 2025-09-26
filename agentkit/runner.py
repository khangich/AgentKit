"""LangChain agent runner used by the FastAPI server."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from . import ui
from .config import AgentConfig, load_config
from .state import store


class StreamCallbackHandler(AsyncCallbackHandler):
    """Stream LangChain callbacks into the run store."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # type: ignore[override]
        store.append_event(self.run_id, "token", {"text": token})

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:  # type: ignore[override]
        tool_name = serialized.get("name") or serialized.get("id") or "tool"
        store.append_event(
            self.run_id,
            "tool_start",
            {"tool": tool_name, "input": input_str},
        )

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:  # type: ignore[override]
        store.append_event(self.run_id, "tool_end", {"output": output})

    async def on_llm_end(self, response, **kwargs: Any) -> None:  # type: ignore[override]
        # Final token events are handled by the final event.
        return


async def _ainvoke_model(config: AgentConfig, prompt: str, run_id: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        message = "OPENAI_API_KEY is not configured. Returning offline stub response."
        store.append_event(run_id, "token", {"text": message})
        return "Unable to execute agent without API credentials."

    handler = StreamCallbackHandler(run_id)
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
        streaming=True,
        callbacks=[handler],
    )
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are AgentKit, a helpful assistant."),
            ("human", "{input}"),
        ]
    )
    chain = prompt_template | llm | StrOutputParser()
    result = await chain.ainvoke({"input": prompt})
    return result


async def _execute_run(run_id: str, inputs: Dict[str, Any], files: Optional[List[Path]]) -> None:
    try:
        config = load_config()
        store.append_event(run_id, "status", {"message": "Agent started."})
        prompt = build_prompt(inputs, files)
        final_text = await _ainvoke_model(config, prompt, run_id)
        store.append_event(
            run_id,
            "final",
            {
                "text": final_text,
                "artifacts": [str(path) for path in files or []],
            },
        )
        store.finish_run(run_id, "succeeded")
    except Exception as exc:  # pragma: no cover - defensive
        store.append_event(run_id, "error", {"message": str(exc)})
        store.finish_run(run_id, "failed")


def build_prompt(inputs: Dict[str, Any], files: Optional[List[Path]]) -> str:
    prompt_parts = ["Task:", json.dumps(inputs, indent=2)]
    if files:
        prompt_parts.append("Files provided:")
        prompt_parts.extend(str(path) for path in files)
    return "\n".join(prompt_parts)


def run_agent(inputs: Dict[str, Any], files: Optional[Iterable[Path]] = None) -> str:
    """Create a run record and schedule the LangChain agent."""

    file_list = list(files or [])
    run_id = store.create_run(inputs)
    runtime = ui.get_runtime()
    if runtime:
        runtime.record_run(run_id)

    loop = asyncio.get_running_loop()
    loop.create_task(_execute_run(run_id, inputs, file_list))
    return run_id


__all__ = ["run_agent"]
