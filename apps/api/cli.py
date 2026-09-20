"""Minimal safe CLI. There is deliberately no unattended live-trading command."""

from __future__ import annotations

import argparse
import json

from apps.api.demo import build_math_demo
from apps.api.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="quantlab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("math-demo")
    subparsers.add_parser("serve")
    args = parser.parse_args()
    if args.command == "status":
        settings = get_settings()
        print(
            json.dumps(
                {
                    "mode": settings.trading_mode.upper(),
                    "live_enabled": settings.effective_live_trading_enabled,
                    "message": "Research before risk",
                },
                indent=2,
            )
        )
    elif args.command == "math-demo":
        print(json.dumps(build_math_demo(), indent=2, default=str))
    elif args.command == "serve":
        import uvicorn

        settings = get_settings()
        uvicorn.run(
            "apps.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=False,
        )


if __name__ == "__main__":
    main()
