<a id="top"></a>

# 🧠 Design Concepts & Rationale

This file explains **why** each decision was made — the questions most likely to come up in an interview.

## 📋 Quick Navigation

| Topic | Section |
|---|---|
| 📬 | [Decoupling & Async Processing](#decoupling) |
| 🤖 | [AI-Based Spam Detection](#ai) |
| 🛡️ | [Security Decisions](#security) |
| 🌍 | [Cross-Region Considerations](#cross-region) |
| 💰 | [Cost Decisions](#cost) |

---

<a id="decoupling"></a>
## 📬 Decoupling & Async Processing

| Question | Answer |
|---|---|
| Why does `submit-handler` push to SQS instead of processing the message directly? | The user's request only needs a fast acknowledgment. Calling Comprehend, writing to DynamoDB, and publishing to SNS all take time and can fail independently — none of that should block the user's response. |
| Why Standard SQS instead of a FIFO queue? | Message order doesn't matter here. Standard queues are cheaper and have higher throughput, and FIFO's ordering guarantee would be solving a problem this app doesn't have. |
| What happens if `message-processor` fails partway through? | The function doesn't delete the SQS message until it returns successfully, so a failure means the message becomes visible again after the visibility timeout and gets retried automatically. |

---

<a id="ai"></a>
## 🤖 AI-Based Spam Detection

| Question | Answer |
|---|---|
| Why Amazon Comprehend instead of a full custom ML model? | It's a managed, pre-trained API — no training, no infrastructure, and genuinely useful signal for detecting hostile messages without building anything from scratch. |
| Is sentiment analysis alone a reliable spam filter? | No — a negative sentiment doesn't necessarily mean spam, and plenty of spam is neutral or positive in tone. The actual logic combines sentiment with keyword heuristics rather than trusting either signal alone. |
| Why store spam messages instead of just rejecting them at submission time? | Rejecting outright risks losing a legitimate message that was flagged incorrectly. Storing everything and just suppressing the notification means a human can still review borderline cases in the admin dashboard. |
| Why wrap the Comprehend call in try/except? | A missing or temporarily unavailable AI feature shouldn't block the core function of storing a message and notifying the owner. Degrading to keyword-only filtering (sentiment defaults to `NEUTRAL`) keeps the system usable regardless of the AI service's status. |

---

<a id="security"></a>
## 🛡️ Security Decisions

| Question | Answer |
|---|---|
| Why protect `/messages` with a Cognito authorizer instead of a hardcoded password check in the Lambda? | API Gateway rejects unauthenticated requests before any Lambda code runs — the function never has to think about auth, and no secret lives inside application code. |
| Is it a security risk that the Cognito Pool ID and Client ID are visible in the admin page's JavaScript? | No — these identifiers only tell the browser which User Pool to authenticate against. The actual protection is the password check performed by Cognito and the token verification performed by API Gateway. |
| Why use the SPA app client type instead of Traditional web application? | A "Traditional web application" client assumes a server-side backend that can securely store a Client Secret. Browser JavaScript has nowhere secure to keep one, so Cognito rejects the auth flow entirely for that client type. The SPA client type exists specifically for public clients with no secret. |
| Why does `sns:Publish` allow `Resource: "*"` instead of the specific topic ARN? | SNS doesn't support resource-level permissions for `Publish` the way S3 and DynamoDB support scoping to a specific bucket or table. This is a service limitation, not a design choice. |
| Why does CORS need to be configured in two places (Lambda and API Gateway)? | The Lambda's `Access-Control-Allow-Origin` header only applies to the actual response it returns. The browser's preflight `OPTIONS` request never reaches the Lambda at all — API Gateway answers it directly using its own configured headers. Both must agree, or the browser blocks the request before it's even sent. |

---

<a id="cross-region"></a>
## 🌍 Cross-Region Considerations

| Question | Answer |
|---|---|
| Why does the Comprehend client target `eu-west-1` when everything else runs in `eu-north-1`? | Comprehend isn't offered in every AWS region, and `eu-north-1` is one where it's unavailable. A Lambda function can call any AWS service in any region via the SDK — cross-region calls add negligible latency here, and redeploying the entire stack elsewhere just for one dependency would be a much larger change than necessary. |
| Why test the WAF rate limit in batches instead of one large burst? | Rate-based rules measure request rate over a rolling window and need a short window (up to ~30s) to detect an elevated rate. An instant burst can complete before the rule reacts, which doesn't reflect how the rule behaves against real traffic patterns like a script hammering an endpoint over time. |

---

<a id="cost"></a>
## 💰 Cost Decisions

| Question | Answer |
|---|---|
| Why terminate the WAF Web ACL when not actively demoing? | It's the only component in this stack with a real fixed cost regardless of traffic — a Web ACL and its rules bill hourly whether or not any requests come through. Every other service here (Lambda, SQS, DynamoDB, SNS, Cognito, API Gateway, S3, CloudFront) has effectively zero idle cost. |
| Why "You build it" instead of the "Recommended" WAF package? | Bot Control alone adds a fixed $10/month subscription plus per-request fees, pushing the estimated cost from ~$11 to ~$58-59 per 10M requests/month — for a demo project with no real bot traffic to defend against. |
| Why On-Demand DynamoDB instead of Provisioned capacity? | Traffic for a contact form is low and unpredictable — On-Demand charges per actual request with no capacity planning, avoiding both throttling risk and the cost of over-provisioning. |

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
