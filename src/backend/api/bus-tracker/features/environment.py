import os
import sys

_backend_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from shared.behave_setup import configure_function_paths

configure_function_paths(__file__)

from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from shared.transaction_manager import TransactionConfig, TransactionManager
from src.infrastructure.models import Base


def before_all(context):
    context.postgres = PostgresContainer("postgres:16-alpine")
    context.postgres.start()
    TransactionManager.configure(TransactionConfig(url=context.postgres.get_connection_url()))
    Base.metadata.create_all(TransactionManager.get().engine)


def after_all(context):
    if getattr(context, "postgres", None) is None:
        return
    TransactionManager.reset()
    context.postgres.stop()


def after_scenario(context, scenario):
    with TransactionManager.get().session() as s:
        s.execute(text("TRUNCATE TABLE tracked_lines, bus_positions RESTART IDENTITY CASCADE"))
