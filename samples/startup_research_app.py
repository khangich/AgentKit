"""Tech startup two-agent research sample for AgentKit."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agentkit import ui
from agentkit.config import load_config
from agentkit.state import store
from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class StageStreamHandler(AsyncCallbackHandler):
    """Stream LLM tokens, tool events, and errors to the AgentKit console."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # type: ignore[override]
        store.append_event(self.run_id, "token", {"text": token})

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:  # type: ignore[override]
        tool_name = serialized.get("name") or serialized.get("id") or "tool"
        store.append_event(
            self.run_id,
            "tool_start",
            {"tool": tool_name, "input": input_str},
        )

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:  # type: ignore[override]
        store.append_event(self.run_id, "tool_end", {"output": output})


async def _invoke_stage(
    run_id: str,
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float,
    model_name: str,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        offline_message = (
            "OPENAI_API_KEY is not configured. Returning offline stub response."
        )
        store.append_event(run_id, "token", {"text": offline_message})
        return "Unable to execute agent without API credentials."

    handler = StageStreamHandler(run_id)
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        callbacks=[handler],
        streaming=True,
    )
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    chain = prompt_template | llm | StrOutputParser()
    result = await chain.ainvoke({"input": user_prompt})
    return result


async def _execute_workflow(run_id: str, topic: str) -> None:
    try:
        config = load_config()
        model_name = config.model.name
        temperature = config.model.temperature

        store.append_event(
            run_id,
            "token",
            {
                "text": (
                    "Starting research analyst agent for tech startups...\n"
                )
            },
        )

        research_system_prompt = (
            "You are a senior research analyst specializing in technology startups. "
            "Provide detailed, well-structured findings with market context, "
            "notable competitors, funding environment, risks, and emerging opportunities."
        )
        research_user_prompt = (
            "Conduct a deep research analysis on the following tech startup topic. "
            "Synthesize current trends, cite notable examples, and highlight actionable insights.\n\n"
            f"Topic: {topic}"
        )
        research_result = await _invoke_stage(
            run_id,
            research_system_prompt,
            research_user_prompt,
            temperature=temperature,
            model_name=model_name,
        )

        store.append_event(
            run_id,
            "token",
            {
                "text": (
                    "\n---\nResearch agent complete. Launching summarizer agent...\n\n"
                )
            },
        )

        summary_system_prompt = (
            "You are an executive briefing specialist. Summarize research into a concise "
            "narrative that highlights market outlook, key metrics, and strategic takeaways."
        )
        summary_user_prompt = (
            "Summarize the following research findings for a busy founder. "
            "Provide a short narrative followed by bullet-point takeaways and next steps.\n\n"
            f"Research findings:\n{research_result}"
        )
        summary_result = await _invoke_stage(
            run_id,
            summary_system_prompt,
            summary_user_prompt,
            temperature=max(0.2, temperature - 0.2),
            model_name=model_name,
        )

        store.append_event(
            run_id,
            "final",
            {"text": summary_result, "artifacts": []},
        )
        store.finish_run(run_id, "succeeded")
    except Exception as exc:  # pragma: no cover - defensive safeguard
        store.append_event(run_id, "error", {"message": str(exc)})
        store.finish_run(run_id, "failed")


def run_research_workflow(topic: str) -> str:
    run_id = store.create_run({"topic": topic})
    runtime = ui.get_runtime()
    if runtime:
        runtime.record_run(run_id)
    loop = asyncio.get_running_loop()
    loop.create_task(_execute_workflow(run_id, topic))
    return run_id


with ui.page(
    "Startup Research Lab",
    "Run a two-agent pipeline: research tech startups and summarize the findings.",
):
    topic_input = ui.text_input(
        "Research prompt",
        placeholder="e.g., Assess the market outlook for robotics startups in healthcare",
    )
    research_button = ui.button("Research")

    if research_button and topic_input.value.strip():
        run_research_workflow(topic_input.value.strip())
