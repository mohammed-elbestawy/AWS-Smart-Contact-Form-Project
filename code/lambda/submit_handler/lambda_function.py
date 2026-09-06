import json
import os
import re
import uuid
import boto3
from datetime import datetime

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_MESSAGE_LENGTH = 2000
MAX_SHORT_FIELD_LENGTH = 200


def lambda_handler(event, context):
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        required_fields = ["name", "email", "subject", "message"]
        missing = [f for f in required_fields if not str(body.get(f, "")).strip()]
        if missing:
            return _response(400, {"error": "Missing fields: " + ", ".join(missing)})

        name    = body["name"].strip()[:MAX_SHORT_FIELD_LENGTH]
        email   = body["email"].strip()[:MAX_SHORT_FIELD_LENGTH]
        subject = body["subject"].strip()[:MAX_SHORT_FIELD_LENGTH]
        message = body["message"].strip()[:MAX_MESSAGE_LENGTH]

        if not EMAIL_RE.match(email):
            return _response(400, {"error": "Invalid email format"})

        message_id = str(uuid.uuid4())

        # Push to SQS instead of processing here — the user gets an
        # immediate response while sentiment analysis and storage
        # happen asynchronously in message-processor.
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                "message_id": message_id,
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
                "submitted_at": datetime.utcnow().isoformat(),
            }),
        )

        return _response(200, {
            "message_id": message_id,
            "message": "Your message has been received and is being processed.",
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
