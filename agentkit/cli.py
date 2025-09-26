"""Console entry points for AgentKit."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import uvicorn


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="agentkit", description="AgentKit developer tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an AgentKit app")
    run_parser.add_argument("app", help="Path to the agent_app.py file")
    run_parser.add_argument("--host", default="0.0.0.0")
    run_parser.add_argument("--port", type=int, default=8080)
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args(argv)

    if args.command == "run":
        app_path = Path(args.app).resolve()
        if not app_path.exists():
            raise SystemExit(f"App file not found: {app_path}")
        os.environ["AGENTKIT_APP"] = str(app_path)
        uvicorn.run("agentkit.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":  # pragma: no cover
    main()
