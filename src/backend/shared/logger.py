import logging
import sys

from opentelemetry import trace


class _TraceFilter(logging.Filter):
    def filter(self, record):
        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = '-'
            record.span_id = '-'
        return True


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s trace=%(trace_id)s span=%(span_id)s %(name)s %(message)s'
))
_handler.addFilter(_TraceFilter())

logging.root.setLevel(logging.INFO)
logging.root.handlers = [_handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
