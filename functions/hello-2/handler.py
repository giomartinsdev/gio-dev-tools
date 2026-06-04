import sys
import json

def handle(req):
    return json.dumps({
        "function": "hello-2",
        "input": req,
        "version": "1.0.10"
    })

if __name__ == "__main__":
    req = sys.stdin.read()
    response = handle(req)
    sys.stdout.write(response)