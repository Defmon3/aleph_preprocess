import click
import logging
from servicelayer.logs import configure_logging
from ftmstore import get_dataset
from worker import get_worker, OP_SANITIZE

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()


@cli.command()
def worker():
    """Start the RabbitMQ-backed sanitize worker loop."""
    log.info(f"Starting sanitize worker (queue: {OP_SANITIZE})..." )
    w = get_worker()
    w.run()


if __name__ == "__main__":
    cli()
