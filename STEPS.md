<a id="top"></a>

# 🛠️ Build Log — Smart Contact Form

Each step below is the correct way to do it, with a short explanation of its purpose.

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
| 12 | [✅ End-to-End Test](#step-12) |

---

<a id="step-1"></a>
## Step 1 — 🗃️ DynamoDB Table

This stores every message, along with its AI-generated sentiment and spam flag.

| Setting | Value |
|---|---|
| Name | `contact-messages` |
| Partition key | `message_id` (String) |
| Capacity mode | On-demand |

---

<a id="step-2"></a>
## Step 2 — 📬 SQS Queue

This is what lets the user get an instant response on the form, instead of waiting for the full processing (analysis + storage + email) to finish first.

| Setting | Value |
|---|---|
| Name | `contact-messages-queue` |
| Type | Standard |
| Visibility timeout | 30 seconds |

---

<a id="step-3"></a>
## Step 3 — 📣 SNS Topic

Sends an email to the site owner, but only for messages that pass the spam check.

| Setting | Value |
|---|---|
| Topic name | `contact-notifications` |
| Type | Standard |
| Subscription | Email, confirmed |

![SNS topic confirmed](screenshots/03-sns-topic.png)

---

<a id="step-4"></a>
## Step 4 — 🔑 Cognito User Pool

This is what provides real login for the admin dashboard, instead of a hardcoded password in the code.

| Setting | Value |
|---|---|
| Pool name | `contact-admin-pool` |
| Application type | **Single-page application (SPA)** |
| Admin user | Created manually in the Users tab |

**Important note when creating the App Client:** it must be type **SPA** specifically (not "Traditional web application"), because SPA is the only type created without a Client Secret — and any browser-side JavaScript (like `admin.js`) needs exactly that, since it has no secure place to hide a secret.

**If you need to reset an existing user's password**, the fastest way from outside the console is via AWS CLI in CloudShell:
```bash
aws cognito-idp admin-set-user-password \
  --region eu-north-1 \
  --user-pool-id eu-north-1_SmeRcy5oG \
  --username darkxalfax@gmail.com \
  --password "NewPass123!" \
  --permanent
```

![Cognito user pool](screenshots/04-cognito-pool.png)
![Cognito admin user created](screenshots/04-cognito-user.png)

---

<a id="step-5"></a>
## Step 5 — 🔐 IAM Role & Policy

Permissions scoped to exactly what the Lambda functions actually use — nothing more.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:*:*:contact-messages-queue"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:Scan", "dynamodb:GetItem"],
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
## Step 6 — ⚡ Lambda: submit-handler

Quickly validates the form data and puts it on the queue — no heavy processing here, so the user gets an immediate response.

| Setting | Value |
|---|---|
| Name | `submit-handler` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Env vars | `QUEUE_URL`, `ALLOWED_ORIGIN` |
| Timeout | 10 sec |

Full code: [`code/lambda/submit_handler/lambda_function.py`](code/lambda/submit_handler/lambda_function.py)

---

<a id="step-7"></a>
## Step 7 — ⚡ Lambda: message-processor

This one runs automatically from SQS, analyzes the message with Comprehend, decides whether it's spam, and sends the email.

| Setting | Value |
|---|---|
| Name | `message-processor` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Env vars | `TABLE_NAME`, `TOPIC_ARN` |
| Trigger | SQS — `contact-messages-queue` |

**Note on region:** Amazon Comprehend isn't available in every region — `eu-north-1` (Stockholm) is one where it's not offered. The client must explicitly target a supported region:
```python
comprehend = boto3.client("comprehend", region_name="eu-west-1")
```
The rest of the project (Lambda, DynamoDB, SQS, etc.) stays in `eu-north-1` as normal — only the Comprehend call goes to a different region, which is normal and the latency difference is negligible.

**Tip for editing code inside the Lambda console:** if you're modifying existing code, replace the entire file rather than pasting a partial edit — it reduces the chance of indentation errors.

Full code: [`code/lambda/message_processor/lambda_function.py`](code/lambda/message_processor/lambda_function.py)

![SQS trigger attached](screenshots/07-lambda-trigger.png)

---

<a id="step-8"></a>
## Step 8 — ⚡ Lambda: get-messages

Returns every message (including flagged spam) to the protected admin dashboard.

| Setting | Value |
|---|---|
| Name | `get-messages` |
| Runtime | Python 3.12 |
| Role | `contact-lambda-role` |
| Env vars | `TABLE_NAME`, `ALLOWED_ORIGIN` |

Full code: [`code/lambda/get_messages/lambda_function.py`](code/lambda/get_messages/lambda_function.py)

---

<a id="step-9"></a>
## Step 9 — 🔌 API Gateway

Connects the frontend to all three Lambda functions, with the admin route protected by Cognito.

| Setting | Value |
|---|---|
| API name | `contact-api` (REST, Regional) |
| `POST /submit` | Public → `submit-handler` |
| `GET /messages` | **Cognito-protected** → `get-messages` |
| Stage | `prod` |

