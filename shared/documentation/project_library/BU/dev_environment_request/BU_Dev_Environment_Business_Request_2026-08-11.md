# Business Request: Development Environment

**Request for one AWS EC2 development instance to build and validate the BU Editions of the MapSnap, AutoPDF and OnBase DNA toolset**

| Field | Value |
|---|---|
| Requestor | Renne Santiago |
| Department | [Department / Team] |
| Sponsor / approver | [Sponsoring Manager / Director] |
| Cost centre / project code | [Cost Center / Project Code] |
| Date submitted | 2026-08-11 |
| Date required by | [Target date] |
| Estimated recurring cost | Approx. USD 115 - 140 per month with scheduled stop/start |

---

## Request in one paragraph

One Amazon EC2 instance, hosted in a BU-managed AWS account and network, to develop and validate BU-specific editions of tools that read institutional systems of record - principally Hyland OnBase and Jenzabar - and turn undocumented configuration into usable documentation, mappings and searchable knowledge. The environment must sit inside BU's network so institutional data never leaves it, and must be able to host a web service colleagues can open in a browser to review the output.

## Items requested

| # | Item | Specification | Priority |
|---|---|---|---|
| 1 | EC2 instance | m8i.xlarge (4 vCPU / 16 GiB). **m8i family specifically** - older families cannot support containers on Windows | MUST |
| 2 | Operating system | Windows Server 2022, or Ubuntu 22.04 / 24.04 LTS | MUST |
| 3 | OS volume | 100 GB gp3, encrypted | MUST |
| 4 | Separate data volume | 300 GB gp3, encrypted, mounted separately from the OS disk | MUST |
| 5 | Local administrator rights | On this instance only | MUST |
| 6 | Instance control | Stop / start / reboot without raising a ticket | MUST |
| 7 | Snapshot rights | EBS snapshots and machine images | SHOULD |
| 8 | Inbound network access | HTTP on selected ports from approved internal BU subnets. No public IP, no inbound internet | MUST |
| 9 | Administrative access | RDP or SSH from BU management network or VPN | MUST |
| 10 | Database connectivity | Route plus read-only credentials to OnBase and Jenzabar. Non-production preferred | MUST |
| 11 | Outbound internet | Package repositories, source control, approved AI endpoints, via BU proxy | MUST |
| 12 | Proxy certificate detail | Confirmation of TLS inspection, and the root certificate if in use | MUST |
| 13 | IAM instance profile | Role-based access instead of long-lived keys | SHOULD |
| 14 | Automated backup | Daily snapshot, short retention | SHOULD |
| 15 | Container registry | Push/pull in a BU ECR repository | FUTURE |
| 16 | Kubernetes access | Managed cluster credentials when the work reaches that stage | FUTURE |
| 17 | Resize headroom | Agreement in principle to move to m8i.2xlarge | SHOULD |
| 18 | Tagging | Owner, purpose, cost centre, review date | MUST |

## Estimated cost

| Line | Basis | Approx. monthly |
|---|---|---|
| Compute | m8i.xlarge, business hours with scheduled stop/start | USD 80 - 100 |
| Storage | 400 GB gp3, billed running or stopped | USD 32 |
| Snapshots | Short retention | USD 3 - 8 |
| **Total expected** | With cost controls applied | **USD 115 - 140** |
| Total if continuous | Comparison only; not requested | USD 285 - 340 |

## What is not being requested

- No public IP address and no internet-facing service
- No write access to any system of record - all credentials read-only
- No production data copied outside the instance
- No software licences
- No additional user accounts
- No permanent commitment - BU-owned, terminable at any point

## Questions to resolve before provisioning

1. Is the **m8i** family available in BU's approved catalogue? If not, the OS should be Linux rather than Windows.
2. Does BU's outbound proxy perform **TLS inspection**, and where is the root certificate obtained?
3. Will **local administrator rights** on this instance be granted?
4. Are **non-production copies** of OnBase and Jenzabar available, or must work use read-only credentials against production?

---

*Generated 2026-08-11. Full version with approval block and consequence analysis in the Word document alongside this file.*
