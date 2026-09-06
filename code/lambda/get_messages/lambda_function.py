import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        # API Gateway's Cognito authorizer already validated the token
        # before this function ever runs — an invalid/missing token
        # never reaches this code.
        result = table.scan()
        items = result.get("Items", [])
        items.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)

        return _response(200, {
            "count": len(items),
            "messages": items,
        })

    except Exception as e:
        print(f"ERROR: {e}")
        return _response(500, {"error": "Something went wrong. Please try again later."})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
