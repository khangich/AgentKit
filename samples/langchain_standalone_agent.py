"""Standalone LangChain agent example with optional AgentKit UI support.

This sample mirrors the official LangChain quickstart for building a tool-using
agent: https://python.langchain.com/docs/use_cases/agents/quickstart

You can run it from the command line:

    export OPENAI_API_KEY="sk-..."
    python samples/langchain_standalone_agent.py

Or launch it inside the AgentKit UI via ``agentkit run samples/langchain_standalone_agent.py``.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agentkit import ui
from agentkit.state import store
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def build_agent() -> AgentExecutor:
    """Create the LangChain agent executor used in the quickstart example."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    tools = [multiply]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a math tutor who solves problems step by step. "
                "When helpful, call the available tools to do calculations.",
            ),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


class LangChainStandaloneStreamHandler(AsyncCallbackHandler):
    """Stream LangChain callbacks into the AgentKit run store."""

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


async def _execute_agent_run(run_id: str, question: str) -> None:
    question = question.strip()
    try:
        store.append_event(run_id, "status", {"message": "LangChain agent started."})

        if not os.getenv("OPENAI_API_KEY"):
            offline_text = "OPENAI_API_KEY is not configured. Returning offline stub response."
            store.append_event(run_id, "token", {"text": offline_text})
            store.append_event(
                run_id,
                "final",
                {
                    "text": "Unable to execute agent without API credentials.",
                    "artifacts": [],
                },
            )
            store.finish_run(run_id, "succeeded")
            return

        agent = build_agent()
        handler = LangChainStandaloneStreamHandler(run_id)
        result = await agent.ainvoke({"input": question}, callbacks=[handler])
        store.append_event(
            run_id,
            "final",
            {"text": result["output"], "artifacts": []},
        )
        store.finish_run(run_id, "succeeded")
    except Exception as exc:  # pragma: no cover - defensive
        store.append_event(run_id, "error", {"message": str(exc)})
        store.finish_run(run_id, "failed")


def run_langchain_standalone(question: str) -> str:
    cleaned_question = question.strip()
    run_id = store.create_run({"question": cleaned_question})
    runtime = ui.get_runtime()
    if runtime:
        runtime.record_run(run_id)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_execute_agent_run(run_id, cleaned_question))
    else:
        loop.create_task(_execute_agent_run(run_id, cleaned_question))
    return run_id


with ui.page(
    "LangChain Standalone Agent",
    "Run the LangChain quickstart agent from AgentKit's web UI.",
):
    question_input = ui.text_input(
        "Question",
        placeholder="e.g., What is (17 * 23) + 102? Show your work.",
    )
    run_button = ui.button("Run Agent")
    ui.chat()

    if run_button and question_input.value.strip():
        run_langchain_standalone(question_input.value)


def main() -> None:
    agent_executor = build_agent()
    question = "What is (17 * 23) + 102? Show your work."
    result = agent_executor.invoke({"input": question})
    print("Agent output:\n")
    print(result["output"])


if __name__ == "__main__":
    main()
