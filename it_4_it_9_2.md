# IT4IT 9.2.1 Configuration Functional Component – DocType Mapping

> **Purpose**: Provide a complete, Confluence‑ready mapping from the Word file’s Frappe DocTypes to the IT4IT **9.2.1 Configuration Functional Component** and **9.2.1.1 Actual Product Instance** requirements.
>
> **Language**: English (per your preference).
>
> **Attachments**: See the CSV/XLSX links at the bottom.

---

## 1) Executive Summary
This document maps existing DocTypes (Server, Virtual Machine, Storage Plan, Site Domain, Application Instance, etc.) to IT4IT 9.2.1 functional criteria and to the 9.2.1.1 **Actual Product Instance** (API) data object. It also identifies three proposed DocTypes (**Runbook**, **Service Contract**, **Problem**) to achieve a literal 100% alignment with the standard’s relationship set.

---

## 2) Scope
- Standard: **IT4IT v9 – Section 9.2.1 & 9.2.1.1**
- Platform: **Frappe/ERPNext DocTypes** (from the provided Word file)
- Output artifacts: CSV (detailed one‑row‑per‑relationship/role) and XLSX versions

---

## 3) Glossary (selected)
- **Actual Product Instance (API)**: The realized deployment of a Desired Product Instance (DPI) including all CIs, integrations and dependencies.
- **CI (Configuration Item)**: A component under configuration control (e.g., Server, VM, Disk, Domain, Alert Rule).
- **Service Monitor**: Monitoring/alerting definition applied to Actual Product Instances.

---

## 4) IT4IT 9.2.1 – Functional Criteria Mapping

**How to read**: Each row ties an IT4IT criterion to concrete DocTypes and the key relationships that implement it.

| IT4IT Functional Criterion | DocTypes Implementing | Key Relationships | Notes |
|---|---|---|---|
| System of record for all Actual Product Instances & relationships | **Server**, **Virtual Machine**, **Storage Plan**, **Disk/Volume**, **Site Domain**, **Application Instance** | Server ↔ VM (1:n), Server/VM ↔ Storage Plan (n:1), Site Domain ↔ Server (n:m) | Inventory + relationship graph for compute, storage, and routing |
| Manage lifecycle of the Actual Product Instance | **Server**, **Virtual Machine**, **Backup/Snapshot** | Server/VM ↔ Backup (1:n) | Status/history, backup/restore checkpoints |
| Create Actual Product Instance(s) from Desired Product Instance | **Release Group**, **Release Group Server**, **Deploy Candidate** | Release Group → Deploy Candidate (1:n); Release Group Server → Server (n:m) | Implements DPI→API traceability |
| Serve as data store for realization in production | **Server**, **VM**, **Application Instance**, **Press Settings (CI)** | App Instance ↔ Press Settings (1:n) | Runtime config/parameters as CIs |
| Impact analysis on proposed changes | **Resource Tag**, **Log Server** | Tag ↔ Server/VM/Disk/Network (n:m); Log Server ← Server/VM (n:m) | Enables dependency/blast‑radius graphs and change correlation |
| Business impact of Incident | **Incident** (links to instances) | Incident ↔ Server/VM/App Instance (n:m) | Prioritization by affected services |
| Business impact of Event | **Webhook Event** / Events | Event ↔ Server/VM/App Instance (n:m) | Event→impact mapping |
| May be populated by service discovery | **Agent Job**, **Agent Step**, **Agent Type** | Agent Job → Server/VM (n:m) | Auto‑populate/refresh CMDB entries |

---

## 5) IT4IT 9.2.1.1 – Actual Product Instance (API) Data Object

### 5.1 API Purpose
Represents the realized deployment of a specific Desired Product Instance including the CIs that compose it.

### 5.2 API Key Attributes → DocType/Field Mapping

| Attribute | Implemented In | Notes |
|---|---|---|
| **Id** | Server / VM / Application Instance (primary keys) | Unique identifier of the Actual Product Instance element |
| **Name** | Server / VM / Application Instance | Human‑readable name |
| **Type** | Server.Type / VM.Type / App Instance.Type | e.g., infrastructure service, customer‑facing service |
| **Configuration Items (CI model)** | Press Settings (CI), Storage Plan, Disk/Volume, Prometheus Alert Rules | CI graph for parameters, storage, monitors |
| **Create Time** | Server/VM/App Instance (created_on) | Creation timestamps |
| **Last Modified Time** | Server/VM/App Instance (modified_on) | Significant change timestamps |
| **Location** | Server/VM (Location); Domain (logical) | Physical/logical location |

### 5.3 API Relationships – Implementation Status

