# 🛡️ Smart Contact Form — AI-Powered & Secured

> A serverless contact form that decouples submission from processing, filters spam using AI before it reaches an inbox, protects the API from bots and abuse, and gives the site owner a real authenticated dashboard — not just raw database access.

![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live%20Tested-brightgreen)

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Live Test Result](#live-test-result)
- [Skills Demonstrated](#skills-demonstrated)
- [Cost Decisions](#cost-decisions)
- [Possible Improvements](#possible-improvements)
- [Repository Structure](#repository-structure)

## Overview

This started as a simple contact form and was deliberately extended into something closer to a real production system: messages are queued instead of processed inline, screened for spam using Amazon Comprehend before anyone gets notified, and reviewed through an admin dashboard that requires actual sign-in — not an open database query.

Every component below was designed, deployed, and verified by hand on a personal AWS account. Full step-by-step build log is in [`STEPS.md`](STEPS.md); design rationale for every decision is in [`CONCEPTS.md`](CONCEPTS.md).

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

| Layer | Service | Purpose |
|---|---|---|
| Frontend delivery | S3 (private) + CloudFront | Static site served over HTTPS, origin locked to CloudFront only |
| Edge protection | AWS WAF | Rate limiting + core exploit protection in front of the API |
| API | API Gateway (REST) | `POST /submit` (public), `GET /messages` (Cognito-authorized) |
| Decoupling | SQS | Submission is queued instantly; processing happens asynchronously |
| Compute | Lambda x3 (Python 3.12) | Submission intake, AI processing, admin data retrieval |
| AI filtering | Amazon Comprehend | Sentiment analysis used as an input to spam detection |
| Storage | DynamoDB | Stores messages with sentiment score and spam flag |
| Notifications | SNS | Emails the owner — only for messages that pass the spam check |
| Authentication | Amazon Cognito | Real login for the admin dashboard |

Region: `eu-north-1`

## Features

- **Async submission** — the user gets an instant response while AI analysis happens in the background
- **AI-assisted spam filtering** using Amazon Comprehend sentiment analysis combined with keyword heuristics
- **Bot and abuse protection** via AWS WAF rate limiting and AWS-managed core rules
- **Authenticated admin dashboard** — no more opening DynamoDB manually to read messages
- **HTTPS everywhere** via CloudFront, with a fully private S3 origin

## Live Test Result

Submitted both a normal message and a message containing spam markers. The normal message triggered an instant email notification; the spam message was silently flagged and stored without notifying the owner. Both were visible, correctly labeled, in the Cognito-authenticated admin dashboard.

![Admin dashboard showing flagged and clean messages](screenshots/13-fulltest-admin-dashboard.png)

## Skills Demonstrated

- Decoupling a request/response flow with SQS so user-facing latency stays low
- Using a managed AI service (Comprehend) as one signal in a broader filtering decision, rather than trusting it blindly
- Protecting an API Gateway endpoint with a Cognito authorizer, so authorization is enforced before any application code runs
- Evaluating AWS WAF's pricing model in detail and making a deliberate, documented trade-off between coverage and cost
- Reusing a proven security pattern (CloudFront + OAC + private S3) across multiple projects instead of reinventing it each time

## Cost Decisions

AWS WAF has **no Free Tier** — the "Recommended" rule package (which bundles Bot Control) was estimated at $58-59 per 10M requests/month, with fixed hourly charges regardless of real traffic. A custom, minimal rule pack (rate limiting + core rule set only, ~$11 baseline) was built instead, verified working, and the Web ACL was deleted immediately after capturing evidence — since this is a demo project with no real traffic to protect. Full reasoning in [`STEPS.md`](STEPS.md#step-10).

Every other component (S3, CloudFront, API Gateway, Lambda, SQS, DynamoDB, SNS, Cognito) has an always-free tier or near-zero idle cost and was left running.

## Possible Improvements

- Replace the keyword + sentiment spam heuristic with a custom-trained Comprehend classifier
- Add a Dead Letter Queue (DLQ) on the SQS queue to catch messages that fail processing repeatedly
- Move the WAF Web ACL into Infrastructure as Code (Terraform) so it can be recreated on demand for a live demo without manual reconfiguration
- Add CloudWatch alarms on Lambda error rates and SQS queue depth

## Repository Structure

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
    └── iam/contact-lambda-policy.json
