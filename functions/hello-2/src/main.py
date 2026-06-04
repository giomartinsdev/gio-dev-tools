def main(event, context):
    headers = {
        "Content-Type": "application/json"
    }
    return {
        "statusCode": 200,
        "body": {
            "message": "Hello from Python on OpenFaaS",
            "version": "1.0.17"
        },
        "headers": headers
    }