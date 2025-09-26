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
