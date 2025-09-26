"""AgentKit-compatible CrewAI sample with a minimal web UI."""

from __future__ import annotations

import asyncio
from agentkit import ui
from agentkit.state import store
from crewai import Agent, Crew, Process, Task


def build_crewai_agents(topic: str) -> Crew:
    """Create the researcher/writer crew used for the sample run."""

    researcher = Agent(
        role="Senior Research Analyst",
        goal="Discover the latest breakthroughs relevant to the assigned topic.",
        backstory="You excel at finding insightful sources and synthesizing concise briefs.",
    )

    writer = Agent(
        role="Tech Content Writer",
        goal="Produce a punchy and informative summary for a general audience.",
        backstory="You transform dense technical findings into clear, engaging reading.",
    )

    research_task = Task(
        description=(
            f"Investigate recent developments and noteworthy news about the '{topic}' topic. "
            "Collect key findings and cite reputable sources."
        ),
        agent=researcher,
        expected_output="Bullet list covering the 3 most newsworthy findings with source links.",
    )

    writing_task = Task(
        description=(
            f"Using the research notes, craft a crisp newsletter-style update about '{topic}'. "
            "Highlight why the findings matter to practitioners."
        ),
        agent=writer,
        expected_output="200-word summary referencing the provided sources.",
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
    )


def run_crewai_sync(topic: str) -> str:
    crew = build_crewai_agents(topic)
    return crew.kickoff(inputs={"topic": topic})


async def _execute_crewai_run(run_id: str, topic: str) -> None:
    try:
        store.append_event(run_id, "status", {"message": "Crew started"})
        result = await asyncio.to_thread(run_crewai_sync, topic)
        for line in result.splitlines(keepends=True):
            store.append_event(run_id, "token", {"text": line})
        store.append_event(run_id, "final", {"text": result, "artifacts": []})
        store.finish_run(run_id, "succeeded")
    except Exception as exc:  # pragma: no cover - defensive
        store.append_event(run_id, "error", {"message": str(exc)})
        store.finish_run(run_id, "failed")


def run_crewai(topic: str) -> str:
    run_id = store.create_run({"topic": topic})
    runtime = ui.get_runtime()
    if runtime:
        runtime.record_run(run_id)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_execute_crewai_run(run_id, topic))
    else:
        loop.create_task(_execute_crewai_run(run_id, topic))
    return run_id


with ui.page("CrewAI Researcher", "Run a two-agent CrewAI workflow through AgentKit"):
    topic_input = ui.text_input(
        "Research topic",
        placeholder="e.g. large language models",
    )
    run_button = ui.button("Run Crew")
    ui.chat()

    if run_button and topic_input.value:
        run_crewai(topic_input.value)


def main() -> None:
    topic = "large language models"
    print(run_crewai_sync(topic))


if __name__ == "__main__":
    main()
