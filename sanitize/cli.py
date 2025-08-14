import click
import logging
from servicelayer.logs import configure_logging
from sanitize.worker import ServiceWorker, OP_SANITIZE

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()


@cli.command()
def worker():
    """Start the queue and process tasks as they come. Blocks while waiting"""
    worker = ServiceWorker(stages=[OP_SANITIZE])
    worker.run()


if __name__ == "__main__":
    cli()

    """
    docker compose logs -f | grep -Ev \"heartbeat|AMQPConnectionWorkflow|GET /api/2/(status|collections)|GoogleHC\""
    
    """