import sys
from .src.main import MainHandler

def handle(req):
    return MainHandler().handle(req)

if __name__ == "__main__":
    req = sys.stdin.read()
    response = handle(req)
    sys.stdout.write(response)