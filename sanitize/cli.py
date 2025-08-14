import logging

import click
from servicelayer.logs import configure_logging

from sanitize.worker import run_sanitize

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()





@cli.command()
@click.option("--dataset", required=False, help="Name of the dataset")
def worker(dataset):
    log.debug(f"Starting sanitize worker for dataset: {dataset}")
    run_sanitize(dataset)


if __name__ == "__main__":
    cli()
