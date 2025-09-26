"""Minimal AgentKit sample app for smoke testing."""

from agentkit import run_agent, ui


with ui.page("Minimal Agent", "Single text input and run button"):
    prompt = ui.text_input("Prompt", placeholder="Type anything to echo")
    run = ui.button("Run Agent")
    ui.chat()

    if run and prompt.value:
        run_agent({"prompt": prompt.value})
