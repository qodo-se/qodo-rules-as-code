#!/usr/bin/env python3
"""Sync rules/*.yaml to Qodo Review Standards through the qodo CLI.

Create-or-update by exact rule name. Never deletes or deactivates: removing a
file leaves its rule live in Qodo (retire it in the portal or with
`qodo rules set-state`), and changing a file's `name:` creates a new rule and
orphans the old one.

Environment:
  QODO_BIN   path to the qodo CLI (default: "qodo")
  DRY_RUN    "1" to report what would change without calling the API
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

QODO = os.environ.get("QODO_BIN", "qodo")
DRY_RUN = os.environ.get("DRY_RUN", "").lower() not in ("", "0", "false", "no")
RULES_DIR = Path(__file__).resolve().parent.parent / "rules"

REQUIRED = ("name", "category", "severity", "content")
# Fields this repo manages; anything else in the YAML is rejected to catch typos.
KNOWN = {
    "name", "category", "severity", "content",
    "good_examples", "bad_examples", "scopes",
}
SEVERITIES = {"error", "warning", "recommendation"}
# Keep in step with `qodo rules metadata` for your workspace — the API rejects
# a category it doesn't know, and validation runs offline so it can't ask.
CATEGORIES = {
    "Accessibility", "Architecture", "Compliance", "Correctness",
    "Maintainability", "Observability", "Performance", "Quality",
    "Reliability", "Security", "Testability",
}
MAX_NAME = 128
MAX_SCOPES = 25
# Rules this repo may overwrite. A rule Qodo derived from a repo file
# (AGENTS.md) or imported from its library is managed at that source, not here.
OWNED_SOURCE_TYPES = {"User"}
# Rule files shipped as examples carry this marker on their first line. A real
# sync refuses to run while any remain, because Qodo rules cannot be deleted
# once created — only deactivated. Delete the file, or drop the marker line to
# adopt the rule as your own.
EXAMPLE_MARKER = "# qodo-rules-as-code:example"


def qodo(*argv):
    proc = subprocess.run(
        [QODO, *argv, "--json"], capture_output=True, text=True, timeout=120
    )
    # Tool errors come back as a JSON envelope on stdout with non-zero exit.
    line = next((l for l in proc.stdout.splitlines() if l.lstrip().startswith("{")), "")
    payload = json.loads(line) if line else {}
    if proc.returncode != 0:
        raise RuntimeError(payload.get("error") or proc.stderr.strip() or "qodo failed")
    return payload


def parse_scopes(value):
    """[] (or absent) means the universal scope '/'."""
    if value is None:
        return []
    if isinstance(value, str):
        raise ValueError("scopes must be a YAML list, not a string")
    if not isinstance(value, list):
        raise ValueError("scopes must be a YAML list of repository paths")
    for scope in value:
        if not isinstance(scope, str) or not scope.startswith("/") or not scope.endswith("/"):
            raise ValueError(
                f"scope {scope!r} must be a path starting and ending with '/', "
                "e.g. '/owner/repo/' or '/owner/repo/src/module/'"
            )
    if len(value) > MAX_SCOPES:
        raise ValueError(f"at most {MAX_SCOPES} scopes per rule, got {len(value)}")
    if "/" in value and len(value) > 1:
        raise ValueError("scope '/' is already universal — drop the others, or omit scopes")
    return value


def load_rule(path):
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict):
        raise ValueError("not a YAML mapping")
    unknown = set(doc) - KNOWN
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    missing = [f for f in REQUIRED if not doc.get(f)]
    if missing:
        raise ValueError(f"missing fields: {missing}")
    # Presence isn't enough: a YAML list or number here passes the PR check and
    # then breaks the sync after merge (.rstrip() / subprocess argv).
    for field in ("name", "category", "severity", "content", "good_examples", "bad_examples"):
        if field in doc and doc[field] is not None and not isinstance(doc[field], str):
            raise ValueError(f"{field} must be a string, got {type(doc[field]).__name__}")
    if doc["severity"] not in SEVERITIES:
        raise ValueError(f"severity must be one of {sorted(SEVERITIES)}")
    if doc["category"] not in CATEGORIES:
        raise ValueError(
            f"category {doc['category']!r} is not a workspace category "
            f"(one of {sorted(CATEGORIES)})"
        )
    if len(doc["name"]) > MAX_NAME:
        raise ValueError(f"name exceeds {MAX_NAME} chars")
    doc.setdefault("good_examples", "")
    doc.setdefault("bad_examples", "")
    doc["scopes"] = parse_scopes(doc.get("scopes"))
    return doc


def find_existing(name):
    # --name-contains is a substring match, so a common name can match more than
    # one page; read every page before concluding the rule doesn't exist.
    page_no = 1
    while True:
        page = qodo("rules", "list", "--name-contains", name,
                    "--page-size", "100", "--page", str(page_no))
        rules = page.get("rules", [])
        match = next((r for r in rules if r["name"] == name), None)
        if match is not None:
            return match
        total = page.get("totalCount")
        if not rules or (isinstance(total, int) and page_no * 100 >= total):
            return None
        page_no += 1


def in_sync(rule, existing):
    # rstrip: whether the YAML file ends with a newline changes a block
    # scalar's trailing "\n", which would otherwise show up as a change and
    # rewrite the rule on every sync.
    same_fields = all(
        (existing.get(remote) or "").rstrip("\n") == rule[local].rstrip("\n")
        for local, remote in (
            ("category", "category"),
            ("severity", "severity"),
            ("content", "content"),
            ("good_examples", "goodExamples"),
            ("bad_examples", "badExamples"),
        )
    )
    # An empty local list and a remote ["/"] are the same universal scope.
    return same_fields and sorted(existing.get("scopes") or ["/"]) == sorted(
        rule["scopes"] or ["/"]
    )


def create(rule):
    argv = [
        "rules", "create",
        "--name", rule["name"],
        "--category", rule["category"],
        "--severity", rule["severity"],
        "--content", rule["content"],
        "--good-examples", rule["good_examples"],
        "--bad-examples", rule["bad_examples"],
    ]
    # Omitting --scopes on create is the universal scope "/".
    if rule["scopes"]:
        argv += ["--scopes", ",".join(rule["scopes"])]
    return qodo(*argv)


def update(rule, existing):
    argv = [
        "rules", "update",
        "--rule-id", str(existing["ruleId"]),
        "--category", rule["category"],
        "--severity", rule["severity"],
        "--content", rule["content"],
        "--good-examples", rule["good_examples"],
        "--bad-examples", rule["bad_examples"],
    ]
    if rule["scopes"]:
        argv += ["--scopes", ",".join(rule["scopes"])]
    else:
        # --scopes takes a comma list and can't express "empty"; the JSON
        # escape hatch can, and [] means the universal scope "/".
        argv += ["--args", json.dumps({"scopes": []})]
    return qodo(*argv)


def is_example(path):
    return path.read_text().lstrip().startswith(EXAMPLE_MARKER)


def main():
    files = sorted(p for p in RULES_DIR.glob("*.yaml") if not p.name.startswith("_"))
    if not files:
        print("no rule files found — nothing to sync")
        return 0

    examples = [p.name for p in files if is_example(p)]
    if examples and not DRY_RUN:
        print("refusing to sync: these files are still the shipped examples, and a "
              "Qodo rule cannot be deleted once created — only deactivated:",
              file=sys.stderr)
        for name in examples:
            print(f"  {name}", file=sys.stderr)
        print("\nDelete each one, or remove its first-line "
              f"'{EXAMPLE_MARKER}' comment to adopt it as your own rule. "
              "Re-run with DRY_RUN=1 to preview the sync meanwhile.",
              file=sys.stderr)
        return 1

    if DRY_RUN:
        print("DRY RUN — reading Qodo, writing nothing")
        if examples:
            print(f"NOTE: {len(examples)} shipped example rule(s) present — a real "
                  "sync will refuse until they are replaced or adopted.")
        print()

    created, updated, unchanged, failed = [], [], [], []
    for path in files:
        try:
            rule = load_rule(path)
            existing = find_existing(rule["name"])
            if existing is None:
                if not DRY_RUN:
                    res = create(rule)
                    if res.get("state") == "pending":
                        print(f"NOTE: '{rule['name']}' created as PENDING — the CI "
                              "identity is not a workspace admin; approve it in Qodo.")
                created.append(rule["name"])
                continue

            source_type = existing.get("sourceType")
            if source_type not in OWNED_SOURCE_TYPES:
                raise ValueError(
                    f"a rule with this name already exists in Qodo from "
                    f"{source_type!r} (id {existing.get('ruleId')}), which this repo "
                    "does not manage — rename this file's `name:` instead"
                )
            if in_sync(rule, existing):
                unchanged.append(rule["name"])
            else:
                if not DRY_RUN:
                    update(rule, existing)
                updated.append(rule["name"])
            # Content can match while the rule is switched off in Qodo. For a gate
            # rule (severity: error) that silently removes a merge blocker, so it
            # fails the sync; anything else is reported. The sync doesn't
            # reactivate it: someone deactivated it on purpose, so a person decides.
            state = existing.get("state")
            if state != "active":
                msg = (f"'{rule['name']}' is {state!r} in Qodo, so it is not enforced — "
                       f"reactivate it (qodo rules set-state) or remove the file")
                if rule["severity"] == "error":
                    failed.append((path.name, "gate rule " + msg))
                else:
                    print(f"NOTE: {msg}")
        except Exception as exc:
            failed.append((path.name, str(exc)))

    for name in created:
        print(f"{'would create' if DRY_RUN else 'created'}:   {name}")
    for name in updated:
        print(f"{'would update' if DRY_RUN else 'updated'}:   {name}")
    for name in unchanged:
        print(f"unchanged:     {name}")
    for fname, err in failed:
        print(f"FAILED:        {fname}: {err}", file=sys.stderr)
    created_verb, updated_verb = ("to create", "to update") if DRY_RUN else ("created", "updated")
    print(f"\n{len(created)} {created_verb}, {len(updated)} {updated_verb}, "
          f"{len(unchanged)} unchanged, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
