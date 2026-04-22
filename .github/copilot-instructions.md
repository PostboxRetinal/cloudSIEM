---
applyTo: "**"
---

# CloudSIEM Copilot Instructions

## Project scope
- This repository is an academic SIEM project built around `Elasticsearch`, `Logstash`, `Kibana`, `Filebeat` and/or `Metricbeat`, `Docker Compose`, Python log generators, and optional `Wazuh`.
- Follow the project scope, requirements, deliverables, and acceptance criteria defined in [`README.md`](../README.md).

## Source of truth
- Treat `README.md` as the primary source of truth for architecture, requirements `R8.1` to `R8.8`, deliverables, and expected repository structure.
- Do not claim that pipelines, dashboards, alerts, playbooks, screenshots, or deployments already exist unless the corresponding files or configurations are present in the repository.

## Communication style
- Use clear, direct, and concise language.
- Do not use emojis.
- Prefer factual statements over promotional or decorative wording.
- Keep explanations practical and focused on what exists, what is missing, and what should be implemented next.

## Documentation rules
- Write project documentation in Spanish.
- Keep code, configuration keys, service names, index names, and technical identifiers in English.
- Prefer short sections, clean Markdown structure, and tables when they improve readability.
- Do not present planned work as completed work.

## Implementation guidance
- Prefer `Docker Compose` as the default deployment target unless a task explicitly requires Kubernetes.
- Align ingested events to `ECS` whenever possible.
- For `Logstash` pipelines, prefer explicit parsing and enrichment with `grok`, `mutate`, and `geoip`.
- Route malformed logs to a dedicated error index and preserve the rejection reason.
- Keep changes minimal, practical, and consistent with the current repository structure.

## Security and detection requirements
- Preserve the required detections: SSH brute force, port scanning, repeated `404` errors, off-hours login, and access to sensitive paths.
- Preserve the required attack simulations: brute force, `nmap` scanning, and SQL injection reflected in logs.
- Distinguish clearly between executive dashboards and operational dashboards.
- Incident response playbooks must include investigation, containment, eradication, and lessons learned.
