"""Minimal safe CLI. There is deliberately no unattended live-trading command."""

from __future__ import annotations

import argparse
import json

from apps.api.demo import build_math_demo


def main() -> None:
    parser = argparse.ArgumentParser(prog="quantlab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("math-demo")
    args = parser.parse_args()
    if args.command == "status":
        print(
            json.dumps(
                {"mode": "PAPER", "live_enabled": False, "message": "Research before risk"},
                indent=2,
            )
        )
    elif args.command == "math-demo":
        print(json.dumps(build_math_demo(), indent=2, default=str))
