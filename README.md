# 🛡️ Smart Contact Form — AI-Powered & Secured

> A serverless contact form that decouples submission from processing, filters spam using AI before it reaches an inbox, protects the API from bots and abuse, and gives the site owner a real authenticated dashboard — not just raw database access.

![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live%20Tested-brightgreen)

## Table of Contents
- [The Problem](#the-problem)
- [Architecture](#architecture)
- [Live Test Result](#live-test-result)
- [Skills Demonstrated](#skills-demonstrated)
- [Cost Decisions](#cost-decisions)
- [Possible Improvements](#possible-improvements)
- [Repository Structure](#repository-structure)

## The Problem

A public contact form is an easy target: spam bots submit junk 24/7, malicious actors probe it for exploits, and every submission — real or fake — normally lands straight in the owner's inbox with no filtering and no access control on who can view past messages.

This project builds a small defense-in-depth pipeline around a contact form to solve exactly that:

| Risk | How this project handles it |
|---|---|
| Bots hammering the endpoint | **AWS WAF** rate-limits and blocks abusive traffic at the edge |
| Spam / abusive messages reaching the inbox | **Amazon Comprehend** scores sentiment; suspicious messages are stored but never trigger a notification |
| Slow user experience while the backend does work | **SQS** decouples the request from processing — the user gets an instant response |
| Anyone with the DynamoDB console being able to read messages | **Cognito** locks the admin view behind real authentication |

## Architecture

![Architecture Diagram](screenshots/architecture-diagram.png)

| Layer | Service | Purpose |
|---|---|---|
| Frontend delivery | S3 (private) + CloudFront | Static site served over HTTPS, origin locked to CloudFront only via OAC |
| Edge protection | AWS WAF | Rate limiting + core exploit protection in front of the API |
| API | API Gateway (REST) | `POST /submit` (public), `GET /messages` (Cognito-authorized) |
| Decoupling | SQS | Submission is queued instantly; processing happens asynchronously |
| Compute | Lambda x3 (Python 3.12) | Submission intake, AI processing, admin data retrieval |
| AI filtering | Amazon Comprehend | Sentiment analysis used as an input to spam detection |
| Storage | DynamoDB | Stores messages with sentiment score and spam flag |
| Notifications | SNS | Emails the owner — only for messages that pass the spam check |
| Authentication | Amazon Cognito | Real login for the admin dashboard (SPA app client) |

Region: `eu-north-1` (Comprehend calls target `eu-west-1`, since Comprehend isn't offered in `eu-north-1`)

## Live Test Result

Submitted both a normal message and a message containing spam markers. The normal message triggered an instant email notification; the spam message was silently flagged and stored without notifying the owner. The WAF rate limit was verified with a batched load test (Total 1060 · Allowed 965 · Blocked 100). Both message types were visible, correctly labeled, in the Cognito-authenticated admin dashboard.

![Admin dashboard showing flagged and clean messages](screenshots/13-fulltest-admin-dashboard.png)

## Skills Demonstrated

- Decoupling a request/response flow with SQS so user-facing latency stays low
- Using a managed AI service (Comprehend) as one signal in a broader filtering decision, rather than trusting it blindly, including handling cross-region service availability
- Protecting an API Gateway endpoint with a Cognito authorizer and choosing the correct app client type (SPA) for browser-based auth
- Coordinating CORS configuration across two independently-configured services (Lambda and API Gateway)
- Testing a rate-based WAF rule the way it actually behaves in production (sustained batches) rather than assuming an instant burst
- Evaluating AWS WAF's pricing model in detail and making a deliberate, documented trade-off between coverage and cost

## Cost Decisions

AWS WAF has **no free tier** — the "Recommended" rule package (which bundles Bot Control) was estimated at $58-59 per 10M requests/month, with fixed hourly charges regardless of real traffic. A custom, minimal rule pack (rate limiting + core rule set only, ~$11 baseline) was built instead using WAF's "You build it" option, verified working, and the Web ACL should be deleted whenever not actively demoing.

Every other component (S3, CloudFront, API Gateway, Lambda, SQS, DynamoDB, SNS, Cognito, and Comprehend at this call volume) has an always-free tier or near-zero cost and was left running.

## Possible Improvements

- Replace the keyword + sentiment spam heuristic with a custom-trained Comprehend classifier
- Add a Dead Letter Queue (DLQ) on the SQS queue to catch messages that fail processing repeatedly
- Move the WAF Web ACL into Infrastructure as Code (Terraform) so it can be recreated on demand for a live demo without manual reconfiguration
- Add CloudWatch alarms on Lambda error rates and SQS queue depth
- Move email delivery from SNS to Amazon SES for the submitter-facing notification, since SES doesn't attach the `List-Unsubscribe` header that SNS does by default — which can cause mail clients to treat transactional emails as bulk subscriptions

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
