# AgentKit

AgentKit is a minimal "Streamlit for agents" framework. Build LangChain-powered agent apps in a single `agent_app.py` file, stream outputs to the browser, and persist runs automatically.

## Features

- 1-file mental model: declare inputs and agent execution in `agent_app.py` using the `agentkit.ui` DSL.
- FastAPI + server-rendered HTML with zero frontend build steps.
- Live token streaming, tool traces, and artifact listing over Server-Sent Events.
- SQLite-backed persistence for runs, events, and uploaded files.
- One-command dev server: `agentkit run agent_app.py --reload`.
- Docker image for production (`uvicorn agentkit.server:app`).

## Quickstart

Follow these steps to run the example app locally.

1. Ensure you have Python 3.10+ available.
2. Create and activate a virtual environment (use `./.venv/Scripts/activate` on Windows):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies and expose the AgentKit CLI:

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. Copy `.env.example` to `.env` and populate it with your secrets (at minimum `OPENAI_API_KEY`):

   ```bash
   cp .env.example .env
   ```

5. Start the development server:

   ```bash
   agentkit run agent_app.py --reload
   ```

6. Open http://localhost:8080 in your browser to interact with the app.

## Sample apps

Once the environment is set up, you can explore the sample projects under `samples/` from the repo root with the AgentKit CLI:

- `samples/minimal_agent.py` – minimal echo agent for validating the UI shell. Run: `agentkit run samples/minimal_agent.py --reload`
- `samples/ui_showcase.py` – demonstrates every UI control AgentKit ships with. Run: `agentkit run samples/ui_showcase.py --reload`
- `samples/langchain_ui_agent.py` – LangChain math tutor that streams tokens back through the UI (requires `OPENAI_API_KEY`). Run: `agentkit run samples/langchain_ui_agent.py --reload`
- `samples/langchain_standalone_agent.py` – LangChain quickstart agent with optional CLI mode (also `python samples/langchain_standalone_agent.py`, requires `OPENAI_API_KEY`). Run: `agentkit run samples/langchain_standalone_agent.py --reload`
- `samples/startup_research_app.py` – two-agent startup research workflow that relies on your configured OpenAI model (`OPENAI_API_KEY`). Run: `agentkit run samples/startup_research_app.py --reload`
- `samples/crewai_agent_sample.py` – CrewAI integration demo; install CrewAI first (`pip install crewai`) then run via AgentKit or `python samples/crewai_agent_sample.py`. Run: `agentkit run samples/crewai_agent_sample.py --reload`

Samples that call OpenAI will emit placeholder output if the API key is missing, so populate `.env` with your credentials for the best experience.

## Writing an agent app

```python
from agentkit import run_agent, ui

with ui.page("Demo", "Ask any question"):
    task = ui.text_input("Task")
    attachments = ui.file_uploader("Files")
    run = ui.button("Run Agent")
    ui.chat()

    if run and task.value:
        run_agent({"task": task.value}, files=attachments.value)
```

Inputs become HTML form controls automatically. When the button is pressed, `run_agent` records a run, streams model output to the UI, and persists everything to SQLite.

## Configuration

- `agent.yaml` controls the default model and enabled tools.
- `.env` provides environment variables such as `OPENAI_API_KEY` and `AGENTKIT_DATABASE`.
- Uploaded files are stored in `data/uploads/` and logged in SQLite.

## Testing

Run the smoke test suite with `pytest`:

```bash
pytest
```

## Docker

Build and run the production image:

```bash
docker build -t agentkit .
docker run -p 8080:8080 agentkit
```
