"""
AGENTVIGIL – Replay Debug Dumps into Phoenix UI
================================================
Reads locally saved JSON debug dumps and uploads them to a running Phoenix
server as OTEL traces, so you can view past runs in the Phoenix UI
WITHOUT re-running the test.

Requirements:
  - Phoenix server must be running:  phoenix serve
  - Then run this script:            python tests/replay_to_phoenix.py

Usage:
  python tests/replay_to_phoenix.py                # Upload most recent run
  python tests/replay_to_phoenix.py --all          # Upload ALL saved runs
  python tests/replay_to_phoenix.py --file <name>  # Upload a specific run
"""

import os
import sys
import json
import glob
import time
import argparse
import datetime

# Force UTF-8 on Windows
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Silence OTEL noise
import logging
for lib in ("opentelemetry", "grpc", "urllib3", "httpx"):
    logging.getLogger(lib).setLevel(logging.CRITICAL)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import track
    from rich import box
    from rich.table import Table
except ImportError:
    print("pip install rich")
    sys.exit(1)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode
except ImportError:
    print("pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http")
    sys.exit(1)

console = Console()
DEBUG_DUMPS_DIR = os.path.join(os.path.dirname(__file__), "debug_dumps")
PHOENIX_ENDPOINT = "http://localhost:6006/v1/traces"


def setup_tracer(project_name: str = "agentvigil-replay") -> trace.Tracer:
    """Configure OTEL to send spans to Phoenix."""
    resource = Resource.create({"service.name": project_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("agentvigil.replay"), provider


def ns_from_iso(iso_str: str) -> int:
    """Convert ISO timestamp string to nanoseconds since epoch."""
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return int(dt.timestamp() * 1e9)
    except Exception:
        return int(time.time() * 1e9)


def replay_run(filepath: str, tracer: trace.Tracer):
    """Load one JSON dump and send it to Phoenix as OTEL spans."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_ts = data.get("run_timestamp", "unknown")
    llm_backend = data.get("llm_backend", "unknown")
    total_seeds = data.get("total_seeds", 0)
    mutations = data.get("mutations_performed", 0)
    best = data.get("best_seed", {})
    all_seeds = data.get("all_seeds_ranked", [])

    console.print(f"\n  Replaying: [bold cyan]{os.path.basename(filepath)}[/bold cyan]")
    console.print(f"  Timestamp: {run_ts} | Seeds: {total_seeds} | Mutations: {mutations}")

    # --- ROOT span: one per run -----------------------------------------------
    with tracer.start_as_current_span(
        "agentvigil.fuzzing_run",
        attributes={
            "run.timestamp": run_ts,
            "run.llm_backend": llm_backend,
            "run.total_seeds": total_seeds,
            "run.initial_corpus_size": data.get("initial_corpus_size", 0),
            "run.mutations_performed": mutations,
            "run.best_score": best.get("score", 0.0) or 0.0,
            "run.best_seed_id": best.get("id", ""),
            "run.source_file": os.path.basename(filepath),
        },
    ) as root_span:

        # --- CHILD span: best seed summary ------------------------------------
        if best.get("text"):
            with tracer.start_as_current_span(
                "agentvigil.best_seed",
                attributes={
                    "seed.id": best.get("id", ""),
                    "seed.score": best.get("score", 0.0) or 0.0,
                    "seed.prompt_text": best.get("text", "")[:2000],
                    "seed.label": "BEST",
                },
            ):
                pass

        # --- CHILD span: one per evaluated seed (prompt) ----------------------
        for seed in track(all_seeds, description=f"  Sending {len(all_seeds)} seeds..."):
            score = seed.get("score", 0.0) or 0.0
            label = "SUCCESS" if score >= 1.0 else ("PARTIAL" if score > 0 else "FAIL")

            with tracer.start_as_current_span(
                f"agentvigil.seed_eval",
                attributes={
                    "seed.rank": seed.get("rank", 0),
                    "seed.score": score,
                    "seed.label": label,
                    "seed.mutation_path": seed.get("mutation_path", ""),
                    "seed.prompt_preview": seed.get("prompt_full", "")[:500],
                    "seed.prompt_full": seed.get("prompt_full", "")[:2000],
                    "llm.input.value": seed.get("prompt_full", "")[:2000],
                    "llm.output.value": f"Injection result: {label} (score={score:.2f})",
                },
            ) as span:
                if score >= 1.0:
                    span.set_status(StatusCode.OK)
                elif score == 0.0:
                    span.set_status(StatusCode.ERROR)

        root_span.set_status(StatusCode.OK)

    console.print(f"  [bold green]Done![/bold green] {len(all_seeds)} spans sent to Phoenix.")


def list_dumps():
    return sorted(glob.glob(os.path.join(DEBUG_DUMPS_DIR, "run_*.json")), reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Replay AgentVigil debug dumps into Phoenix UI.")
    parser.add_argument("--all", action="store_true", help="Upload all saved runs")
    parser.add_argument("--file", type=str, help="Upload a specific run file")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]AgentVigil – Replay Logs into Phoenix[/bold cyan]\n"
        "Make sure [bold]phoenix serve[/bold] is running first!\n"
        "Then open: [link=http://localhost:6006]http://localhost:6006[/link]",
        title="Phoenix Log Uploader"
    ))

    os.makedirs(DEBUG_DUMPS_DIR, exist_ok=True)
    dumps = list_dumps()

    if not dumps:
        console.print("[red]No debug dumps found in:[/red]", DEBUG_DUMPS_DIR)
        console.print("Run [bold]python tests/test_agentvigil.py[/bold] first to generate logs.")
        return

    # Choose which files to replay
    if args.file:
        target = args.file if os.path.exists(args.file) else os.path.join(DEBUG_DUMPS_DIR, args.file)
        files_to_replay = [target]
    elif args.all:
        files_to_replay = dumps
        console.print(f"\nFound [bold]{len(files_to_replay)}[/bold] run(s) to upload.")
    else:
        files_to_replay = [dumps[0]]  # Most recent
        console.print(f"\nUploading most recent run: [bold]{os.path.basename(dumps[0])}[/bold]")
        console.print("[dim]Use --all to upload all runs, --file <name> for a specific one.[/dim]")

    # Setup OTEL tracer pointing at Phoenix
    tracer, provider = setup_tracer()

    for fpath in files_to_replay:
        try:
            replay_run(fpath, tracer)
        except FileNotFoundError:
            console.print(f"[red]File not found:[/red] {fpath}")
        except Exception as e:
            console.print(f"[red]Error replaying {fpath}:[/red] {e}")

    # Flush all buffered spans before exit
    console.print("\n[dim]Flushing spans to Phoenix...[/dim]")
    provider.force_flush(timeout_millis=10_000)
    provider.shutdown()

    console.print(Panel.fit(
        "[bold green]Upload complete![/bold green]\n"
        "Open Phoenix UI: [link=http://localhost:6006]http://localhost:6006[/link]\n"
        "Go to [bold]Tracing -> Traces[/bold] to see your runs.",
        title="Done"
    ))


if __name__ == "__main__":
    main()
