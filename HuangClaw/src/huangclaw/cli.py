from __future__ import annotations

import argparse

from huangclaw.agent import HuangClawAgent
from huangclaw.skills import PdfSkill


def main() -> None:
    parser = argparse.ArgumentParser(prog="huangclaw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Chunk PDFs and store vectors in Chroma.")
    ingest_parser.add_argument("--docs-dir", default=None, help="PDF directory. Default: ../docs")
    ingest_parser.add_argument("--reset", action="store_true", help="Delete and rebuild the collection.")
    ingest_parser.add_argument("--chunk-size", type=int, default=1200)
    ingest_parser.add_argument("--chunk-overlap", type=int, default=180)
    ingest_parser.add_argument("--batch-size", type=int, default=64)

    ask_parser = subparsers.add_parser("ask", help="Ask HuangClaw a question.")
    ask_parser.add_argument("question", nargs="+")

    slack_parser = subparsers.add_parser("slack", help="Run the Slack FastAPI service.")
    slack_parser.add_argument("--host", default="0.0.0.0")
    slack_parser.add_argument("--port", type=int, default=3010)

    args = parser.parse_args()

    if args.command == "ingest":
        stats = PdfSkill().ingest(
            docs_dir=args.docs_dir,
            reset=args.reset,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            batch_size=args.batch_size,
        )
        print(
            "Ingest complete: "
            f"pdfs={stats.pdf_count}, pages={stats.page_count}, chunks={stats.chunk_count}, "
            f"collection={stats.collection_name}, chroma={stats.chroma_dir}"
        )
        return

    if args.command == "ask":
        question = " ".join(args.question)
        print(HuangClawAgent().ask(question))
        return

    if args.command == "slack":
        import uvicorn

        uvicorn.run("huangclaw.slack_app:api", host=args.host, port=args.port)
        return
