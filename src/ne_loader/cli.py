"""Provides basic command line functionality."""

import click
import shutil

from . import map_loader
from .cacher import get_cache_dir


@click.group()
def main() -> None:
    """Entry point for the ne-loader CLI."""


@main.command("download")
@click.argument("category")
@click.argument("name")
@click.option("--res", default="10m", help="NE dataset resolution (default: 10m)")
def cli_get_natural_earth(category: str, name: str, res: map_loader.Resolution) -> None:
    """Download a Natural Earth dataset and load it into GeoPandas."""
    map_loader.get_natural_earth(category, name, res)


@main.command("where")
def cli_where_cache() -> None:
    """Locate the cache directory."""
    cache_dir = get_cache_dir()
    click.echo(cache_dir)


@main.command("list")
def cli_list_cached_files() -> None:
    """List all cached NE files within the cache dir."""
    cache_dir = get_cache_dir()
    sub_folders = [f.name for f in cache_dir.iterdir() if f.is_dir()]
    click.echo(", ".join(sub_folders))


@main.command("rm")
@click.argument("dataset", required=False)
@click.option(
    "--all",
    "all_",
    is_flag=True,
    default=False,
    help="Remove the entire cache directory instead of a single dataset.",
)
def cli_remove_cached_file(dataset: str | None, all_: bool) -> None:
    """Remove a specific cached dataset, or the entire cache when --all is used."""
    cache_dir = get_cache_dir()

    if all_:
        if click.confirm(
            "Are you sure you want to delete all cached Natural Earth datasets?",
            default=False,
        ):
            shutil.rmtree(cache_dir, ignore_errors=True)
            click.echo("Removed all cached datasets.")
        return

    if not dataset:
        raise click.UsageError(
            "Specify a dataset name to remove or use --all toclear the whole cache."
        )

    dataset_dir = cache_dir / dataset
    if not dataset_dir.exists():
        raise click.ClickException(f"Cached dataset not found: {dataset}")

    if click.confirm(
        f"Are you sure you want to delete the cached dataset '{dataset}'?",
        default=False,
    ):
        shutil.rmtree(dataset_dir, ignore_errors=True)
        click.echo(f"Removed cached dataset: {dataset}")
