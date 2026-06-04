import random
import pandas as pd
from shared.request import Request
from shared.response import Response
from shared.logger import get_logger

logger = get_logger(__name__)

def main(request: Request) -> Response:
    match request.body:
        case {"404": "404"}:
            response = Response(
                body={
                    "message": "404 Not Found",
                },
                status_code=404,
            )
        case {"500": "500"}:
            response = Response(
                body={
                    "message": "500 Internal Server Error",
                },
                status_code=500,
            )
        case _:  
            response = Response(
                body={
                    "message": "Hello from Python on OpenFaaS",
                    "version": "1.0.26",
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

    logger.info(response.to_dict())
    return response
