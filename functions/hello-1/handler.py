import sys
import json

def handle(req):
    try:
        data = json.loads(req) if req else {}
    except json.JSONDecodeError:
        data = {}
    return json.dumps({"function": "hello-1", "input": data})

if __name__ == "__main__":
    req = sys.stdin.read()
    response = handle(req)
    sys.stdout.write(response)