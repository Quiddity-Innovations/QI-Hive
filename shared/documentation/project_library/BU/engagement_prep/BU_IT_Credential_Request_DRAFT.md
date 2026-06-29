# DRAFT — OnBase Test-Instance Credential Request
*Internal draft for Renne. Do NOT send until a BU contact and the engagement are confirmed. Fill the [bracketed] fields.*

---

**To:** [BU IT / OnBase administrator — name, email]
**Cc:** [BU REST POC team lead]
**From:** Renne Santiago, Quiddity Innovations
**Subject:** Credential request — shared OnBase test instance (CogniBase + REST POC alignment)

Hi [name],

To move the OnBase work forward without either team duplicating effort, I'd like to request a single set of API credentials that **both** the BU REST POC team and CogniBase can use against the same OnBase **test/non-prod** instance. This keeps our work aligned (same upstream Hyland API) and avoids two parallel credential requests.

**What I'm asking IT to issue (against the test instance only):**

| Item | Detail |
|---|---|
| Identity service URL | `https://[onbase-host]/identityservice/connect/token` |
| `client_id` | issued by IT |
| `client_secret` | issued by IT |
| `tenant` | OnBase tenant name |
| `grant_type` | `password` (PKCE acceptable) |
| `scope` | `evolution` |
| Service account | read-mostly account scoped to the test instance |
| API base URLs | Document Management + Workflow + Administration REST endpoints |

**Scope & safety:**
- **Test/non-prod only** to start. No production access requested at this stage.
- CogniBase is **read-mostly**; no writes to OnBase configuration or documents.
- Regulated data stays on-machine — CogniBase runs locally with a default `local_only` policy; nothing is shipped to any cloud LLM unless an administrator explicitly raises the policy with a recorded agreement.
- We will log rate-limit / field-shape observations and share them with the REST POC team.

**Who uses these:** the BU REST POC team for their plumbing; CogniBase for the OnBase domain layer (DocType modelling, Custom Query semantics, Query Federator) on top.

Happy to fill out whatever IT request form you use, or jump on a short call to scope it. What's the right channel and is there a non-prod OnBase instance we should target?

Thanks,
Renne
Quiddity Innovations · quiddityinnovations.com

---
*Reference: the auth flow and SDK materials are in `C:\CogniBase\API\` (IDP token-generation doc, Unity API SDK, REST API lab guide). Coordination model: `C:\CogniBase\DESIGN\COORDINATION_BU_TEAM.md`.*
