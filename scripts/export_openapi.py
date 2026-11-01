import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from api.openapi import openapi_contract_errors
    from main import app

    document = app.openapi()
    errors = openapi_contract_errors(document)
    if errors:
        raise SystemExit("OpenAPI export failed:\n" + "\n".join(errors))

    output_path = PROJECT_ROOT / "openapi.json"
    output_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
