import sys
from shared.request import Request
from src.main import main


def handle(raw_body: str) -> str:
    return main(
        Request(raw_body),
    ).send()


if __name__ == "__main__":
    raw_body = sys.stdin.read()
    sys.stdout.write(handle(raw_body))
