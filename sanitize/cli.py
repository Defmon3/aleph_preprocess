import logging

import click
from ftmstore import get_dataset
from servicelayer.logs import configure_logging

from sanitize.worker import run_sanitize

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()





@cli.command()
@click.option("--dataset", required=True, help="Name of the dataset")
def worker(dataset):
    run_sanitize(dataset)


if __name__ == "__main__":
    cli()
