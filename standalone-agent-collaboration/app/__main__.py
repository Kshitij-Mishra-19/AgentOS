"""Command-line entrypoint.

Usage:
    python -m app "Create a project plan for launching a website"
    python -m app --title "Launch plan" "Create a project plan for launching a website"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.bootstrap import Application


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="Run a task through the Planner -> Executor -> Reviewer collaboration system.",
    )
    parser.add_argument("description", help="The task description to run.")
    parser.add_argument(
        "--title", default=None, help="Optional short title (defaults to the description)."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the final result as raw JSON only."
    )
    return parser.parse_args(argv)


async def _run(argv: list[str]) -> int:
    args = parse_args(argv)
    title = args.title or args.description[:80]

    app = Application.from_config_path()

    if not args.json:
        print(f"Task: {title}")
        print(f"Description: {args.description}")
        print("Running Planner -> Executor -> Reviewer workflow...\n")

    result = await app.run_task(title, args.description)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.success else 1

    print(f"Status: {result.status}")
    print(f"Revision cycles used: {result.revision_count}")

    if result.success:
        print("\nFinal output:")
        print(json.dumps(result.final_output, indent=2))
        if result.review:
            print("\nFinal review:")
            print(json.dumps(result.review, indent=2))
        print("\nWorkflow completed successfully.")
        return 0

    print(f"\nWorkflow FAILED: {result.error}")
    return 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(argv if argv is not None else sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
