from __future__ import annotations

import importlib

from .types import Answer, AnswerTrace, PageDocument

RICH_INSTALL_MESSAGE = "Rich output requested, but `rich` is not installed. Install with `pip install -e .[ui]`."


def rich_available() -> bool:
    try:
        importlib.import_module("rich.console")
        importlib.import_module("rich.panel")
        importlib.import_module("rich.table")
        importlib.import_module("rich.text")
        importlib.import_module("rich.json")
        return True
    except ImportError:
        return False


def should_use_rich(
    *,
    explicit_rich: bool,
    plain: bool,
    stdout_is_tty: bool,
    rich_installed: bool,
    json_mode: bool,
) -> bool:
    if plain:
        return False
    if explicit_rich:
        return rich_installed
    if json_mode:
        return False
    return stdout_is_tty and rich_installed


def _load_rich() -> dict[str, object]:
    try:
        return {
            "Console": importlib.import_module("rich.console").Console,
            "Group": importlib.import_module("rich.console").Group,
            "Panel": importlib.import_module("rich.panel").Panel,
            "Table": importlib.import_module("rich.table").Table,
            "Text": importlib.import_module("rich.text").Text,
            "JSON": importlib.import_module("rich.json").JSON,
            "box": importlib.import_module("rich.box"),
        }
    except ImportError as exc:
        raise RuntimeError(RICH_INSTALL_MESSAGE) from exc


def _verdict_style(verdict: str) -> str:
    return {
        "supported": "green",
        "mixed": "yellow",
        "insufficient": "red",
    }.get(verdict, "cyan")


def _trace_table(modules: dict[str, object], trace: AnswerTrace | None):
    Table = modules["Table"]
    box = modules["box"]
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True, show_header=True)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="white")

    query_count = len(trace.queries) if trace is not None else 0
    pages_fetched = trace.pages_fetched if trace is not None else 0
    pages_extracted = trace.pages_extracted if trace is not None else 0
    failures = len(trace.failures) if trace is not None else 0

    table.add_row("Queries", str(query_count))
    table.add_row("Pages fetched", str(pages_fetched))
    table.add_row("Pages extracted", str(pages_extracted))
    table.add_row("Failures", str(failures))
    if trace is not None and trace.failures:
        table.add_row("Last failure", trace.failures[0].get("error", "-"))
    return table


def print_json_rich(payload: dict) -> None:
    modules = _load_rich()
    Console = modules["Console"]
    JSON = modules["JSON"]
    console = Console()
    console.print(JSON.from_data(payload, indent=2))


def print_answer_rich(answer: Answer) -> None:
    modules = _load_rich()
    Console = modules["Console"]
    Group = modules["Group"]
    Panel = modules["Panel"]
    Table = modules["Table"]
    Text = modules["Text"]
    box = modules["box"]

    console = Console()
    summary_group = Group(
        Text(answer.question, style="bold white"),
        Text(f"Strategy: {answer.strategy.replace('_', ' ').title()}", style="cyan"),
        Text(answer.answer, style="white"),
    )
    console.print(Panel(summary_group, title="Search Result", border_style="blue"))

    sources = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True, show_header=True)
    sources.add_column("#", style="bold cyan", width=3)
    sources.add_column("Source", style="bold white")
    sources.add_column("Score", justify="right", style="green", width=7)
    sources.add_column("Published", style="magenta", width=14)
    sources.add_column("Quote", style="white")

    for rank, item in enumerate(answer.evidence[:5], start=1):
        sources.add_row(
            str(rank),
            item.title,
            f"{item.score:.2f}",
            item.published_at or "-",
            item.quote,
        )
    if not answer.evidence:
        sources.add_row("-", "No evidence found", "-", "-", "-")

    console.print(Panel(sources, title="Top Sources", border_style="green"))
    console.print(Panel(_trace_table(modules, answer.trace), title="Trace", border_style="yellow"))


