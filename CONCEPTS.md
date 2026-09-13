<a id="top"></a>

# 🧠 Design Concepts & Rationale

This file explains **why** the architecture was designed this way and covers the questions most likely to come up in an AWS, Cloud Security, or DevSecOps interview.

## 📋 Quick Navigation

| Topic | Section |
|---|---|
| 📬 | [Decoupling & Async Processing](#decoupling) |
| 🤖 | [AI-Assisted Spam Detection](#ai) |
| 🔐 | [Authentication & Authorization](#authentication) |
| 🛡️ | [Defense in Depth](#security) |
| 🌍 | [Private S3 + CloudFront OAC](#cloudfront) |
| 🔑 | [IAM & Least Privilege](#iam) |
| 🔒 | [CORS](#cors) |
| 💰 | [Cost Decisions](#cost) |
| 🚀 | [Possible Improvements](#improvements) |

---

<a id="decoupling"></a>
## 📬 Decoupling & Async Processing

| Question | Answer |
|---|---|
| Why does `submit-handler` push to SQS instead of processing the message directly? | The submission endpoint only needs to acknowledge receipt quickly. Comprehend analysis, DynamoDB writes, and SNS publishing can take additional time or fail independently. SQS separates the user's request from that background work. |
| Why use SQS Standard instead of FIFO? | Contact form messages have no ordering dependency. Standard SQS provides the required queueing behavior without paying for ordering guarantees the application does not need. |
| What happens if `message-processor` fails? | The SQS message is not successfully completed, so it becomes visible again after the visibility timeout and can be retried. This reduces the chance of silently losing a submission. |
| What is the main architectural benefit? | The frontend-facing request path stays fast while backend processing can scale and retry independently. |

---

<a id="ai"></a>
## 🤖 AI-Assisted Spam Detection

| Question | Answer |
|---|---|
| Why Amazon Comprehend? | It provides managed, pre-trained language analysis without requiring the project to train or host its own ML model. |
| Is sentiment analysis itself a spam detector? | No. Negative sentiment is not automatically spam, and spam can have neutral or positive wording. The project therefore combines sentiment analysis with keyword heuristics. |
| Why store spam messages instead of deleting them? | Immediate deletion can create false positives and permanently lose legitimate messages. Storing them allows an administrator to review the classification. |
| Why perform the analysis asynchronously? | AI analysis is unnecessary for the immediate HTTP acknowledgment, so moving it behind SQS keeps the public request path lightweight. |

---

<a id="authentication"></a>
## 🔐 Authentication & Authorization

| Question | Answer |
|---|---|
| Why Cognito instead of a hardcoded password in the frontend? | A frontend password is not a proper authentication system and can be extracted from client-side code. Cognito provides real user authentication and token-based access. |
| Why attach Cognito to API Gateway? | API Gateway can reject unauthenticated requests before the Lambda function executes. This moves an important security control closer to the API boundary. |
| Is the Cognito Pool ID or Client ID secret? | No. These identifiers can be present in browser-side configuration. They identify the Cognito resources; they do not grant administrative access by themselves. |
| What actually protects `/messages`? | The authenticated Cognito identity and the token validation performed by the API Gateway authorizer. |

---

<a id="security"></a>
## 🛡️ Defense in Depth

The project intentionally uses multiple independent controls.

```text
Internet
   │
   ▼
CloudFront ──► Private S3
   │
   ▼
AWS WAF
   │
   ▼
API Gateway
   │
   ├── POST /submit ──► submit-handler ──► SQS
   │                                      │
   │                                      ▼
   │                              message-processor
   │                                 │      │
   │                                 ▼      ▼
   │                              DynamoDB  SNS
   │
   └── GET /messages
             │
       Cognito Authorizer
             │
             ▼
       get-messages
             │
             ▼
          DynamoDB
```

### Why multiple layers?

No single service solves every problem:

- **CloudFront + OAC** protects the S3 origin from direct public access.
- **WAF** reduces abusive and malicious HTTP traffic.
- **API Gateway** provides the API boundary.
- **Cognito** protects administrative access.
- **IAM** controls what Lambda functions can do.
- **SQS** isolates processing failures from the public request.
- **Spam filtering** reduces unwanted notifications.

This is a practical example of **defense in depth**.

---

<a id="cloudfront"></a>
## 🌍 Private S3 + CloudFront OAC

| Question | Answer |
|---|---|
| Why not make the S3 bucket public? | Public S3 access is unnecessary when CloudFront can serve the site. Keeping the bucket private reduces the number of ways the origin can be accessed. |
| What does OAC do? | Origin Access Control lets CloudFront authenticate when accessing the S3 origin, while the bucket policy can restrict access to the specific CloudFront distribution. |
| Why redirect HTTP to HTTPS? | HTTPS protects the connection between the browser and CloudFront and prevents users from continuing over plain HTTP. |
| Why use CloudFront for a static frontend? | It provides HTTPS delivery, caching, and a clean public entry point while keeping the S3 origin private. |

---

<a id="iam"></a>
## 🔑 IAM & Least Privilege

The Lambda role was designed around the resources the application actually uses.

The policy includes permissions for:

- Writing CloudWatch Logs
- Sending/receiving/deleting SQS messages
- Reading/writing the contact-message table
- Publishing SNS notifications
- Calling `comprehend:DetectSentiment`

### Why least privilege?

If a Lambda function is compromised, excessive IAM permissions increase the potential impact.

The principle is:

> Give a workload only the permissions required to perform its job.

A further production improvement would be to split the shared role into separate execution roles for the three Lambdas and scope wildcard resources such as SNS and Comprehend wherever practical.

---

<a id="cors"></a>
## 🔒 CORS

| Question | Answer |
|---|---|
| Why was `ALLOWED_ORIGIN=*` changed? | A wildcard allows browser requests from any origin. The project has a known frontend origin, so restricting it is a better security posture. |
| Does CORS replace authentication? | No. CORS is a browser security mechanism; it is not an authentication or authorization system. |
| Why restrict both public-facing Lambdas? | Both frontend-facing functions can receive browser requests, so both need consistent origin handling. |

---

<a id="cost"></a>
## 💰 Cost Decisions

### Why delete WAF but keep the other services?

WAF was intentionally treated as a temporary demonstration component because its Web ACL and rules can create ongoing charges even when the demo has little or no traffic.

The project therefore:

1. Created the WAF configuration.
2. Used only the rules needed for the demonstration.
3. Tested the configuration.
4. Captured screenshots.
5. Deleted the Web ACL.

The remaining serverless components are primarily usage-based and suitable for low-volume learning/testing, subject to the account's current Free Tier eligibility and AWS pricing.

### Why avoid the WAF Recommended/Bot Control package?

Bot Control provides additional protection, but the project's purpose is to demonstrate the architecture and security concepts rather than protect a production website with meaningful bot traffic.

For a portfolio demo, the additional fixed/request-based cost does not provide enough practical value to justify keeping it enabled.

### Why On-Demand DynamoDB?

A contact form has low and unpredictable traffic.

On-Demand mode avoids manually estimating provisioned capacity and is a natural fit for workloads where traffic can vary significantly.

---

<a id="improvements"></a>
## 🚀 Possible Improvements

| Improvement | Benefit |
|---|---|
| SQS Dead Letter Queue | Isolates messages that repeatedly fail processing |
| Separate IAM roles | Stronger least-privilege isolation between Lambdas |
| Terraform / CloudFormation | Reproducible infrastructure and easier WAF recreation |
| CloudWatch alarms | Detect Lambda failures and queue buildup |
| Dedicated spam classifier | More specialized spam detection than heuristics |
| Admin pagination | Better performance with many stored messages |
| Admin filtering | Faster review of spam vs legitimate messages |
| Input validation hardening | Better protection against malformed or oversized input |
| Secrets management where needed | Centralized handling of sensitive configuration |

---

## 🎯 Interview Summary

If asked to explain the project in one answer:

> **“I built a serverless contact form on AWS using API Gateway and Lambda, but instead of processing submissions synchronously, I used SQS to decouple intake from background processing. A second Lambda analyzes messages with Amazon Comprehend and keyword heuristics, stores both legitimate and spam messages in DynamoDB, and sends SNS notifications only for legitimate submissions. The admin dashboard is protected by Cognito and API Gateway authorization. The frontend is hosted in a private S3 bucket behind CloudFront with OAC, and I also implemented and tested AWS WAF rate limiting and core rules, then removed the WAF Web ACL afterward to avoid unnecessary ongoing demo costs.”**

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
