import json

class MainHandler:
    def handle(req):
        return json.dumps({
            "function": "hello-2",
            "input": req.body,
            "version": "1.0.3"
        })