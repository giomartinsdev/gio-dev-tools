import random
import pandas as pd

def generate_mock_df():
    return pd.DataFrame({
        "col1": [1, 2, 3, 4, 5],
        "col2": [6, 7, 8, 9, 10],
        "col3": [11, 12, 13, 14, 15]
    })

def main(event, context):
    headers = {
        "Content-Type": "application/json"
    }
    return {
        "statusCode": 200,
        "body": {
            "message": "Hello from Python on OpenFaaS",
            "version": "1.0.19",
            "random_int": random.randint(1, 100),
            "df_head": generate_mock_df().head().to_dict()
        },
        "headers": headers
    }