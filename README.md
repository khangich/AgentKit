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

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) create a virtual environment and install AgentKit in editable mode:

   ```bash
   pip install -e .
   ```

3. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.

4. Run the example app:

   ```bash
   agentkit run agent_app.py --reload
   ```

   The server listens on [http://localhost:8080](http://localhost:8080).

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
