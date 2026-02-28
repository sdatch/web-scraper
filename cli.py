import os
import sys

import click
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from web_scraper.utils.config_loader import list_sites, load_merged_config


@click.group()
def cli():
    """Web Content Scraper — config-driven web scraping tool."""
    pass


@cli.command()
@click.option("--site", required=True, help="Site config name (e.g., itl)")
@click.option("--dry-run", is_flag=True, help="List discovered URLs without fetching articles")
def scrape(site, dry_run):
    """Run the scraper for a given site."""
    # Verify site config exists
    available = list_sites()
    if site not in available:
        click.echo(f"Error: Site '{site}' not found. Available: {', '.join(available)}")
        sys.exit(1)

    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "web_scraper.settings")
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(site, site=site, dry_run=str(dry_run))
    process.start()


@cli.command("list-sites")
def list_sites_cmd():
    """Show available site configurations."""
    sites = list_sites()
    if not sites:
        click.echo("No site configs found.")
        return
    click.echo("Available sites:")
    for s in sites:
        click.echo(f"  - {s}")


@cli.command("validate-config")
@click.option("--site", required=True, help="Site config name to validate")
def validate_config(site):
    """Validate a site configuration file."""
    try:
        config = load_merged_config(site)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

    errors = []

    if not config.get("brand"):
        errors.append("Missing 'brand'")
    if not config.get("base_url"):
        errors.append("Missing 'base_url'")
    if not config.get("entry_points"):
        errors.append("Missing or empty 'entry_points'")
    else:
        for i, ep in enumerate(config["entry_points"]):
            if not ep.get("url"):
                errors.append(f"Entry point {i}: missing 'url'")

    extraction = config.get("extraction", {})
    if not extraction.get("jsonld", {}).get("field_map") and not extraction.get("dom_fallback", {}).get("selectors"):
        errors.append("No extraction config (need jsonld.field_map or dom_fallback.selectors)")

    if errors:
        click.echo(f"Config '{site}' has errors:")
        for e in errors:
            click.echo(f"  - {e}")
        sys.exit(1)
    else:
        click.echo(f"Config '{site}' is valid.")


if __name__ == "__main__":
    cli()
