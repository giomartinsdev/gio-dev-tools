import json
from .src.main import main

def handle(req):
    return main(req, None)

if __name__ == "__main__":
    import sys
    req = sys.stdin.read()
    response = json.dumps(handle(req))
    sys.stdout.write(response)