# 🛡️ Smart Contact Form — AI-Powered & Secured

> A serverless contact form that decouples submission from processing, filters spam using AI before it reaches an inbox, protects the API from bots and abuse, and gives the site owner a real authenticated dashboard — not just raw database access.

![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live%20Tested-brightgreen)

![Lambda](https://img.shields.io/badge/Lambda-FF9900?style=flat&logo=awslambda&logoColor=white)
![SQS](https://img.shields.io/badge/SQS-FF4F8B?style=flat&logo=amazonsqs&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat&logo=amazondynamodb&logoColor=white)
![Cognito](https://img.shields.io/badge/Cognito-DD344C?style=flat&logo=amazoncognito&logoColor=white)
![Comprehend](https://img.shields.io/badge/Comprehend-232F3E?style=flat&logo=amazonaws&logoColor=white)
![WAF](https://img.shields.io/badge/WAF-232F3E?style=flat&logo=amazonaws&logoColor=white)

## Table of Contents

- [The Problem](#the-problem)
- [Architecture](#architecture)
- [Features](#features)
- [Live Test Result](#live-test-result)
- [Cost Decisions](#cost-decisions)
- [Possible Improvements](#possible-improvements)
- [Repository Structure](#repository-structure)

---

## The Problem

A public contact form is an easy target: spam bots submit junk 24/7, malicious actors probe it for exploits, and every submission — real or fake — normally lands straight in the owner's inbox with no filtering and no access control on who can view past messages.

This project builds a small defense-in-depth pipeline around a contact form to solve exactly that:

| **Risk** | **How this project handles it** |
| --- | --- |
| Bots hammering the endpoint | **AWS WAF** rate-limits and blocks abusive traffic at the API |
| Spam / abusive messages reaching the inbox | **Amazon Comprehend** provides sentiment analysis, combined with keyword heuristics; suspicious messages are stored but do not trigger notifications |
| Slow user experience while the backend does work | **SQS** decouples the request from processing — the user gets an instant response |
| Anyone being able to read stored messages | **Cognito** locks the admin view behind real authentication |

---

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

| **Layer** | **Service** | **Purpose** |
| --- | --- | --- |
| Frontend delivery | S3 (private) + CloudFront | Static site served over HTTPS, with the S3 origin locked to CloudFront |
| Edge protection | AWS WAF | Rate limiting + AWS-managed core rules in front of the API |
| API | API Gateway (REST) | `POST /submit` (public), `GET /messages` (Cognito-authorized) |
| Decoupling | SQS | Submission is queued instantly; processing happens asynchronously |
| Compute | Lambda x3 (Python 3.12) | Submission intake, AI processing, and admin data retrieval |
| AI filtering | Amazon Comprehend | Sentiment analysis used as an input to spam detection |
| Storage | DynamoDB | Stores messages with sentiment information and spam flag |
| Notifications | SNS | Emails the owner only for messages that pass the spam check |
| Authentication | Amazon Cognito | Real login for the admin dashboard |

Region: `eu-north-1`

---

## Features

- **Async submission** — the user gets an instant response while processing happens in the background
- **AI-assisted spam filtering** using Amazon Comprehend sentiment analysis combined with keyword heuristics
- **Bot and abuse protection** via AWS WAF rate limiting and AWS-managed core rules
- **Authenticated admin dashboard** — messages can be reviewed through a protected web interface
- **HTTPS everywhere** via CloudFront, with a fully private S3 origin
- **CORS restriction** using the deployed CloudFront origin instead of a wildcard
- **Serverless architecture** with Lambda, API Gateway, SQS, DynamoDB, SNS, Cognito, and Comprehend

---

## Live Test Result

The complete flow was tested with both normal and spam-like messages.

A normal message was processed successfully and triggered the owner notification. A message containing spam markers such as `buy now` and `click here` was stored with `is_spam: true` and did not trigger an owner notification.

Both messages remained available in the Cognito-authenticated admin dashboard, where the spam message was correctly flagged.

### Admin Dashboard

![Admin Dashboard](screenshots/13-fulltest-admin-dashboard.png)

![Admin Dashboard](screenshots/13-fulltest-admin-dashboard%282%29.png)

### Normal Message

![Normal Message](screenshots/13-fulltest-normal.png)

![Normal Message](screenshots/13-fulltest-normal%282%29.png)

### Spam Message

![Spam Message](screenshots/13-fulltest-spam.png)

![Spam Message](screenshots/13-fulltest-spam%282%29.png)

### WAF Blocking Test

The WAF configuration was also tested before the Web ACL was deleted to avoid ongoing charges.

![WAF Blocked Request](screenshots/13-fulltest-waf-blocked.png)

![WAF Blocked Request](screenshots/13-fulltest-waf-blocked%282%29.png)

---

## Cost Decisions

AWS WAF has **no Free Tier**. The AWS WAF Recommended rule package, which includes additional protection such as Bot Control, was estimated at roughly $58–59 per 10M requests/month, while a smaller custom configuration was estimated at around $11 baseline.

For this portfolio project, a custom WAF configuration was created with rate limiting and the AWS-managed Core Rule Set, tested successfully, and then the Web ACL was **deleted immediately after capturing the evidence** because the project does not have real production traffic to protect.

Every other component was left available for continued testing because the project uses serverless services with Free Tier / low idle-cost characteristics.

Full implementation details and decisions are documented in [`STEPS.md`](STEPS.md) and [`CONCEPTS.md`](CONCEPTS.md).

---

## Possible Improvements

- Replace the keyword + sentiment spam heuristic with a custom-trained Comprehend classifier
- Add a Dead Letter Queue (DLQ) to catch messages that fail processing repeatedly
- Move the WAF Web ACL into Infrastructure as Code (Terraform) so it can be recreated on demand for a live demo
- Add CloudWatch alarms on Lambda error rates and SQS queue depth
- Add stronger validation and structured logging across the API and processing pipeline

---

## Repository Structure

```text
AWS-Smart-Contact-Form-Project/
├── README.md
├── STEPS.md              # Full step-by-step build log
├── CONCEPTS.md           # Design rationale for each decision
├── screenshots/
├── code/
│   ├── lambda/
│   │   ├── submit_handler/lambda_function.py
│   │   ├── message_processor/lambda_function.py
│   │   └── get_messages/lambda_function.py
│   └── frontend/
│       ├── index.html
│       ├── admin.html
│       ├── style.css
│       ├── script.js
│       └── admin.js
└── IAM/
    └── contact-lambda-policy.json
```
