<a id="top"></a>

# 🛠️ Build Log — Smart Contact Form

A step-by-step record of the AWS resources created, their important settings, and the real engineering decisions made during the build.

## 📋 Quick Navigation

| Step | Section |
|---|---|
| 1 | [🗃️ DynamoDB Table](#step-1) |
| 2 | [📬 SQS Queue](#step-2) |
| 3 | [📣 SNS Topic](#step-3) |
| 4 | [🔑 Cognito User Pool](#step-4) |
| 5 | [🔐 IAM Role & Policy](#step-5) |
| 6 | [⚡ Lambda: submit-handler](#step-6) |
| 7 | [⚡ Lambda: message-processor](#step-7) |
| 8 | [⚡ Lambda: get-messages](#step-8) |
| 9 | [🔌 API Gateway](#step-9) |
| 10 | [🛡️ AWS WAF](#step-10) |
| 11 | [🌍 S3 + CloudFront (OAC)](#step-11) |
| 12 | [🔒 CORS Restriction](#step-12) |
| 13 | [✅ End-to-End Test](#step-13) |

---

<a id="step-1"></a>
## Step 1 — 🗃️ DynamoDB Table

DynamoDB stores every submitted message together with its sentiment analysis result and spam classification.

| Setting | Value |
|---|---|
| Table name | `contact-messages` |
| Partition key | `message_id` |
| Key type | String |
| Capacity mode | On-demand |

![DynamoDB table](screenshots/01-dynamodb.png)

---

<a id="step-2"></a>
## Step 2 — 📬 SQS Queue

SQS decouples the public submission request from the heavier processing pipeline.

The user does not have to wait for Comprehend, DynamoDB, and SNS operations to finish before receiving a response.

| Setting | Value |
|---|---|
| Queue name | `contact-messages-queue` |
| Type | Standard |
| Visibility timeout | 30 seconds |

![SQS queue](screenshots/02-sqs-queue.png)

---

<a id="step-3"></a>
## Step 3 — 📣 SNS Topic

SNS sends an email notification to the site owner for messages that pass the spam check.

| Setting | Value |
|---|---|
| Topic name | `contact-notifications` |
| Type | Standard |
| Subscription | Email |
| Subscription status | Confirmed |

![SNS topic](screenshots/03-sns-topic.png)

---

<a id="step-4"></a>
## Step 4 — 🔑 Cognito User Pool

Cognito provides real authentication for the admin dashboard instead of storing a hardcoded password in the frontend.

| Setting | Value |
|---|---|
| Pool name | `contact-admin-pool` |
| Application type | Traditional web application |
| Admin user | Created manually in Users |

![Cognito user pool](screenshots/04-cognito-pool.png)

![Cognito admin user](screenshots/04-cognito-user.png)

---

<a id="step-5"></a>
## Step 5 — 🔐 IAM Role & Policy

A shared Lambda execution role was configured with the permissions required by the application.

The policy covers:

- CloudWatch Logs
- SQS message operations
- DynamoDB operations
- SNS publishing
- Amazon Comprehend sentiment detection

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:contact-messages-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Scan",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/contact-messages"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "comprehend:DetectSentiment",
      "Resource": "*"
    }
  ]
}
```

![IAM role](screenshots/05-iam-role.png)

---

<a id="step-6"></a>
## Step 6 — ⚡ Lambda: `submit-handler`

This function is intentionally lightweight.

It validates the incoming request and pushes the message to SQS. Heavy processing is handled asynchronously by `message-processor`.

| Setting | Value |
|---|---|
| Function name | `submit-handler` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Environment variables | `QUEUE_URL`, `ALLOWED_ORIGIN` |
| Timeout | 10 seconds |

![submit-handler configuration](screenshots/06-lambda-submit-config.png)

Full code: `code/lambda/submit_handler/lambda_function.py`

---

<a id="step-7"></a>
## Step 7 — ⚡ Lambda: `message-processor`

This function is triggered by SQS.

Its job is to:

1. Read the queued message.
2. Analyze sentiment using Amazon Comprehend.
3. Apply the project's spam logic.
4. Store the result in DynamoDB.
5. Publish an SNS notification only when the message is considered legitimate.

| Setting | Value |
|---|---|
| Function name | `message-processor` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Environment variables | `TABLE_NAME`, `TOPIC_ARN` |
| Trigger | SQS — `contact-messages-queue` |

![message-processor configuration](screenshots/07-lambda-processor-config.png)

![SQS trigger](screenshots/07-lambda-trigger.png)

Full code: `code/lambda/message_processor/lambda_function.py`

---

<a id="step-8"></a>
## Step 8 — ⚡ Lambda: `get-messages`

This Lambda retrieves stored messages for the admin dashboard.

It is not exposed as an unrestricted public endpoint; API Gateway protects it with Cognito authorization.

| Setting | Value |
|---|---|
| Function name | `get-messages` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Environment variables | `TABLE_NAME`, `ALLOWED_ORIGIN` |

![get-messages configuration](screenshots/08-lambda-getmessages-config.png)

Full code: `code/lambda/get_messages/lambda_function.py`

---

<a id="step-9"></a>
## Step 9 — 🔌 API Gateway

API Gateway connects the frontend to the Lambda backend.

| Setting | Value |
|---|---|
| API name | `contact-api` |
| API type | REST API |
| Endpoint type | Regional |
| Stage | `prod` |
| `POST /submit` | Public → `submit-handler` |
| `GET /messages` | Cognito-authorized → `get-messages` |

The admin route uses a Cognito authorizer, so API Gateway validates the user's authentication token before forwarding the request to Lambda.

![API Gateway resources](screenshots/09-apigateway-resources.png)

![Cognito authorizer](screenshots/09-apigateway-authorizer.png)

![API Gateway invoke URL](screenshots/09-apigateway-invoke.png)

---

<a id="step-10"></a>
## Step 10 — 🛡️ AWS WAF

AWS WAF was added as an additional protection layer in front of the API.

### Rules Used

| Rule | Purpose |
|---|---|
| Custom rate-based rule | Block abusive request rates |
| AWS Managed Core Rule Set | Protect against common web exploits |

The rate-based rule was configured for **100 requests per 5 minutes**.

![WAF Web ACL](screenshots/10-waf-webacl.png)

![WAF rules](screenshots/10-waf-rules.png)

### 💰 Cost Decision

WAF was not left running permanently.

The recommended WAF package includes additional protection such as Bot Control and can introduce significant fixed and request-based costs. WAF also does not provide the same Free Tier-style idle economics as the serverless services used elsewhere in this demo.

For this portfolio project:

1. A minimal WAF configuration was created.
2. The rules were validated.
3. Rate-limit blocking was tested.
4. Screenshots were captured as evidence.
5. The Web ACL was deleted immediately afterward.

This gives the project a real WAF implementation and test without leaving a continuously billable protection layer attached to a demo API.

![WAF blocked request test](screenshots/13-fulltest-waf-blocked.png)

---

<a id="step-11"></a>
## Step 11 — 🌍 S3 + CloudFront (Private, via OAC)

The frontend is hosted in S3 but the bucket itself remains private.

CloudFront is the only service allowed to read the S3 origin through **Origin Access Control (OAC)**.

| Setting | Value |
|---|---|
| Bucket | `contact-frontend-<account-id>` |
| Block Public Access | On |
| CloudFront origin access | OAC |
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Default root object | `index.html` |

![S3 bucket](screenshots/11-s3-bucket.png)

![CloudFront distribution](screenshots/11-cloudfront-distribution.png)

![S3 bucket policy](screenshots/11-s3-bucket-policy.png)

---

<a id="step-12"></a>
## Step 12 — 🔒 CORS Restriction

The public-facing Lambda functions were configured to allow the real CloudFront frontend origin instead of using a wildcard.

| Setting | Before | Final |
|---|---|---|
| `ALLOWED_ORIGIN` | `*` | CloudFront domain |

![Lambda allowed origin](screenshots/12-lambda-allowed-origin.png)

This prevents unrelated browser origins from being treated as trusted frontend origins.

---

<a id="step-13"></a>
## Step 13 — ✅ End-to-End Test

The final test covered the full application pipeline.

### Test 1 — Normal Message

A normal message was submitted.

Expected and observed behavior:

- Frontend returned a successful response.
- Message was processed asynchronously.
- Message was stored.
- SNS notification email was sent.
- Message appeared in the admin dashboard.

![Normal message](screenshots/13-fulltest-normal.png)

### Test 2 — Spam Message

A message containing spam markers such as `"buy now"` and `"click here"` was submitted.

Expected and observed behavior:

- Message was stored.
- `is_spam` was set to `true`.
- No SNS notification was sent.
- Message remained visible in the admin dashboard.

![Spam message](screenshots/13-fulltest-spam.png)

### Test 3 — Authenticated Admin Dashboard

The Cognito admin user logged in successfully and could retrieve the stored messages.

![Admin dashboard](screenshots/13-fulltest-admin-dashboard.png)

### Final Verification

| Check | Result |
|---|---|
| Normal message → success response | ✅ |
| Normal message → notification sent | ✅ |
| Spam message → flagged | ✅ |
| Spam message → no notification | ✅ |
| Both messages stored | ✅ |
| Cognito admin login | ✅ |
| Admin dashboard shows messages | ✅ |
| WAF rate-limit behavior | ✅ |

> **WAF note:** the WAF block behavior was verified during Step 10. It was not repeated after the Web ACL was deleted.

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
