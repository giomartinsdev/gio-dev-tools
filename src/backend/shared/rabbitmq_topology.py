from __future__ import annotations

import aio_pika

INGESTION_EXCHANGE = "ingestion.events"
DOMAIN_EXCHANGE = "domain.events"
ANALYSIS_EXCHANGE = "analysis.events"

Q_ARCHIVE_RAW = "q.archive.raw"
Q_PERSISTER = "q.persister"
Q_INSIGHT_PROJECTOR = "q.insight.projector"
Q_BUS_POSITIONS = "q.bus.positions"

_QUEUE_BINDINGS = {
    Q_ARCHIVE_RAW: (INGESTION_EXCHANGE, "raw.#"),
    Q_PERSISTER: (DOMAIN_EXCHANGE, "#"),
    Q_INSIGHT_PROJECTOR: (ANALYSIS_EXCHANGE, "analysis.insight_generated"),
    Q_BUS_POSITIONS: (DOMAIN_EXCHANGE, "bus.position_captured"),
}


def _dead_letter_names(queue: str) -> tuple[str, str]:
    return f"dlx.{queue}", f"q.{queue}.dead"


async def declare_topology(channel: aio_pika.abc.AbstractChannel) -> None:
    """Idempotently declare exchanges, queues, bindings and DLXs.

    Both bzzoiro-acl (producer) and domain-persister (consumer) call this on
    startup so the topology can never drift between the two sides.
    """
    exchanges = {
        name: await channel.declare_exchange(name, aio_pika.ExchangeType.TOPIC, durable=True)
        for name in (INGESTION_EXCHANGE, DOMAIN_EXCHANGE, ANALYSIS_EXCHANGE)
    }

    for queue_name, (exchange_name, routing_key) in _QUEUE_BINDINGS.items():
        dlx_name, dead_queue_name = _dead_letter_names(queue_name)
        dlx = await channel.declare_exchange(dlx_name, aio_pika.ExchangeType.FANOUT, durable=True)
        dead_queue = await channel.declare_queue(dead_queue_name, durable=True)
        await dead_queue.bind(dlx)

        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": dlx_name},
        )
        await queue.bind(exchanges[exchange_name], routing_key=routing_key)
