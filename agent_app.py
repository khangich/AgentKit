"""Example AgentKit application."""

from agentkit import run_agent, ui


with ui.page("AgentKit Demo", "Minimal LangChain agent template"):
    task = ui.text_input("Task", placeholder="Ask a question or describe a task")
    attachments = ui.file_uploader("Attachments", accept=["text/plain", "application/pdf"])
    run_button = ui.button("Run Agent")
    ui.chat()

    if run_button and task.value:
        run_agent({"task": task.value}, files=attachments.value)