| Required Relationship (IT4IT) | How Implemented (DocTypes) | Cardinality | Status |
|---|---|---:|---|
| **Desired Product Instance → Actual Product Instance** | Release Group → Deploy Candidate → Release Group Server → Server/VM | 1:1 (per DPI to its realized API) | ✅ Implemented via deployment chain |
| **Problem ↔ Actual Product Instance** | **Problem (Proposed)** ↔ Server/VM/App Instance | n:m | 🔶 Proposed (add DocType + M:N links) |
| **Runbook ↔ Actual Product Instance** | **Runbook (Proposed)** ↔ Server/VM/App Instance | n:m | 🔶 Proposed (operational SOP linkage) |
| **Incident ↔ Actual Product Instance** | Incident ↔ Server/VM/App Instance | n:m | ✅ Implemented |
| **Event ↔ Actual Product Instance** | Webhook Event ↔ Server/VM/App Instance | n:m | ✅ Implemented |
| **Actual Product Instance → Service Contract** | Server/VM/App Instance → **Service Contract (Proposed)** | 1:n | 🔶 Proposed (contract/OLA mapping) |
| **Service Monitor → Actual Product Instance** | Prometheus Alert Rule Cluster → Server/VM/App Instance | 1:n | ✅ Implemented |
| **Actual Product Instance ↔ Actual Product Instance** | Server ↔ VM; Site Domain ↔ Server; App Instance ↔ DB/Server (as applicable) | n:m | ✅ Implemented (extend as needed) |

> **Composite Definition**: In practice, we treat **Actual Product Instance** as a composite object composed of Server, VM, Application Instance, and Site Domain, plus their attached CIs (Press Settings, Storage Plan, Disks, Monitors, Tags).

---

## 6) Gaps & Proposed DocTypes (to reach literal 100% parity)

| Proposed DocType | Why | Key Fields | Links |
|---|---|---|---|
| **Runbook** | Map operational SOPs to APIs | Title, Steps (rich text), Owner, Version | n:m to Server/VM/App Instance |
| **Service Contract** | Tie SLAs/OLAs/commercials to APIs | Contract Id, Provider, SLA targets, Term dates | 1:n from API elements |
| **Problem** | Separate root‑cause record from Incident | Problem Id, Category, Known Error, Workaround | n:m to API elements |

> These are included in the CSV/XLSX as **(Proposed)** rows so you can implement them when ready without breaking the mapping.

---

## 7) Field/Link Additions (if not already present)
- **Incident**: add M:N link tables to Server, VM, Application Instance.
- **Webhook Event**: add M:N link tables to Server, VM, Application Instance.
- **Prometheus Alert Rule Cluster**: add 1:n links to Server/VM/App Instance.
- **Resource Tag**: ensure n:m across Server/VM/Disk/Network for impact graphs.
- **Server/VM/Application Instance**: ensure **Location**, **Create/Modified** timestamps are visible.

---

## 8) Import/Publish Checklist (Confluence)
1. Upload this page content to Confluence (Markdown paste or attachment import).
2. Attach the CSV/XLSX to the page (links below) and reference them in a "Related Files" section.
3. (Optional) Add Confluence labels: `it4it`, `configuration`, `cmdb`, `mapping`.
4. (Optional) Create child pages for **Runbook**, **Service Contract**, **Problem** design docs.

---

## 9) Related Files (attach to this Confluence page)
- **CSV (detailed)**: `IT4IT_Config_Component_Mapping.csv`
- **Excel (detailed)**: `IT4IT_Config_Component_Mapping.xlsx`

> You can use the Excel to filter by Role/Relation and copy rows directly into JIRA/Change templates.

---

## 10) Appendix – One‑row‑per‑relationship/role examples
The attached CSV/XLSX contain the full list. Examples:

```
Server,System of record for Actual Product Instances,Linked to Virtual Machine (1:n); Linked to Storage Plan (n:1),Stores configuration and lifecycle data
Virtual Machine,Actual Product Instance,Hosted on Server (n:1); Uses Storage Plan (n:1),Represents realized compute node
Release Group,Desired→Actual linkage,Linked to Deploy Candidate (1:n),Bridges desired to actual deployment
Incident,Incident↔Actual Product Instance,Linked to Server/VM (n:m),Tracks incidents affecting actual instances
Prometheus Alert Rule Cluster,Service monitor,Monitors Server/VM/App Instance (1:n),Provides health signals and thresholds
Runbook (Proposed),Operational procedure linkage,Linked to Server/VM/App Instance (n:m),Step‑by‑step remediation
```

---

**Owner**: <your team>

**Last Updated**: <fill on publish>

