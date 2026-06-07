import sys
import inspect
import functools
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer("auto-tracer")

def _wrap_func(func, span_name):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(StatusCode.ERROR, str(e))
                    raise
        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(span_name) as span:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return wrapper

def _wrap_classmethod(func, span_name):
    original = func.__func__
    if inspect.iscoroutinefunction(original):
        @functools.wraps(original)
        async def async_wrapper(cls, *args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return await original(cls, *args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(StatusCode.ERROR, str(e))
                    raise
        return classmethod(async_wrapper)

    @functools.wraps(original)
    def wrapper(cls, *args, **kwargs):
        with tracer.start_as_current_span(span_name) as span:
            try:
                return original(cls, *args, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return classmethod(wrapper)

def _wrap_staticmethod(func, span_name):
    original = func.__func__
    if inspect.iscoroutinefunction(original):
        @functools.wraps(original)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return await original(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(StatusCode.ERROR, str(e))
                    raise
        return staticmethod(async_wrapper)

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(span_name) as span:
            try:
                return original(*args, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise
    return staticmethod(wrapper)

def _instrument_class(cls, module_name):
    for name, obj in inspect.getmembers(cls):
        if name.startswith("__") and name.endswith("__"):
            continue

        raw = cls.__dict__.get(name)
        if raw is None:
            continue

        span_name = f"{module_name}.{cls.__name__}.{name}"

        if isinstance(raw, classmethod):
            setattr(cls, name, _wrap_classmethod(raw, span_name))
        elif isinstance(raw, staticmethod):
            setattr(cls, name, _wrap_staticmethod(raw, span_name))
        elif inspect.isfunction(raw):
            setattr(cls, name, _wrap_func(raw, span_name))

def _instrument_module(module):
    module_name = module.__name__

    for name, obj in inspect.getmembers(module, predicate=inspect.isfunction):
        if obj.__module__ != module_name:
            continue
        if name.startswith("__"):
            continue
        span_name = f"{module_name}.{name}"
        setattr(module, name, _wrap_func(obj, span_name))

    for name, obj in inspect.getmembers(module, predicate=inspect.isclass):
        if obj.__module__ != module_name:
            continue
        _instrument_class(obj, module_name)

class _AutoTraceImportHook:
    def __init__(self, packages):
        self.packages = tuple(packages)
        self._instrumenting = set()

    def find_module(self, fullname, path=None):
        if fullname in self._instrumenting:
            return None
        if any(fullname == p or fullname.startswith(p + ".") for p in self.packages):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            module = sys.modules[fullname]
            if fullname not in self._instrumenting:
                self._instrumenting.add(fullname)
                _instrument_module(module)
                self._instrumenting.discard(fullname)
            return module

        self._instrumenting.add(fullname)
        try:
            __import__(fullname)
        finally:
            self._instrumenting.discard(fullname)

        module = sys.modules[fullname]
        _instrument_module(module)
        return module

_hook = None

def install(packages: list[str]):
    global _hook
    if _hook is not None:
        return
    _hook = _AutoTraceImportHook(packages)
    sys.meta_path.insert(0, _hook)

def __getattr__(name: str):
    import importlib
    install([name])
    try:
        return importlib.import_module(name)
    except ImportError:
        raise AttributeError(name)
