"""
WebReach Pipeline — CLI entry point.
Orchestrates all agents for automated website outreach.
"""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from config.settings import settings
from database.connection import init_db, get_session
from database.models import Lead, LeadStatus
from orchestrator.pipeline import Pipeline
from agents.scanner import ScannerAgent
from agents.verifier import VerifierAgent
from agents.builder import BuilderAgent
from agents.deployer import DeployerAgent
from agents.outreach import OutreachAgent
from agents.followup import FollowUpAgent
from utils.logging_setup import setup_logging

console = Console()
logger = logging.getLogger(__name__)


def create_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.register_agent("scanner", ScannerAgent())
    pipeline.register_agent("verifier", VerifierAgent())
    pipeline.register_agent("builder", BuilderAgent())
    pipeline.register_agent("deployer", DeployerAgent())
    pipeline.register_agent("outreach", OutreachAgent())
    pipeline.register_agent("followup", FollowUpAgent())
    return pipeline


@click.group()
def cli():
    """WebReach — Automated Website Outreach Pipeline"""
    setup_logging()
    init_db()


@cli.command()
@click.argument("location")
@click.option("--query", "-q", default="", help="Additional search keyword")
@click.option("--radius", "-r", default=5000, help="Search radius in meters")
def scan(location: str, query: str, radius: int):
    """Scan a location for businesses without websites."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_scan(location, query, radius)
        console.print(
            f"\n[bold green]Scan complete:[/] "
            f"{run.leads_succeeded} leads found "
            f"(processed {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
@click.option("--batch-size", "-b", default=10, help="Number of leads to verify")
def verify(batch_size: int):
    """Verify discovered leads (website check + contact info)."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_verification(batch_size)
        console.print(
            f"\n[bold green]Verification complete:[/] "
            f"{run.leads_succeeded} verified, "
            f"{run.leads_failed} rejected "
            f"(of {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
@click.option("--batch-size", "-b", default=10, help="Number of websites to build")
def build(batch_size: int):
    """Build websites for verified leads."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_build(batch_size)
        console.print(
            f"\n[bold green]Build complete:[/] "
            f"{run.leads_succeeded} websites built "
            f"(of {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
@click.option("--batch-size", "-b", default=5, help="Number of sites to deploy")
def deploy(batch_size: int):
    """Deploy built websites to Railway."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_deploy(batch_size)
        console.print(
            f"\n[bold green]Deploy complete:[/] "
            f"{run.leads_succeeded} deployed "
            f"(of {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
@click.option("--batch-size", "-b", default=10, help="Number of emails to send")
def outreach(batch_size: int):
    """Send outreach emails to deployed leads."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_outreach(batch_size)
        console.print(
            f"\n[bold green]Outreach complete:[/] "
            f"{run.leads_succeeded} sent "
            f"(of {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
def followup():
    """Process follow-ups for sent outreach."""
    pipeline = create_pipeline()

    async def _run():
        run = await pipeline.run_followup()
        console.print(
            f"\n[bold green]Follow-up complete:[/] "
            f"{run.leads_succeeded} sent "
            f"(of {run.leads_processed})"
        )

    asyncio.run(_run())


@cli.command()
@click.argument("location")
@click.option("--query", "-q", default="", help="Additional search keyword")
@click.option("--radius", "-r", default=5000, help="Search radius in meters")
def run_all(location: str, query: str, radius: int):
    """Run the full pipeline: scan → verify → build → deploy → outreach."""
    pipeline = create_pipeline()

    async def _run():
        console.print("[bold]Starting full pipeline...[/]\n")
        results = await pipeline.run_full_pipeline(location, query, radius)

        table = Table(title="Pipeline Results")
        table.add_column("Stage", style="bold")
        table.add_column("Processed", justify="right")
        table.add_column("Succeeded", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Status")

        for stage, run in results.items():
            table.add_row(
                stage,
                str(run.leads_processed),
                str(run.leads_succeeded),
                str(run.leads_failed),
                run.status,
            )

        console.print(table)

    asyncio.run(_run())


@cli.command()
def status():
    """Show current pipeline status and lead counts."""
    session = get_session()
    try:
        table = Table(title="Lead Status Overview")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")

        total = 0
        for s in LeadStatus:
            count = session.query(Lead).filter(Lead.status == s).count()
            if count > 0:
                table.add_row(s.value, str(count))
                total += count

        table.add_row("─" * 20, "─" * 5)
        table.add_row("TOTAL", str(total), style="bold")
        console.print(table)
    finally:
        session.close()


@cli.command()
@click.option("--port", "-p", default=8000, help="Dashboard port")
def dashboard(port: int):
    """Start the web dashboard."""
    import uvicorn
    console.print(f"[bold]Starting dashboard on http://localhost:{port}[/]")
    uvicorn.run("dashboard.app:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    cli()
