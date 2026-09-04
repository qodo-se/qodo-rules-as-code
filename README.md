# qodo-rules-starter

Manage your Qodo **Review Standards** as code.

A Review Standard is a rule Qodo applies when it reviews a pull request — "money
must not be a float", "every outbound call needs a timeout" — and it normally
lives in the Qodo portal, edited by hand. This repo makes git the source of truth
instead: one YAML file in `rules/` is one rule, pull requests are where rules get
proposed and reviewed, and merging to `main` syncs them to Qodo. The portal
becomes the deployment target rather than the place rules are written.

You need git and CI familiarity; no prior Qodo setup is assumed.

## Layout

```
rules/                     one YAML file per rule; _template.yaml to copy
scripts/sync_rules.py      create-or-update rules in Qodo (the merge step)
scripts/validate_rules.py  offline schema checks (the PR gate)
tests/test_rules.py        unit tests for the schema and comparison logic
skills/qodo-rule-author/   authoring guidance, also read by Qodo at review time
.github/workflows/         validate-rules.yml (PRs), sync-rules.yml (main)
.github/CODEOWNERS         who must approve a rule change
```

## How it works

1. Copy `rules/_template.yaml` to `rules/<kebab-case-name>.yaml` and fill it in.
2. Open a PR. **Validate rules** runs offline checks — schema, kebab-case
   filenames, duplicate names, non-empty examples — plus warnings when the diff
   renames or deletes a rule, since the sync never deletes and the old rule would
   be left behind in Qodo.
3. Merge to `main`. **Sync rules to Qodo** creates or updates each rule through
   the `qodo` CLI. Rules already matching their file are skipped.

> **The sync workflow ships disabled.** Enable it once you have pointed the repo
> at your own workspace — see *Setup* below.

## Three worked examples

`rules/` ships three examples chosen to show rule *types*, since the type tends
to settle where a rule's substance goes.

| File | Type | What it does |
|---|---|---|
| `noqa-prohibited-suppressions.yaml` | prohibition | bans a pattern outright; one condition |
| `noqa-conditional-suppressions.yaml` | qualified permission | allows the pattern, but judges the reason attached to it |
| `no-n-plus-one-queries.yaml` | contextual | the violation is not decidable from the changed lines alone |

Two habits they demonstrate, both easy to miss:

**Silence has to be authored.** Every case you want passed over must appear in
`good_examples` as a passing condition. The N+1 rule stays quiet on a
prefetching origin and on a bounded literal loop because both are listed. A rule
that only ever fires is a rule nobody trusts.

**An exemption belongs inside the rule it exempts.** A separate "these are
acceptable" rule will not stop another rule from flagging. Name the permitted
cases in the `good_examples` of the rule that would otherwise flag them — which
is what the two NOQA files do.

Each file carries a `# qodo-rules-as-code:example` first line, so a real sync
refuses to run while they are present. Adopt one by deleting that line; drop the
rest.

## Prerequisites

- **The `qodo` CLI**, and a login: `curl -fsSL https://get.qodo.ai/install.sh | sh`
  then `qodo login`. Verify with `qodo whoami --json`.
- **A Qodo workspace admin identity** for the key the sync will use. A non-admin
  key creates rules as *pending* suggestions an admin must approve, and cannot
  update existing ones.
- **Python 3 with PyYAML**: `pip install 'pyyaml==6.0.2'`.

## Setup

1. **Point it at your workspace.** Set `QODO_SDK_BASE_URL` as a repository
   *variable* — read yours from `qodo whoami --json`, field `sdkBaseUrl`. The
   sync fails fast if it is unset, so the repo can never sync into someone
   else's workspace.
2. **Add `QODO_API_KEY`** as a secret in a repository environment named
   `qodo-sync`, using an admin key.
3. **Scope your rules.** Omit `scopes:` for org-wide, or list repository paths.
   Scopes are not validated against real repositories, so copy paths verbatim
   from `qodo rules list --json` rather than typing them.
4. **Clear the example guard.** Delete the shipped example files, or remove
   their `# qodo-rules-as-code:example` first line to adopt them. The sync
   refuses while any remain, because a Qodo rule cannot be deleted once created
   — only deactivated.
5. **Enable the sync workflow** and protect `main` with CODEOWNERS review.

## Before you open a PR

```bash
python3 scripts/validate_rules.py          # offline; same checks as the PR gate
DRY_RUN=1 python3 scripts/sync_rules.py    # read-only; confirms create vs update
```

The dry run distinguishes the two outcomes that matter: `would create` means a
new rule, `would update` means you matched an existing name and will change it.