def print_page_document_rich(doc: PageDocument, *, max_chars: int | None = 4000) -> None:
    modules = _load_rich()
    Console = modules["Console"]
    Group = modules["Group"]
    Panel = modules["Panel"]
    Table = modules["Table"]
    Text = modules["Text"]
    box = modules["box"]

    console = Console()
    text = doc.text.strip()
    truncated = False
    if max_chars is not None and max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
        truncated = True

    metadata = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True, show_header=False)
    metadata.add_column("Key", style="bold cyan", width=14)
    metadata.add_column("Value", style="white")
    metadata.add_row("Title", doc.title or "(untitled)")
    metadata.add_row("URL", doc.url)
    metadata.add_row("Extraction", doc.extraction_method)
    metadata.add_row("Fetched", doc.fetched_at)
    metadata.add_row("Words", str(len(doc.text.split())))
    metadata.add_row("Characters", str(len(doc.text)))
    if doc.published_at:
        metadata.add_row("Published", doc.published_at)
    if doc.metadata.get("structured_sources"):
        metadata.add_row("Structured", ", ".join(doc.metadata["structured_sources"]))
    if doc.metadata.get("dynamic_signals"):
        metadata.add_row("Signals", ", ".join(doc.metadata["dynamic_signals"]))
    if doc.metadata.get("recovery_failed"):
        metadata.add_row("Recovery", "Likely dynamic or unsupported")
    if truncated:
        metadata.add_row("Truncated", f"Yes ({max_chars} chars)")

    console.print(Panel(metadata, title="Page", border_style="blue"))
    console.print(
        Panel(
            Group(Text(text or "No text extracted.", style="white")),
            title="Text",
            border_style="green",
        )
    )


def print_price_result_rich(
    *,
    question: str,
    result,
    trace: AnswerTrace | None = None,
    min_sources: int = 3,
) -> None:
    modules = _load_rich()
    Console = modules["Console"]
    Group = modules["Group"]
    Panel = modules["Panel"]
    Table = modules["Table"]
    Text = modules["Text"]
    box = modules["box"]

    console = Console()
    verdict_style = _verdict_style(result.verdict)
    header = Group(
        Text(question, style="bold white"),
        Text(f"Verdict: {result.verdict}", style=f"bold {verdict_style}"),
        Text(f"Confidence: {result.confidence:.2f}", style="cyan"),
        Text(result.summary, style="white"),
        Text(f"Rule: at least {min_sources} independent source(s)", style="dim"),
    )
    console.print(Panel(header, title="Price Consensus", border_style=verdict_style))

    agreeing = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True, show_header=True)
    agreeing.add_column("#", style="bold cyan", width=3)
    agreeing.add_column("Source", style="bold white")
    agreeing.add_column("Price", style="green", width=14)
    agreeing.add_column("Domain", style="magenta")
    agreeing.add_column("Snippet", style="white")
    for rank, item in enumerate(result.agreeing, start=1):
        agreeing.add_row(
            str(rank),
            item.source_title,
            f"{item.currency} {item.amount:,.2f}",
            item.domain,
            item.snippet,
        )
    if not result.agreeing:
        agreeing.add_row("-", "No agreeing sources", "-", "-", "-")
    console.print(Panel(agreeing, title="Agreeing Sources", border_style="green"))

    if result.conflicting:
        conflicting = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True, show_header=True)
        conflicting.add_column("#", style="bold cyan", width=3)
        conflicting.add_column("Source", style="bold white")
        conflicting.add_column("Price", style="yellow", width=14)
        conflicting.add_column("Domain", style="magenta")
        conflicting.add_column("Snippet", style="white")
        for rank, item in enumerate(result.conflicting, start=1):
            conflicting.add_row(
                str(rank),
                item.source_title,
                f"{item.currency} {item.amount:,.2f}",
                item.domain,
                item.snippet,
            )
        console.print(Panel(conflicting, title="Conflicting Sources", border_style="yellow"))

    console.print(Panel(_trace_table(modules, trace), title="Trace", border_style="cyan"))