**Important note on CORS:** there are **two separate places** that must be configured together, not just one:
1. `ALLOWED_ORIGIN` inside the Lambda itself (environment variable)
2. The `Access-Control-Allow-Origin` header on API Gateway's own **OPTIONS** method (Method Response / Integration Response)

The value in both must match **exactly** (`https://`, not `http://`, no trailing `/`). After any change in API Gateway, you must run **Actions → Deploy API → prod** for the change to actually take effect.

![Cognito authorizer attached to /messages](screenshots/09-apigateway-authorizer.png)
![API Gateway invoke URL](screenshots/09-apigateway-invoke.png)

---

<a id="step-10"></a>
## Step 10 — 🛡️ AWS WAF (new console interface)

Adds a protection layer in front of the API — rate limiting and baseline protection against known attacks. The console interface has changed recently, so here are the current steps:

1. **WAF & Shield** → **Protection packs (web ACLs)** → **Create protection pack**
2. **Tell us about your app:**
   - App category: pick anything close (e.g. "Other")
   - App focus: **API**
3. **Select resources to protect:** choose `contact-api` (stage `prod`)
4. **Choose initial protections:** pick **"You build it"** (Build your own pack), not "Recommended" or "Essentials" — for tighter cost control (details below)
5. Under **Add rules**, add two:
   - **Custom rule** → Rate-based rule → Limit: `100` requests / `5` minutes → Action: **Block**
   - **AWS-managed rule group** → **AWS Core rule set**
6. **Create protection pack**

**How to test it correctly:** rate-based rules can take up to **~30 seconds** to detect an elevated rate — if all requests are sent in one instant burst, they can all pass through before the rule reacts. The correct way: send requests in **batches** (e.g. 3 batches of 100 requests, 15 seconds apart), which will actually show the block working.

**⚠️ Cost:** WAF has **no free tier at all** — fixed monthly charges apply (~$5 per Web ACL + $1 per rule) regardless of traffic volume. The "You build it" plan with 2 rules costs roughly ~$11, versus $58-59 for "Recommended" (which adds Bot Control at a much higher cost for no real benefit here). **Delete the Web ACL whenever not actively demoing.**

![WAF protection pack configured](screenshots/10-waf-webacl.png)
![WAF rules — rate limit + core rule set](screenshots/10-waf-rules.png)

---

<a id="step-11"></a>
## Step 11 — 🌍 S3 + CloudFront (new console interface)

The bucket stays fully private, and only CloudFront can read from it. The new console interface now hides these settings under "Customize" instead of showing them directly:

1. **S3** → **Create bucket** → `contact-frontend-<account-id>` → **leave Block all public access enabled**
2. Upload the frontend files (`index.html`, `admin.html`, `style.css`, `script.js`, `admin.js`)
3. **CloudFront** → **Create distribution**
4. Origin: select the S3 bucket
5. **Allow private S3 bucket access to CloudFront**: leave this **enabled ✅** — this sets up OAC automatically, no extra steps needed
6. **Origin settings**: leave on **Use recommended origin settings**
7. **Cache settings**: choose **Customize cache settings** (so you can set these):
   - **Viewer protocol policy**: Redirect HTTP to HTTPS
   - **Allowed HTTP methods**: GET, HEAD
   - **Cache policy**: use the recommended existing one, don't create a new one
8. **Enable security protections**: choose **"Do not enable security protections"** — the suggested WAF here has its own estimated cost and isn't needed (WAF was already set up separately and deliberately in Step 10)
9. **Create distribution**

**About the default root object:** if it's not shown during creation, don't worry — after the distribution is created, you can go into its settings (General → Edit) and set it to `index.html` there if it wasn't set automatically.

10. Once the distribution is ready, a banner will show a **ready-made bucket policy** — click **Copy policy**, and paste it into **S3 → Bucket policy → Edit → Paste → Save**

![S3 bucket — public access blocked](screenshots/11-s3-bucket.png)
![CloudFront distribution enabled](screenshots/11-cloudfront-distribution.png)
![S3 bucket policy scoped to CloudFront](screenshots/11-s3-bucket-policy.png)

---

<a id="step-12"></a>
## Step 12 — ✅ End-to-End Test

A full check of the entire project, start to finish.

| Check | Result |
|---|---|
| Normal message → stored + email sent | ✅ |
| Spam message → `is_spam: true`, no email | ✅ |
| WAF rate limit (batched test) | ✅ Total 1060 · Allowed 965 · Blocked 100 |
| Admin dashboard (Cognito login) | ✅ All messages shown with correct flags |
| Amazon Comprehend | ✅ Active, returning real sentiment scores |
| Email delivery via SNS | ✅ |

![Form submitted successfully](screenshots/13-fulltest-form.png)
![Admin dashboard showing flagged and clean messages](screenshots/13-fulltest-admin-dashboard.png)

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
