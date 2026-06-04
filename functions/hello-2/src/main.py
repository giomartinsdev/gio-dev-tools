import json

class MainHandler:
    def handle(req):
        return json.dumps({
            "function": "hello-2-a",
            "input": req.body
        })