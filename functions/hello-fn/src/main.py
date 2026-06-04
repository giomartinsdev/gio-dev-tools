import random
import pandas as pd
from shared.request import Request
from shared.response import Response


def main(request: Request) -> Response:
    return Response(
        body={
            "message": "Hello from Python on OpenFaaS",
            "version": "1.0.22",
            "random_int": random.randint(1, 100),
            "df_head": pd.DataFrame({
                "col1": [1, 2, 3, 4, 5],
                "col2": [6, 7, 8, 9, 10],
                "col3": [11, 12, 13, 14, 15]
            }).to_dict(orient="records"),
            "request": request,
        },
        status_code=200,
    )
