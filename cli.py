"""
CLI interface for edit-file.

Usage:
    edit-file read <path>
    edit-file edit <path> --old <old_text> --new <new_text> [--skip-stale]
"""
from __future__ import annotations

import argparse
import json
import sys

from core import EditFile
from exceptions import EditFileError


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="edit-file",
        description="Reliable AI-agent code editor with 9-pass fuzzy reconciliation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # read
    read_p = sub.add_parser("read", help="Read a file and register its snapshot.")
    read_p.add_argument("path", help="File to read.")

    # edit
    edit_p = sub.add_parser("edit", help="Apply a search-and-replace edit.")
    edit_p.add_argument("path", help="File to edit.")
    edit_p.add_argument("--old", required=True, help="Text to find (old_text).")
    edit_p.add_argument("--new", required=True, help="Replacement text (new_text).")
    edit_p.add_argument(
        "--skip-stale",
        action="store_true",
        help="Bypass the stale-read check.",
    )
    edit_p.add_argument(
        "--json",
        action="store_true",
        help="Emit result as JSON.",
    )

    args = parser.parse_args()
    editor = EditFile()

    try:
        if args.command == "read":
            content = editor.read_file(args.path)
            sys.stdout.write(content)

        elif args.command == "edit":
            # Pre-read so the stale check has a baseline.
            editor.read_file(args.path)

            result = editor.edit_file(
                path=args.path,
                old_text=args.old,
                new_text=args.new,
                skip_stale_check=args.skip_stale,
            )
            if args.json:
                payload = {
                    "success": result.success,
                    "strategy": result.strategy_used.value if result.success else None,
                    "pass": result.pass_number,
                    "confidence": result.confidence,
                    "error": result.error,
                    "diagnostics": result.diagnostics,
                }
                print(json.dumps(payload, indent=2))
            else:
                if result.success:
                    print(
                        f"✓ Edit applied via Pass {result.pass_number} "
                        f"({result.strategy_used.value}) "
                        f"confidence={result.confidence:.2f}"
                    )
                else:
                    print(f"✗ Edit failed: {result.error}", file=sys.stderr)
                    sys.exit(1)

    except EditFileError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()