import json

class MainHandler:
    def handle(req):
        return json.dumps({
            "function": "hello-1",
            "input": req.body
        })