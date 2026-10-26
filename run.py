"""Command-line entry point for nothingtodo."""

import argparse
import logging
import sys
from pathlib import Path

from core import digest, pipeline, store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dir", default="~/Downloads")
    parser.add_argument("--digest", action="store_true")
    parser.add_argument("--snooze", type=int)
    parser.add_argument("--resolve", type=int)
    args = parser.parse_args()
    store.init_db()

    if args.digest:
        path = digest.write_digest(digest.render_digest(store.open_items()))
        print(path)
        return 0
    if args.snooze is not None:
        count = store.snooze(args.snooze)
        print(f"Snoozed #{args.snooze} (now {count} snoozes)")
        return 0
    if args.resolve is not None:
        store.resolve(args.resolve)
        print(f"Resolved #{args.resolve}")
        return 0

    results = pipeline.process_dir(Path(args.dir).expanduser(), args.apply)
    for result in results:
        if "error" in result:
            print(f"ERROR                    {Path(result['path']).name[:40]:40} {result['error'][:60]}")
            continue
        verdict = result["verdict"]
        print(f"{result['tier_label']:24} {Path(result['path']).name[:40]:40} {verdict.two_line_verdict[:60]}")
    skipped = sum("skipped" in result for result in results)
    errors = sum("error" in result for result in results)
    print(f"{len(results)} processed, {skipped} skipped, {errors} errors")
    if args.apply:
        path = digest.write_digest(digest.render_digest(store.open_items()))
        print(path)
    else:
        print("DRY RUN — nothing written, no audio generated")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logging.exception("nothingtodo failed")
        sys.exit(1)
