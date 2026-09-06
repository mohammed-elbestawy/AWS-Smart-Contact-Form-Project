<a id="top"></a>

# 🧠 Design Concepts & Rationale

This file explains **why** each decision was made — the questions most likely to come up in an interview.

## 📋 Quick Navigation

| Topic | Section |
|---|---|
| 📬 | [Decoupling & Async Processing](#decoupling) |
| 🤖 | [AI-Based Spam Detection](#ai) |
| 🛡️ | [Security Decisions](#security) |
| 💰 | [Cost Decisions](#cost) |

---

<a id="decoupling"></a>
## 📬 Decoupling & Async Processing

| Question | Answer |
|---|---|
| Why does `submit-handler` push to SQS instead of processing the message directly? | The user's request only needs a fast acknowledgment. Calling Comprehend, writing to DynamoDB, and publishing to SNS all take time and can fail independently — none of that should block the user's response. |
| Why Standard SQS instead of a FIFO queue? | Message order doesn't matter here — two contact form submissions have no relationship to each other. Standard queues are cheaper and have higher throughput, and FIFO's ordering guarantee would be solving a problem this app doesn't have. |
| What happens if `message-processor` fails partway through? | Since the function doesn't delete the SQS message until it returns successfully, a failure means the message becomes visible again after the visibility timeout and gets retried automatically — no message is silently lost. |

---

<a id="ai"></a>
## 🤖 AI-Based Spam Detection

| Question | Answer |
|---|---|
| Why Amazon Comprehend instead of a full custom ML model? | Comprehend's sentiment analysis is a managed, pre-trained API — no model training, no infrastructure, and it's genuinely useful signal for detecting hostile or abusive messages without building anything from scratch. |
| Is sentiment analysis alone a reliable spam filter? | No — a negative sentiment doesn't necessarily mean spam, and plenty of spam is neutral or positive in tone ("congratulations, you won..."). That's why the actual logic combines sentiment with keyword heuristics rather than trusting either signal alone. |
| Why store spam messages instead of just rejecting them at submission time? | Rejecting outright risks losing a legitimate message that was flagged incorrectly (a false positive). Storing everything and just suppressing the notification means a human can still review borderline cases in the admin dashboard. |

---

<a id="security"></a>
## 🛡️ Security Decisions

| Question | Answer |
|---|---|
| Why protect `/messages` with a Cognito authorizer instead of a hardcoded password check in the Lambda? | API Gateway rejects unauthenticated requests before any Lambda code even runs — the function never has to think about auth at all. A password check inside the function would mean the function itself is a bigger attack surface, and secrets would need to live somewhere in the code or environment. |
| Is it a security risk that the Cognito Pool ID and Client ID are visible in the admin page's JavaScript? | No — these identifiers only tell the browser which User Pool to authenticate against. They carry no special privilege by themselves; the actual protection is the password check performed by Cognito and the token verification performed by API Gateway. |
| Why keep the same CloudFront + OAC + private S3 pattern from the previous project instead of trying something different? | Reusing a proven, already-justified security pattern is a legitimate engineering choice — consistency across projects also makes the portfolio read as a coherent body of work rather than unrelated one-off experiments. |

---

<a id="cost"></a>
## 💰 Cost Decisions

| Question | Answer |
|---|---|
| Why was AWS WAF deleted right after testing, unlike the always-on services in this stack? | WAF is the only component in this architecture with real fixed costs regardless of traffic — a Web ACL and its rules bill hourly whether or not any requests come through. Every other service here (Lambda, SQS, DynamoDB, SNS, Cognito, API Gateway, S3, CloudFront) has effectively zero idle cost, so there's no equivalent reason to tear them down. |
| Why not just use the "Recommended" WAF rule package since it offers more protection? | Bot Control alone adds a fixed $10/month subscription plus per-request fees, pushing the estimated cost from ~$11 to ~$58-59 per 10M requests/month — for a demo project with no real bot traffic to defend against. The extra coverage has no practical value here, so the cost isn't justified. |
| Why On-Demand DynamoDB instead of Provisioned capacity? | Traffic for a contact form is low and unpredictable — On-Demand charges per actual request with no capacity planning, avoiding both the risk of throttling real users and the cost of over-provisioning for traffic that may never arrive. |

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
