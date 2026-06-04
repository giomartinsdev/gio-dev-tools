import json

def handle(event, context):
    return json.dumps(
        {
            "function": "test-hello-2",
            "input": json.loads(event.body) if event.body else {}
        }
    )