import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from urllib import error, request


SAMPLE_TEXTS = [
    "I forgot my umbrella again and got soaked walking back from the grocery store.",
    "Thank you for the update. I reviewed the draft and left a few notes for tomorrow.",
    "The committee recommends a phased rollout to minimize operational disruption and training risk.",
    "This comprehensive solution empowers organizations to unlock transformative efficiency at scale.",
    "Fix landed. Please pull main and rerun the failing migration.",
    "The function caches parsed tokens so repeated requests do not redo the full normalization pass.",
    "lol this was way harder than I thought but at least it works now",
    "Our analysis suggests that the observed variance is driven by uneven sample quality rather than model drift alone.",
    "The sunset looked unreal tonight, like the whole sky was orange for ten minutes.",
    "In summary, the platform delivers seamless collaboration, adaptive intelligence, and measurable business value.",
    "ship it",
    (
        "I spent the afternoon rewriting the onboarding flow because too many people were dropping off "
        "before the second step, and the new version feels much easier to follow."
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark LLM provider latency via the local Provenance Guard app.")
    parser.add_argument("--provider", choices=["groq", "ollama"], required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    return parser.parse_args()


def submit_text(base_url: str, provider: str, text: str, index: int) -> dict:
    payload = {
        "creator_id": f"benchmark-{provider}-{index}",
        "text": text,
        "llm_provider": provider,
    }
    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{base_url.rstrip('/')}/submit",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(http_request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_latencies(latencies: list[int]) -> dict:
    if not latencies:
        return {
            "average_llm_latency_ms": None,
            "median_llm_latency_ms": None,
            "min_llm_latency_ms": None,
            "max_llm_latency_ms": None,
        }

    return {
        "average_llm_latency_ms": round(sum(latencies) / len(latencies), 2),
        "median_llm_latency_ms": round(statistics.median(latencies), 2),
        "min_llm_latency_ms": min(latencies),
        "max_llm_latency_ms": max(latencies),
    }


def save_results(provider: str, results: dict) -> Path:
    output_dir = Path("benchmark_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"latency_{provider}_{timestamp}.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    total_requests = len(SAMPLE_TEXTS) * max(args.rounds, 1)
    latencies: list[int] = []
    failures: list[dict] = []

    request_index = 0
    for round_number in range(max(args.rounds, 1)):
        for sample_index, text in enumerate(SAMPLE_TEXTS):
            request_index += 1
            try:
                payload = submit_text(args.base_url, args.provider, text, request_index)
                latency_ms = payload.get("llm_latency_ms")
                if isinstance(latency_ms, int):
                    latencies.append(latency_ms)
                else:
                    failures.append({
                        "round": round_number + 1,
                        "sample_index": sample_index,
                        "error": "Response did not include integer llm_latency_ms.",
                    })
            except error.HTTPError as exc:
                failures.append({
                    "round": round_number + 1,
                    "sample_index": sample_index,
                    "error": f"HTTP {exc.code}",
                })
            except Exception as exc:
                failures.append({
                    "round": round_number + 1,
                    "sample_index": sample_index,
                    "error": str(exc),
                })

    successful_requests = len(latencies)
    failed_requests = len(failures)
    summary = {
        "provider": args.provider,
        "base_url": args.base_url,
        "rounds": max(args.rounds, 1),
        "sample_count": len(SAMPLE_TEXTS),
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        **summarize_latencies(latencies),
        "failures": failures,
    }
    output_path = save_results(args.provider, summary)

    print(f"provider: {summary['provider']}")
    print(f"total requests: {summary['total_requests']}")
    print(f"successful requests: {summary['successful_requests']}")
    print(f"failed requests: {summary['failed_requests']}")
    print(f"average llm_latency_ms: {summary['average_llm_latency_ms']}")
    print(f"median llm_latency_ms: {summary['median_llm_latency_ms']}")
    print(f"min llm_latency_ms: {summary['min_llm_latency_ms']}")
    print(f"max llm_latency_ms: {summary['max_llm_latency_ms']}")
    if any(failure.get("error") == "HTTP 429" for failure in failures):
        print("Requests were rate-limited. For local benchmarking, raise SUBMIT_RATE_LIMIT or increase delay.")
    print(f"saved results: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
