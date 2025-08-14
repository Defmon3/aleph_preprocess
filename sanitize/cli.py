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
@click.option("--dataset", required=False, help="Name of the dataset")
def worker(dataset):
    log.debug(f">>>>>>>>>>>>   Starting worker for dataset {dataset}   <<<<<<<<<<<<")
    log.debug(f">>> >>>>>>>>>>   Using dataset  <<<<<<<<<<<<")
    """Start the queue and process tasks as they come. Blocks while waiting"""
    # worker = ServiceWorker(stages=[OP_SANITIZE])
    get_worker()
    # worker.run()


@cli.command()
@click.option("--dataset", required=True, help="Name of the dataset")
def sanitize(dataset):
    run_sanitize(dataset)


if __name__ == "__main__":
    cli()
