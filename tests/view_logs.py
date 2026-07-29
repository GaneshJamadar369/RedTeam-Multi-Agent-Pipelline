"""
AGENTVIGIL Debug Log Viewer
============================
View saved debug dump logs from previous test runs WITHOUT re-running tests.

Usage:
  python tests/view_logs.py                  # View the most recent run
  python tests/view_logs.py --all            # List all saved runs
  python tests/view_logs.py --file <name>    # View a specific run file
"""

import os
import sys
import json
import argparse
import glob
from datetime import datetime

# Force UTF-8 on Windows
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.rule import Rule
except ImportError:
    print("Please install rich: pip install rich")
    sys.exit(1)

console = Console()
DEBUG_DUMPS_DIR = os.path.join(os.path.dirname(__file__), "debug_dumps")


def list_all_runs():
    """List all saved debug dump files."""
    files = sorted(glob.glob(os.path.join(DEBUG_DUMPS_DIR, "run_*.json")), reverse=True)
    if not files:
        console.print("[red]No debug dumps found in:[/red]", DEBUG_DUMPS_DIR)
        console.print("Run [bold]python tests/test_agentvigil.py[/bold] first to generate logs.")
        return []

    console.print(Panel.fit(
        f"[bold cyan]Found {len(files)} saved run(s)[/bold cyan]",
        title="AgentVigil Debug Logs"
    ))

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("File", style="bold")
    table.add_column("Timestamp")
    table.add_column("LLM Backend")
    table.add_column("Seeds", justify="right")
    table.add_column("Mutations", justify="right")
    table.add_column("Best Score", justify="right")

    for i, fpath in enumerate(files):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("run_timestamp", "?")
            backend = data.get("llm_backend", "?")
            seeds = str(data.get("total_seeds", "?"))
            mutations = str(data.get("mutations_performed", "?"))
            best = data.get("best_seed", {})
            best_score = f"{best.get('score', 0):.2f}" if best.get("score") is not None else "N/A"
            table.add_row(str(i + 1), fname, ts[:19], backend[:30], seeds, mutations, best_score)
        except Exception as e:
            table.add_row(str(i + 1), fname, "?", f"[red]Error: {e}[/red]", "?", "?", "?")

    console.print(table)
    console.print(f"\n[dim]To view a specific run:[/dim] python tests/view_logs.py --file <filename>")
    return files


def display_run(filepath: str):
    """Display a single run in full detail."""
    if not os.path.exists(filepath):
        # Try treating it as just a filename inside debug_dumps
        alt = os.path.join(DEBUG_DUMPS_DIR, filepath)
        if os.path.exists(alt):
            filepath = alt
        else:
            console.print(f"[red]File not found:[/red] {filepath}")
            sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    console.print()
    console.print(Panel.fit(
        "[bold green]AgentVigil – Saved Run Report[/bold green]",
        subtitle=os.path.basename(filepath),
        title="Debug Log Viewer"
    ))

    # ── Run metadata ──────────────────────────────────────────────────────────
    console.print(Rule("[bold]Run Metadata[/bold]"))
    console.print(f"  [bold]Timestamp  :[/bold] {data.get('run_timestamp', 'N/A')}")
    console.print(f"  [bold]LLM Backend:[/bold] {data.get('llm_backend', 'N/A')}")
    phoenix_status = "[green]Yes[/green]" if data.get("phoenix_active") else "[yellow]No (Phoenix was not running)[/yellow]"
    console.print(f"  [bold]Phoenix UI :[/bold] {phoenix_status}")

    # ── Prompt generation metrics ─────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Prompt Generation Metrics[/bold]"))
    console.print(f"  [bold]Total prompts evaluated:[/bold] {data.get('total_seeds', 0)}")
    console.print(f"  [bold]Initial corpus size    :[/bold] {data.get('initial_corpus_size', 0)}")
    console.print(f"  [bold]Mutations performed    :[/bold] {data.get('mutations_performed', 0)}")

    # ── All prompt scores ─────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]All Prompt Scores (Ranked)[/bold]"))

    all_seeds = data.get("all_seeds_ranked", [])
    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    table.add_column("Rank", width=5, style="dim")
    table.add_column("Score", width=7)
    table.add_column("Mutation Path", width=30)
    table.add_column("Prompt Preview (first 80 chars)")

    for seed in all_seeds:
        score = seed.get("score", 0)
        score_color = "green" if score >= 1.0 else ("yellow" if score > 0 else "red")
        preview = seed.get("prompt_full", "")[:80].replace("\n", " ")
        if len(seed.get("prompt_full", "")) > 80:
            preview += "..."
        table.add_row(
            f"#{seed['rank']}",
            f"[{score_color}]{score:.2f}[/{score_color}]",
            seed.get("mutation_path", "?"),
            preview,
        )

    console.print(table)

    # ── Best prompt ───────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Best Performing Prompt[/bold]"))
    best = data.get("best_seed", {})
    if best and best.get("score") is not None:
        console.print(f"  [bold]ID    :[/bold] {best.get('id', 'N/A')}")
        console.print(f"  [bold]Score :[/bold] [bold green]{best.get('score', 0):.2f}[/bold green]")
        console.print(f"\n  [bold]Full Prompt Text:[/bold]")
        console.print(Panel(
            best.get("text", ""),
            border_style="green",
            padding=(1, 2)
        ))
    else:
        console.print("  [red]No successful seeds found in this run.[/red]")

    console.print()


def get_latest_run():
    """Return the path to the most recently saved debug dump."""
    files = sorted(glob.glob(os.path.join(DEBUG_DUMPS_DIR, "run_*.json")), reverse=True)
    return files[0] if files else None


def main():
    parser = argparse.ArgumentParser(
        description="View AgentVigil debug dump logs without re-running tests."
    )
    parser.add_argument("--all", action="store_true", help="List all saved runs")
    parser.add_argument("--file", type=str, help="View a specific run file (name or full path)")
    args = parser.parse_args()

    os.makedirs(DEBUG_DUMPS_DIR, exist_ok=True)

    if args.all:
        list_all_runs()
    elif args.file:
        display_run(args.file)
    else:
        # Default: show the most recent run
        latest = get_latest_run()
        if latest:
            console.print(f"[dim]Showing most recent run. Use --all to list all runs.[/dim]")
            display_run(latest)
        else:
            console.print("[red]No debug dumps found.[/red]")
            console.print(f"Run [bold]python tests/test_agentvigil.py[/bold] first.")
            console.print(f"Logs are saved to: [bold]{DEBUG_DUMPS_DIR}[/bold]")


if __name__ == "__main__":
    main()
