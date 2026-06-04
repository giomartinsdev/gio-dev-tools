import random
import pandas as pd
from shared.request import Request
from shared.response import Response
from shared.logger import get_logger

logger = get_logger(__name__)

def handle_404():
    response = Response(
        body={
            "message": "404 Not Found",
        },
        status_code=404,
    )
    logger.info(response)
    return response

def handle_500():
    raise ValueError("500 Internal Server Error")

def handle_200(request: Request):
    return Response(
        body={
            "message": "Hello from Python on OpenFaaS",
            "version": "1.0.40",
            "random_int": random.randint(1, 100),
            "df_head": pd.DataFrame({
                "col1": [1, 2, 3, 4, 5],
                "col2": [6, 7, 8, 9, 10],
                "col3": [11, 12, 13, 14, 15]
            }).to_dict(orient="records"),
            "request": request.to_dict(),
        },
        status_code=200,
    )

def main(request: Request) -> Response:

    if request.body == {"404": "404"}:
        return handle_404()

    if request.body == {"500": "500"}:
        return handle_500()

    return handle_200(request)
