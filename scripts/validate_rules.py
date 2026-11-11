#!/usr/bin/env python3
"""PR-time validation for rules/*.yaml — local checks only, no Qodo API.

Fails on: schema violations (see sync_rules.load_rule), non-kebab-case
filenames, duplicate rule names, and — when REQUIRE_EXAMPLES is on — missing
examples. Warns via GitHub annotations on renames and deletions, both of which
leave the previously synced rule live in Qodo (the sync never deletes).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_rules import EXAMPLE_MARKER, RULES_DIR, is_example, load_rule

# Compare against the PR's actual target branch (GITHUB_BASE_REF on pull_request
# events); fall back to main for local runs.
BASE_REF = f"origin/{os.environ.get('GITHUB_BASE_REF') or 'main'}"
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.yaml$")

# --- Repo policy: tighten these for your org ---------------------------------
# Restrict which categories this repo may own, e.g. {"Security"} for a
# security-only ruleset. None = any category the workspace supports.
ALLOWED_CATEGORIES = None
# Require both good_examples and bad_examples on every rule. Examples are what
# make a rule reviewable, so this defaults to on.
REQUIRE_EXAMPLES = True
# -----------------------------------------------------------------------------


def git(*argv):
    return subprocess.run(
        ["git", *argv], capture_output=True, text=True, check=False
    ).stdout


def base_rule_name(path):
    shown = git("show", f"{BASE_REF}:{path.as_posix()}")
    m = re.search(r'^name:\s*"?(.+?)"?\s*$', shown, re.M)
    return m.group(1) if m else None


def main():
    errors, names = [], {}
    # The sync globs *.yaml only, so a .yml file would be silently skipped.
    for stray in sorted(RULES_DIR.glob("*.yml")):
        errors.append(f"{stray.relative_to(RULES_DIR.parent)}: use the .yaml "
                      "extension — .yml files are not synced")
    for path in sorted(RULES_DIR.glob("*.yaml")):
        rel = path.relative_to(RULES_DIR.parent)
        if path.name.startswith("_"):
            continue
        if not KEBAB.match(path.name):
            errors.append(f"{rel}: filename must be kebab-case .yaml")
        try:
            rule = load_rule(path)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            continue
        if ALLOWED_CATEGORIES is not None and rule["category"] not in ALLOWED_CATEGORIES:
            errors.append(
                f"{rel}: category must be one of {sorted(ALLOWED_CATEGORIES)}, "
                f"got {rule['category']!r}"
            )
        if REQUIRE_EXAMPLES:
            for field in ("good_examples", "bad_examples"):
                if not rule[field].strip():
                    errors.append(
                        f"{rel}: {field} is empty — show the pattern, don't just state it"
                    )
        if rule["name"] in names:
            errors.append(f"{rel}: duplicate name also used by {names[rule['name']]}")
        names[rule["name"]] = rel

        # Not an error: a PR may legitimately touch other rules while the
        # examples are still around. The sync is what refuses to write.
        if is_example(path):
            print(f"::warning file={rel}::still a shipped example — the sync will "
                  f"refuse to run until this file is deleted or its "
                  f"'{EXAMPLE_MARKER}' line is removed")

        prior = base_rule_name(rel)
        if prior and prior != rule["name"]:
            print(f"::warning file={rel}::name changed from '{prior}' — the old rule "
                  "stays live in Qodo as an orphan; retire it in the portal after merge")

    for line in git("diff", "--name-status", f"{BASE_REF}...HEAD", "--", "rules/").splitlines():
        parts = line.split("\t")
        status = parts[0]
        # A rename (R<score>\told\tnew) also orphans the old file's rule when its
        # `name:` changed with it; the per-file check above can't see the old path.
        if status.startswith("R") and len(parts) == 3:
            old_path, new_path = parts[1], parts[2]
            old_shown = git("show", f"{BASE_REF}:{old_path}")
            m = re.search(r'^name:\s*"?(.+?)"?\s*$', old_shown, re.M)
            try:
                new_name = load_rule(Path(new_path)).get("name")
            except Exception:
                new_name = None
            if m and m.group(1) != new_name:
                print(f"::warning file={new_path}::renamed from {old_path} and its name "
                      f"changed from '{m.group(1)}' — the old rule stays live in Qodo; "
                      "retire it after merge")
        elif status == "D" and not Path(parts[-1]).name.startswith("_"):
            print(f"::warning file={parts[-1]}::deleted — the synced rule stays live in "
                  "Qodo; retire it in the portal or with qodo rules set-state")

    for e in errors:
        print(f"::error::{e}")
    print(f"{len(names)} rules checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
