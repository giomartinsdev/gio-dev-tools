import sys

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

try:
    from shared.auto_trace import install
    install(["src"])
except Exception:
    pass
