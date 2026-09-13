# 🛡️ Smart Contact Form — AI-Powered & Secured

> A serverless contact form that decouples submission from processing, filters spam using AI-assisted analysis before it reaches the owner's inbox, protects the API from abuse, and provides a real authenticated admin dashboard.

![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?style=flat&logo=awslambda&logoColor=white)
![SQS](https://img.shields.io/badge/AWS-SQS-FF4F8B?style=flat&logo=amazonsqs&logoColor=white)
![DynamoDB](https://img.shields.io/badge/AWS-DynamoDB-4053D6?style=flat&logo=amazondynamodb&logoColor=white)
![Cognito](https://img.shields.io/badge/AWS-Cognito-DD344C?style=flat&logo=amazoncognito&logoColor=white)
![Comprehend](https://img.shields.io/badge/AWS-Comprehend-232F3E?style=flat&logo=amazonaws&logoColor=white)
![WAF](https://img.shields.io/badge/AWS-WAF-232F3E?style=flat&logo=amazonaws&logoColor=white)

---

## 📋 Table of Contents

- [The Problem](#the-problem)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Features](#features)
- [Security](#security)
- [Cost Decisions](#cost-decisions)
- [Live Test Result](#live-test-result)
- [Repository Structure](#repository-structure)
- [Documentation](#documentation)
- [Possible Improvements](#possible-improvements)

---

## The Problem

A public contact form is an easy target for spam bots and abusive traffic. At the same time, processing every submission synchronously can make the user wait while the backend performs AI analysis, database operations, and email notification.

This project builds a small **serverless defense-in-depth pipeline** around a contact form.

| Problem | Solution |
|---|---|
| Bots and abusive traffic | **AWS WAF** rate limiting + AWS Managed Core Rule Set |
| Spam reaching the owner's inbox | **Amazon Comprehend** + keyword heuristics |
| Slow synchronous processing | **Amazon SQS** decouples submission from processing |
| Unauthorized access to messages | **Amazon Cognito** protects the admin endpoint |
| Public access to frontend storage | **Private S3** bucket + CloudFront OAC |
| Unnecessary notifications | SNS only publishes for messages that pass spam checks |

---

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

### AWS Services

| Layer | Service | Purpose |
|---|---|---|
| Frontend | S3 + CloudFront | Private static website delivered over HTTPS |
| Edge / API protection | AWS WAF | Rate limiting and core exploit protection |
| API | API Gateway REST | Public submission + protected admin endpoint |
| Queue | SQS Standard | Asynchronous message processing |
| Compute | Lambda ×3 | Submission, processing, and admin retrieval |
| AI | Amazon Comprehend | Sentiment analysis used in spam detection |
| Storage | DynamoDB | Stores messages, sentiment, and spam status |
| Notifications | SNS | Sends owner email for legitimate messages |
| Authentication | Cognito | Admin login and API authorization |

**Region:** `eu-north-1`

---

## How It Works

### 1. Public Submission

The visitor submits the contact form.

```text
Frontend
   ↓
CloudFront
   ↓
AWS WAF
   ↓
API Gateway
   ↓
submit-handler
```

The `submit-handler` validates the request and sends the message to SQS instead of performing all processing synchronously.

### 2. Asynchronous Processing

```text
submit-handler
      ↓
     SQS
      ↓
message-processor
      ↓
Amazon Comprehend
      ↓
Spam decision
   ↙       ↘
Spam      Legitimate
  ↓           ↓
DynamoDB    DynamoDB
              ↓
             SNS
              ↓
         Owner email
```

Spam messages are still stored so the administrator can review them later.

### 3. Protected Admin Dashboard

```text
Admin
  ↓
Cognito Login
  ↓
JWT / Access Token
  ↓
API Gateway
  ↓
Cognito Authorizer
  ↓
get-messages
  ↓
DynamoDB
  ↓
Admin Dashboard
```

Unauthenticated users are rejected by API Gateway before the Lambda function is invoked.

---

## Features

- **Asynchronous submission** — the user receives a fast response while processing continues in the background.
- **AI-assisted spam filtering** — Amazon Comprehend sentiment analysis is combined with keyword heuristics.
- **Spam preservation** — flagged messages remain available for admin review.
- **Authenticated admin dashboard** — Cognito protects access to stored messages.
- **API protection** — AWS WAF was configured and tested with rate limiting and AWS Managed Core Rule Set.
- **Private frontend origin** — S3 public access remains blocked; CloudFront accesses the bucket through OAC.
- **HTTPS delivery** — CloudFront redirects HTTP traffic to HTTPS.
- **CORS restriction** — public-facing Lambda functions accept requests from the actual CloudFront origin instead of `*`.

---

## Security

The project uses multiple security layers rather than relying on a single control.

### S3 + CloudFront

The S3 bucket is private with **Block Public Access** enabled. CloudFront uses **Origin Access Control (OAC)** to retrieve the frontend files.

### Cognito

The admin dashboard uses a real Cognito user rather than a hardcoded frontend password.

### API Gateway

- `POST /submit` is public.
- `GET /messages` requires Cognito authorization.

### IAM

The Lambda execution role uses scoped permissions for the resources required by the application:

- CloudWatch Logs
- SQS
- DynamoDB
- SNS
- Amazon Comprehend

### CORS

`ALLOWED_ORIGIN` was changed from a wildcard to the actual CloudFront domain on the public-facing Lambdas.

---

## Cost Decisions

AWS WAF was intentionally treated differently from the rest of the project.

The WAF Web ACL was configured with:

- A custom rate-based rule
- AWS Managed Core Rule Set

The configuration was tested, evidence was captured, and the Web ACL was then deleted because this is a portfolio/demo project with no production traffic.

The more expensive WAF recommended package, including Bot Control, was intentionally avoided because its additional protection was not justified for a low-traffic demonstration.

The other services were left available for continued learning/testing because the project uses serverless services with usage-based pricing and Free Tier/low-usage characteristics. Actual AWS pricing can vary by account, region, usage, and current AWS pricing terms.

For the detailed build-time cost reasoning, see [`STEPS.md`](STEPS.md) and [`CONCEPTS.md`](CONCEPTS.md).

---

## Live Test Result

The complete application was tested end-to-end.

### Normal Message

A normal message was submitted successfully and resulted in:

- Successful frontend response
- Message stored in DynamoDB
- Notification email sent through SNS
- Message visible in the authenticated admin dashboard

![Normal message submitted](screenshots/13-fulltest-normal.png)

### Spam Message

A message containing spam markers such as `"buy now"` and `"click here"` was:

- Stored in DynamoDB
- Marked as `is_spam: true`
- Excluded from the owner notification
- Still visible in the admin dashboard

![Spam message flagged](screenshots/13-fulltest-spam.png)

### Admin Dashboard

The Cognito-authenticated dashboard displayed both normal and spam messages with their classification.

![Admin dashboard](screenshots/13-fulltest-admin-dashboard.png)

### Test Summary

| Test | Result |
|---|---|
| Normal message submitted | ✅ |
| Normal message → SNS notification | ✅ |
| Spam message detected | ✅ |
| Spam message → no notification | ✅ |
| Spam message stored for review | ✅ |
| Cognito admin login | ✅ |
| Admin dashboard displays messages | ✅ |
| WAF rate-limit behavior | ✅ Tested during WAF configuration |

> **Note:** WAF was not left attached after testing because the project has no real production traffic and the Web ACL carries ongoing charges.

---

## Repository Structure

```text
AWS-Smart-Contact-Form-Project/
├── README.md
├── STEPS.md
├── CONCEPTS.md
├── screenshots/
│   ├── architecture-diagram.png
│   ├── 01-dynamodb.png
│   ├── 02-sqs-queue.png
│   ├── 03-sns-topic.png
│   ├── 04-cognito-pool.png
│   ├── 04-cognito-user.png
│   ├── 05-iam-role.png
│   ├── 06-lambda-submit-config.png
│   ├── 07-lambda-processor-config.png
│   ├── 07-lambda-trigger.png
│   ├── 08-lambda-getmessages-config.png
│   ├── 09-apigateway-authorizer.png
│   ├── 09-apigateway-invoke.png
│   ├── 09-apigateway-resources.png
│   ├── 10-waf-rules.png
│   ├── 10-waf-webacl.png
│   ├── 11-cloudfront-distribution.png
│   ├── 11-s3-bucket-policy.png
│   ├── 11-s3-bucket.png
│   ├── 12-lambda-allowed-origin.png
│   └── 13-fulltest-*.png
├── code/
│   ├── lambda/
│   │   ├── submit_handler/
│   │   ├── message_processor/
│   │   └── get_messages/
│   └── frontend/
└── IAM/
    └── contact-lambda-policy.json
```

---

## Documentation

| File | Purpose |
|---|---|
| [`STEPS.md`](STEPS.md) | Complete step-by-step AWS build log |
| [`CONCEPTS.md`](CONCEPTS.md) | Design decisions and interview-oriented explanations |
| `README.md` | Project overview, architecture, security, tests, and cost decisions |

---

## Possible Improvements

- Replace keyword + sentiment heuristics with a dedicated trained spam classifier.
- Add an SQS Dead Letter Queue (DLQ) for repeatedly failed messages.
- Manage the infrastructure with Terraform or AWS CloudFormation.
- Add CloudWatch alarms for Lambda errors and SQS queue depth.
- Add pagination to the admin dashboard for larger datasets.
- Add message search/filtering to the admin dashboard.
- Recreate the WAF configuration through Infrastructure as Code when the project needs a live protected deployment.

---

<div align="center">

**Serverless • Secure • Asynchronous • AI-Assisted**

</div>
