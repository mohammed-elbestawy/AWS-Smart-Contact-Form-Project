import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
comprehend = boto3.client("comprehend")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN  = os.environ["TOPIC_ARN"]
table = dynamodb.Table(TABLE_NAME)

# Simple heuristic threshold — a NEGATIVE score above this,
# combined with common spam markers, flags the message for review
# instead of notifying immediately.
NEGATIVE_SENTIMENT_THRESHOLD = 0.85
SPAM_KEYWORDS = {"buy now", "click here", "free money", "act now", "www.", "http://", "https://"}


def lambda_handler(event, context):
    # SQS can deliver a batch of records in one invocation
    for record in event.get("Records", []):
        try:
            process_message(json.loads(record["body"]))
        except Exception as e:
            # Log and continue — one bad message shouldn't drop the
            # rest of the batch. Failed records return to the queue
            # automatically since we don't raise here.
            print(f"Failed to process record: {e}")

    return {"statusCode": 200}


def process_message(data):
    text = f"{data['subject']} {data['message']}"

    sentiment_result = comprehend.detect_sentiment(Text=text[:5000], LanguageCode="en")
    sentiment = sentiment_result["Sentiment"]
    negative_score = sentiment_result["SentimentScore"]["Negative"]

    has_spam_keyword = any(kw in text.lower() for kw in SPAM_KEYWORDS)
    is_spam = has_spam_keyword or (sentiment == "NEGATIVE" and negative_score > NEGATIVE_SENTIMENT_THRESHOLD)

    table.put_item(Item={
        "message_id":   data["message_id"],
        "name":         data["name"],
        "email":        data["email"],
        "subject":      data["subject"],
        "message":      data["message"],
        "submitted_at": data["submitted_at"],
        "sentiment":    sentiment,
        "is_spam":      is_spam,
    })

    # Only notify the site owner for legitimate messages —
    # spam gets stored for visibility in the admin dashboard,
    # but doesn't clutter the inbox.
    if not is_spam:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"New contact message: {data['subject']}"[:100],
            Message=(
                f"From: {data['name']} ({data['email']})\n"
                f"Subject: {data['subject']}\n\n"
                f"Message:\n{data['message']}\n\n"
                f"Sentiment: {sentiment}"
            ),
        )
