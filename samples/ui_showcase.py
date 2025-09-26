"""AgentKit UI showcase sample app."""

from __future__ import annotations

from agentkit import run_agent, ui


with ui.page(
    "AgentKit UI Showcase",
    "Demonstrate every currently supported AgentKit UI component.",
):
    text_value = ui.text_input(
        "Text input",
        placeholder="Describe a task for the agent",
    )
    uploaded_files = ui.file_uploader(
        "File uploader",
        accept=["text/plain", "application/pdf", "image/*"],
        multiple=True,
    )
    run_button = ui.button("Run agent")
    ui.chat()

    if run_button:
        run_agent(
            {
                "text_input": text_value.value,
                "file_count": len(uploaded_files.value),
            },
            files=uploaded_files.value,
        )
