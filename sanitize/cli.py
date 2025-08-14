import click
import logging
from servicelayer.logs import configure_logging
from sanitize.worker import ServiceWorker, OP_SANITIZE

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()


@cli.command()
@click.option("--dataset", required=True, help="Name of the dataset")
def worker():
    log.debug(f">>>>>>>>>>>>   Starting worker for dataset")
    """Start the queue and process tasks as they come. Blocks while waiting"""
    worker = ServiceWorker(stages=[OP_SANITIZE])
    worker.run()


if __name__ == "__main__":
    cli()
