import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from agent import run_agent
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "eval" / "results.json"

class RateLimitedModels:
    def __init__(self, models, interval=5.0):
        self.models = models
        self.interval = interval
        self.last_request = None

    def generate_content(self, **kwargs):
        if self.last_request is not None:
            elapsed = time.monotonic() - self.last_request
            remaining = self.interval - elapsed

            if remaining > 0:
                time.sleep(remaining)

        self.last_request = time.monotonic()
        return self.models.generate_content(**kwargs)


def check_answer(case, answer, trace):
    failures = []

    if case.get("tool"):
        matching_calls = [
            call for call in trace
            if call["tool"] == case["tool"]
            and (
                not case.get("booking_id")
                or call["arguments"].get("booking_id")
                == case["booking_id"]
            )
            and "error" not in call["result"]
        ]

        if not matching_calls:
            failures.append("Required tool call was not executed")

    for pattern in case.get("patterns", []):
        if not re.search(pattern, answer, flags=re.IGNORECASE):
            failures.append(f"Missing expected pattern: {pattern}")

    for pattern in case.get("forbidden", []):
        if re.search(pattern, answer, flags=re.IGNORECASE):
            failures.append(f"Forbidden content matched: {pattern}")

    for amount in case.get("amounts", []):
        pattern = (
            rf"(?<![\d.,]){re.escape(amount)}"
            rf"(?:[.,]00)?(?!\d|[.,]\d)"
        )

        if not re.search(pattern, answer):
            failures.append(f"Missing exact amount: {amount} EUR")

    return failures


def main():
    load_dotenv(ROOT / ".env")

    api_key = os.getenv("AI_API_KEY")
    model = os.getenv("AI_MODEL")

    if not api_key or not model:
        raise SystemExit("Set AI_API_KEY and AI_MODEL in .env")

    cases = json.loads(
        (ROOT / "eval" / "cases.json").read_text(encoding="utf-8")
    )

    report = {
        "model": model,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
    }

    with genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    ) as client:
        limited_client = SimpleNamespace(
            models=RateLimitedModels(client.models)
        )
        for index, case in enumerate(cases):
            trace = []
            print(f"\n[{index + 1}/{len(cases)}] {case['id']}", flush=True)

            result = {"case": case, "trace": trace}

            try:
                answer = run_agent(
                    limited_client,
                    model,
                    case["question"],
                    trace=trace,
                )
                failures = check_answer(case, answer, trace)

                result.update({
                    "status": "fail" if failures else "pass",
                    "answer": answer,
                    "failures": failures,
                })

            except (errors.APIError, httpx.RequestError) as error:
                result.update({
                    "status": "error",
                    "error": str(error).replace(api_key, "[REDACTED]"),
                })

            report["results"].append(result)

            # Save after each question to preserve partial results.
            RESULTS_PATH.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print(result["status"].upper(), flush=True)

    passed = sum(
        item["status"] == "pass"
        for item in report["results"]
    )
    print(f"\nAutomatic checks passed: {passed}/{len(cases)}")
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
