import logging
import sys


try:
    from opentelemetry import trace as _otel_trace
    def _get_trace_ids() -> tuple[str, str]:
        ctx = _otel_trace.get_current_span().get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, '032x'), format(ctx.span_id, '016x')
        return '-', '-'
except ImportError:
    def _get_trace_ids() -> tuple[str, str]:
        return '-', '-'


class _TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id, record.span_id = _get_trace_ids()
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
