import ast
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "message": "missing strategy path"}))
        return 2

    path = Path(sys.argv[1])
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
    except Exception as exc:
        print(json.dumps({"ok": False, "message": str(exc)}))
        return 1

    print(json.dumps({"ok": True, "message": "strategy syntax ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

