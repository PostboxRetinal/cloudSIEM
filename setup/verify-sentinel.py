#!/usr/bin/env python3
"""
verify-sentinel.py
Verifies Microsoft Sentinel resources and recent CloudSIEM ingestion through Azure CLI.
"""

import argparse
import json
import subprocess
import sys


def run_az(args, text_output=False):
    command = ["az", *args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stderr.strip()}")
    output = result.stdout.strip()
    if text_output:
        return output
    if not output:
        return None
    return json.loads(output)


def first_result_cell(query_payload):
    tables = query_payload.get("tables", []) if isinstance(query_payload, dict) else []
    if not tables or not tables[0].get("rows"):
        return None
    first_row = tables[0]["rows"][0]
    return first_row[0] if first_row else None


def query_workspace(workspace_id, query):
    return run_az(
        [
            "monitor",
            "log-analytics",
            "query",
            "--workspace",
            workspace_id,
            "--analytics-query",
            query,
            "--output",
            "json",
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Verify CloudSIEM Microsoft Sentinel integration")
    parser.add_argument("--resource-group", default="rg-cloudsiem-sentinel")
    parser.add_argument("--workspace", default="law-cloudsiem")
    parser.add_argument("--table", default="CloudSIEM_CL")
    parser.add_argument("--subscription", default=None)
    args = parser.parse_args()

    try:
        if args.subscription:
            run_az(["account", "set", "--subscription", args.subscription], text_output=True)

        subscription_id = run_az(["account", "show", "--query", "id", "--output", "tsv"], text_output=True)
        workspace_id = run_az(
            [
                "monitor",
                "log-analytics",
                "workspace",
                "show",
                "--resource-group",
                args.resource_group,
                "--workspace-name",
                args.workspace,
                "--query",
                "customerId",
                "--output",
                "tsv",
            ],
            text_output=True,
        )

        count_payload = query_workspace(workspace_id, f"{args.table} | summarize Count=count()")
        total_count = first_result_cell(count_payload)

        recent_payload = query_workspace(
            workspace_id,
            f"{args.table} | where TimeGenerated > ago(30m) | summarize Count=count()",
        )
        recent_count = first_result_cell(recent_payload)

        rules_uri = (
            f"https://management.azure.com/subscriptions/{subscription_id}"
            f"/resourceGroups/{args.resource_group}"
            f"/providers/Microsoft.OperationalInsights/workspaces/{args.workspace}"
            "/providers/Microsoft.SecurityInsights/alertRules"
            "?api-version=2023-02-01-preview"
        )
        rules_payload = run_az(["rest", "--method", "get", "--uri", rules_uri, "--output", "json"])
        cloudsiem_rules = [
            rule for rule in rules_payload.get("value", [])
            if rule.get("properties", {}).get("displayName", "").startswith("CloudSIEM -")
        ]

        print("Microsoft Sentinel verification")
        print(f"  Subscription: {subscription_id}")
        print(f"  Workspace:    {args.workspace} ({workspace_id})")
        print(f"  Table:        {args.table}")
        print(f"  Total rows:   {total_count}")
        print(f"  Last 30 min:  {recent_count}")
        print(f"  Rules:        {len(cloudsiem_rules)} CloudSIEM rules")

        if total_count is None:
            print("ERROR: no query result returned for the CloudSIEM table", file=sys.stderr)
            return 1
        if len(cloudsiem_rules) < 5:
            print("ERROR: expected at least 5 CloudSIEM analytics rules", file=sys.stderr)
            return 1
    except Exception as exc:  # noqa: BLE001 - CLI diagnostics should be shown as-is
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
