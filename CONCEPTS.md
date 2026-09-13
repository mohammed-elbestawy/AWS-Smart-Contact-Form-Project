# 🧠 Smart Contact Form — Concepts & Design Decisions

> The main architectural, security, asynchronous-processing, AI, and cost decisions behind the Smart Contact Form.

## Table of Contents

- [Decoupling & Async Processing](#decoupling--async-processing)
- [AI-Based Spam Detection](#ai-based-spam-detection)
- [Security Decisions](#security-decisions)
- [Cost Decisions](#cost-decisions)

---

## Decoupling & Async Processing

The submission path is intentionally separated from the processing path:

```text
User
  │
  ▼
submit-handler
  │
  ▼
SQS
  │
  ▼
message-processor
  ├── Comprehend
  ├── DynamoDB
  └── SNS
```

The user only needs the submission to be accepted quickly. Sentiment analysis, database writes, and notifications can take longer or fail independently.

Using SQS means the public Lambda does not need to wait for every downstream operation before returning a response.

### Why Standard SQS?

A Standard queue was selected because message ordering is not required for this contact form.

The application benefits more from the high throughput and simple, low-cost queue model than from strict ordering.

### Retry Behavior

When a message is received from SQS, it becomes temporarily invisible to other consumers for the visibility timeout.

If processing fails and the message is not successfully removed, it becomes available again and can be retried.

This gives the processing pipeline basic resilience without requiring the submission request to remain open.

---

## AI-Based Spam Detection

Amazon Comprehend provides managed sentiment analysis without requiring the project to build or operate its own machine-learning infrastructure.

The project does **not** treat sentiment alone as a complete spam classifier.

Instead, spam detection combines:

- Amazon Comprehend sentiment analysis
- Simple keyword heuristics for obvious spam markers

This keeps the implementation lightweight while demonstrating how a managed AI service can be integrated into a serverless workflow.

### Why Store Spam Instead of Rejecting It?

Suspicious messages are stored with an `is_spam` flag rather than being discarded immediately.

This avoids losing legitimate messages because of a false positive and gives the administrator the ability to review what the system classified as spam.

The notification step is where the spam decision becomes operationally important: flagged messages do not notify the owner.

---

## Security Decisions

### Cognito for the Admin Dashboard

The `/messages` endpoint is protected with Amazon Cognito instead of placing a hardcoded password inside the Lambda function or frontend.

The authentication flow is:

```text
Admin
  │
  ▼
Cognito Login
  │
  ▼
Authenticated Request
  │
  ▼
API Gateway Authorizer
  │
  ▼
get-messages Lambda
```

API Gateway can reject unauthenticated requests before they reach the Lambda function.

### Cognito IDs Are Not Passwords

The Cognito User Pool ID and App Client ID may appear in frontend JavaScript because they identify the Cognito application.

They are identifiers, not authentication secrets.

Credentials and tokens must still be handled securely.

### Private S3 + CloudFront OAC

The frontend bucket is kept private.

CloudFront uses Origin Access Control (OAC) to access the bucket, while users access the website through CloudFront over HTTPS.

This avoids exposing the S3 bucket directly to the public internet.

### CORS Restriction

During development, the backend used:

```text
ALLOWED_ORIGIN=*
```

After deployment, this was changed to the actual CloudFront domain.

This reduces the set of browser origins allowed to make cross-origin requests to the API.

---

## Cost Decisions

### AWS WAF

AWS WAF was the main cost-sensitive component.

The AWS WAF Recommended preset can include additional protections such as Bot Control and was estimated at roughly **$58–59 per 10M requests/month** for the configuration considered.

A smaller custom configuration using rate limiting and the AWS-managed Core Rule Set was estimated at roughly **$11 baseline**.

For a portfolio project without production traffic, keeping the Web ACL active would not provide enough value to justify the ongoing cost.

Therefore:

1. The WAF Web ACL was created.
2. The rules were configured.
3. Blocking behavior was tested.
4. Screenshots were captured.
5. The Web ACL was deleted.

This demonstrates the security design while avoiding an unnecessary recurring resource.

### DynamoDB Capacity Mode

DynamoDB uses **On-Demand** capacity.

For a small portfolio application with low and unpredictable traffic, on-demand capacity avoids the need to estimate provisioned read/write capacity in advance.

It is a practical fit for this type of demo workload.

### General Cost Strategy

The project deliberately uses managed serverless services and avoids always-on compute.

The cost-sensitive design principle is:

> Keep the services that are useful for continued learning and testing, and remove resources with significant fixed ongoing charges when they are not needed.

For the WAF specifically, the resource was removed after testing because it does not have a Free Tier.

---

## Design Summary

The final design follows four main principles:

| **Principle** | **Implementation** |
| --- | --- |
| Fast user response | SQS decouples submission from processing |
| Managed intelligence | Amazon Comprehend provides sentiment analysis |
| Defense in depth | Cognito, private S3/OAC, CORS restriction, and tested WAF protection |
| Cost awareness | Serverless services + deletion of the paid WAF resource after testing |

The project is intentionally small, but the architecture demonstrates real AWS patterns that can be expanded into a production system.
