# AGENTS.md

## Repo Shape
- Read `README.md` and `.github/copilot-instructions.md` first; they define the project scope, required detections, and documentation language.
- The stack lives at the repository root; do not assume a nested `siem-elk/` directory.
- `develop` is the working branch; `main` is stable and PR-only.

## Run The Stack
- Use explicit Compose files from the repository root: `podman-compose -f docker-compose.yml -f docker-compose-podman.yml up --build`.
- Stop the stack with the same file order: `podman-compose -f docker-compose.yml -f docker-compose-podman.yml down`.
- `docker-compose.yml` is the universal base; `docker-compose-podman.yml` is the Linux + Podman override and owns SELinux relabeling.
- The Podman override maps `$XDG_RUNTIME_DIR/podman/podman.sock` to `/var/run/docker.sock` for Filebeat metadata enrichment.
- The cluster bootstrap takes about 90 seconds before health checks are meaningful.

## Verify
- From the repository root: `bash setup/verify-cluster.sh`, `python3 setup/check-cluster-health.py`, `python3 setup/verify-ecs-mapping.py`.
- From the repository root: `bash logstash/test-pipeline.sh`.
- Run Filebeat config checks with Podman, not Docker:
  `podman run --rm --user 0 -e ELASTIC_PASSWORD=test -v "$PWD/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro,Z" docker.elastic.co/beats/filebeat:9.3.3 filebeat test config -e -c /usr/share/filebeat/filebeat.yml`

## Filebeat And Logs
- Filebeat configs should stay on `filestream`; use `parsers` for multiline and container parsing.
- Do not reintroduce `type: log` or `type: container` in Filebeat configs.
- `logs/` contains live sample inputs for Filebeat.
- `setup/generate-test-logs.py` writes directly to log files; its defaults point at `/var/log/...`, so override paths before using it on the host.

## Scripts With Relative Paths
- `setup/import-rules.py` has brittle relative-path defaults; check `RULES_DIR` and `CACERT` before invoking it.
- Several helper scripts read `.env` from the current directory, so run them from the directory shown above.

## Coding Approach
- Think before coding: state assumptions explicitly. If something is unclear or has multiple plausible interpretations, ask instead of guessing.
- Keep solutions minimal: implement only what was requested. Avoid speculative abstractions, configurability, or error handling for impossible scenarios.
- Make surgical changes: touch only what is necessary, match existing style, and do not refactor unrelated code or comments. Remove only unused imports, variables, or functions created by your own changes.
- Be goal-driven: for multi-step work, outline a brief plan and define how each step will be verified.

## Content Rules
- Keep docs in Spanish and code/config identifiers in English.
- Do not use emojis under any circumstance.
- Preserve the 5 required detections, 3 attack simulations, and 2 response playbooks when editing project scope docs.
