#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import pathlib
import time
import urllib.request


REQUIRED_KEYS = {
    "source_id",
    "change_type",
    "title_ko",
    "summary_ko",
    "customer_impact",
    "required_actions_ko",
    "added_items",
    "changed_items",
    "removed_items",
    "evidence_quotes_en",
    "uncertainties_ko",
}
ARRAY_KEYS = {
    "required_actions_ko",
    "added_items",
    "changed_items",
    "removed_items",
    "evidence_quotes_en",
    "uncertainties_ko",
}


def post_json(url: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def validate_output(result: object, case: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["response is not a JSON object"]
    keys = set(result)
    if keys != REQUIRED_KEYS:
        errors.append(f"keys differ: missing={sorted(REQUIRED_KEYS - keys)}, extra={sorted(keys - REQUIRED_KEYS)}")
    if result.get("source_id") != case["id"]:
        errors.append("source_id mismatch")
    if result.get("change_type") not in {"added", "changed", "deprecated", "removed", "fixed", "security", "compatibility"}:
        errors.append("invalid change_type")
    impact = result.get("customer_impact")
    if not isinstance(impact, dict) or set(impact) != {"level", "description_ko"}:
        errors.append("invalid customer_impact object")
    elif impact.get("level") not in {"high", "medium", "low", "unknown"}:
        errors.append("invalid customer_impact.level")
    for key in ARRAY_KEYS:
        if not isinstance(result.get(key), list) or not all(isinstance(item, str) for item in result.get(key, [])):
            errors.append(f"{key} is not a string array")
    for quote in result.get("evidence_quotes_en", []):
        if quote not in case["source_text"]:
            errors.append(f"evidence is not an exact source substring: {quote!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://ollama:11434")
    parser.add_argument("--model", default="ornith-pg-brief:9b")
    parser.add_argument("--case", default="all")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="/results/latest.json")
    args = parser.parse_args()

    base = pathlib.Path(__file__).resolve().parent
    schema = json.loads((base / "schema.json").read_text())
    cases = json.loads((base / "cases.json").read_text())
    if args.case != "all":
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            raise SystemExit(f"unknown case: {args.case}")

    records = []
    for case in cases:
        prompt = (
            f"SOURCE_ID: {case['id']}\n"
            f"SOURCE_URL: {case['source_url']}\n"
            f"SOURCE_TEXT:\n{case['source_text']}\n\n"
            "Extract only supported facts. Return the schema-constrained JSON object. Keep Korean fields concise."
        )
        payload = {
            "model": args.model,
            "prompt": prompt,
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 384, "seed": 42},
        }
        started = time.monotonic()
        api_result = post_json(f"{args.api}/api/generate", payload, args.timeout)
        wall_seconds = time.monotonic() - started
        parse_error = None
        try:
            structured = json.loads(api_result.get("response", ""))
        except json.JSONDecodeError as exc:
            structured = None
            parse_error = str(exc)
        validation_errors = [parse_error] if parse_error else validate_output(structured, case)
        records.append(
            {
                "case": case,
                "output": structured,
                "validation_errors": validation_errors,
                "metrics": {
                    "wall_seconds": round(wall_seconds, 3),
                    "total_duration_ns": api_result.get("total_duration"),
                    "load_duration_ns": api_result.get("load_duration"),
                    "prompt_eval_count": api_result.get("prompt_eval_count"),
                    "prompt_eval_duration_ns": api_result.get("prompt_eval_duration"),
                    "eval_count": api_result.get("eval_count"),
                    "eval_duration_ns": api_result.get("eval_duration"),
                    "done_reason": api_result.get("done_reason"),
                },
            }
        )

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": args.model,
        "records": records,
    }
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(record["validation_errors"] for record in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
