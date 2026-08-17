# Development Environment: Requirements and Technical Rationale

**Selecting the right AWS platform to develop and validate the BU Editions of the MapSnap, AutoPDF and OnBase DNA toolset**

| Field | Value |
|---|---|
| Prepared by | Renne Santiago |
| Department | [Department / Team] |
| Date | 2026-08-11 |
| Document type | Technical justification - supports the accompanying Business Request |
| Audience | Cloud Engineering, Enterprise Architecture, Information Security, Sponsoring Manager |
| Status | For review |

---

## Executive summary

**The recommendation is Amazon EC2, not Amazon WorkSpaces.**

- The tools being developed are server applications that expose HTTP services other people must reach to review. WorkSpaces is a single-user virtual desktop; hosting a service on it is outside its intended use.
- The roadmap is containerisation (Docker) and later orchestration (Kubernetes). **Amazon WorkSpaces does not support nested virtualization and cannot run a container engine locally.**
- The only supported container option on WorkSpaces routes workloads to infrastructure managed by a third party **outside BU's VPC** - not an acceptable data path for OnBase and Jenzabar data.
- EC2 supports every phase of the roadmap on one instance, **provided the correct instance family is chosen at the outset**. This costs nothing extra today and prevents an expensive rebuild later.
- With scheduled stop/start, the cost difference against a WorkSpaces bundle is modest.

## The decisive constraint

Nested virtualization is the ability of a virtual machine to run another virtualized workload inside itself. Docker Desktop and WSL2 require it on Windows.

- Amazon WorkSpaces does not support it, for Windows or Linux bundles.
- Docker's answer, Docker Desktop for Amazon WorkSpaces, does not run the engine locally - it forwards workloads to a Docker-managed instance outside BU.
- **Choosing WorkSpaces therefore means choosing to give up containerisation, or to accept a data path that leaves BU's VPC.**

## The instance family is a one-way door

Until February 2026 AWS offered nested virtualization only on bare-metal EC2. It is now available on virtual instances, but **only on the C8i, M8i and R8i families**. Older families such as m6i and m7i cannot gain it.

> If this request is fulfilled with an m6i or m7i instance, Windows containers, WSL2 and Docker Desktop are permanently unavailable on that instance. Specifying **m8i** now costs approximately the same and keeps every option open.
>
> Fallback: if BU cannot supply m8i, choose **Linux** as the OS - Linux containers run natively and need no nested virtualization.

## Phased roadmap

| Phase | What happens | What the environment must provide |
|---|---|---|
| 0 - Now | Tools run directly as Python services | Compute, storage, database routes, internal HTTP access |
| 1 - Containerise | Tools packaged as images, run with Compose | A local container engine (m8i or Linux) |
| 2 - Registry | Images versioned and pushed | ECR repository plus IAM role |
| 3 - Local orchestration | Validated with k3s or kind | More memory; resize to m8i.2xlarge |
| 4 - Managed orchestration | Deploy to EKS | Cluster credentials; no instance change |

No phase requires a different machine.

## Full document

The complete rationale - option analysis, recommended configuration with per-item justification, network and data access requirements, security posture, cost profile, risk register, success criteria and fallback position - is in the Word version alongside this file.

---

*Generated 2026-08-11.*
