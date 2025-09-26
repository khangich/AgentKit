"""Interactive LangChain agent sample that requires user input via AgentKit UI."""

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


def build_math_agent() -> AgentExecutor:
    """Create the LangChain agent executor used in the UI sample."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    tools = [multiply]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a patient math tutor. Respond in a {tone} tone and explain each step.",
            ),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


class LangChainUIStreamHandler(AsyncCallbackHandler):
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


async def _execute_agent_run(run_id: str, question: str, tone: str) -> None:
    tone = tone or "encouraging"
    try:
        store.append_event(run_id, "status", {"message": "LangChain agent started."})

        if not os.getenv("OPENAI_API_KEY"):
            offline_text = (
                "OPENAI_API_KEY is not configured. Returning offline stub response."
            )
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

        agent = build_math_agent()
        handler = LangChainUIStreamHandler(run_id)
        result = await agent.ainvoke(
            {"input": question, "tone": tone},
            callbacks=[handler],
        )
        store.append_event(
            run_id,
            "final",
            {"text": result["output"], "artifacts": []},
        )
        store.finish_run(run_id, "succeeded")
    except Exception as exc:  # pragma: no cover - defensive
        store.append_event(run_id, "error", {"message": str(exc)})
        store.finish_run(run_id, "failed")


def run_langchain_tutor(question: str, tone: str) -> str:
    cleaned_tone = tone.strip() or "encouraging"
    run_id = store.create_run({"question": question, "tone": cleaned_tone})
    runtime = ui.get_runtime()
    if runtime:
        runtime.record_run(run_id)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_execute_agent_run(run_id, question, cleaned_tone))
    else:
        loop.create_task(_execute_agent_run(run_id, question, cleaned_tone))
    return run_id


with ui.page(
    "LangChain Math Tutor",
    "Ask a math question and let a LangChain agent explain the answer.",
):
    problem_input = ui.text_input(
        "Math problem",
        placeholder="e.g., How do I compute (17 * 23) + 102?",
    )
    tone_input = ui.text_input(
        "Response tone",
        placeholder="e.g., encouraging, formal, playful",
    )
    run_button = ui.button("Solve")
    ui.chat()

    if run_button and problem_input.value.strip():
        run_langchain_tutor(problem_input.value.strip(), tone_input.value)


if __name__ == "__main__":
    question = "What is (17 * 23) + 102? Show your reasoning."
    tone = "encouraging"
    agent = build_math_agent()
    result = agent.invoke({"input": question, "tone": tone})
    print(result["output"])
