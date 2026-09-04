---
name: qodo-rule-author
description: Turn a coding convention into a Qodo Review Standard managed by this repo — a YAML file in rules/, validated and ready for a PR. Use when the user says "make this a Qodo rule", "codify this convention", "add a review standard", "we should enforce this everywhere", or asks to change or retire an existing rule this repo owns. Not for applying rules while writing code, and not for syncing (merging to main does that).
---

# Authoring a Qodo rule in this repo

One YAML file in `rules/` is one rule. Merging to `main` syncs it. Your job ends
at a validated file and a PR — **never run `scripts/sync_rules.py` without
`DRY_RUN=1`**, and never enable the sync workflow.

The reason for that caution: a Qodo rule cannot be deleted once created, only
deactivated. A rule synced by mistake is permanent clutter in the workspace, and
a rule whose `name:` you later change becomes an orphan while a second rule
takes its place.

## Writing the rule

1. **Read `rules/_template.yaml`** — it is the current schema. Copy it to
   `rules/<kebab-case-name>.yaml`. The filename must be kebab-case `.yaml`;
   `.yml` is rejected.

2. **Pick the category from the workspace**, not from memory:
   `qodo rules metadata --json`. If it disagrees with `CATEGORIES` in
   `scripts/sync_rules.py`, say so — that constant is a local mirror and may
   have drifted.

3. **Check the name isn't taken**:
   `qodo rules list --name-contains "<a distinctive phrase>" --page-size 100 --json`.
   A collision with an existing `User` rule means the sync would *overwrite* it;
   a collision with a `Repository File` rule fails the sync by design. Both are
   worth surfacing before you write the file.

4. **Write the rule so it meets the criteria below.** Check it against them
   before handing back, and say which one you had to work at — that is usually
   where the rule is still weak.

5. **Default to org-wide.** Omit `scopes:` unless the rule genuinely shouldn't
   apply everywhere. When you do scope it, copy the path verbatim from
   `qodo rules list --json` output — Qodo accepts any well-formed path, so an
   invented one yields a rule that silently matches nothing.

## What type of rule is this?

Deciding the type first tends to settle the wording, because each type puts its
substance in a different place.

**Prohibition — an absolute ban on a pattern.** Decidable from the changed lines
alone; one condition; `error`. Enumerate the banned patterns in `bad_examples`,
restricted to those that are wrong in every context. A pattern whose correctness
depends on where it appears — source versus tests, say — wants a differently
scoped rule rather than an extra list entry.

**Qualified permission — the pattern is allowed, but only with evidence.** What
is being checked is not the pattern; it is the quality of the reason attached to
it. This is the type most often written as a pattern match and then found
wanting. Phrase the test as a judgement: is there a cause a reader could act on,
or does the comment simply restate what the check means? And say what is out of
scope — "do not check whether the referenced ticket exists" — so the reviewer
does not attempt it.

**Contextual — the violation is not decidable from the diff.** The compliant and
violating diffs look the same; what separates them lives in a file the change
never touches. Put the investigative step in `content`, plainly: "the origin is
often in a different function or module; trace it and read it before reporting."
Then name every passing case in `good_examples`, or the rule fires on the safe
one.

**Allowlist — not a type.** A separate "these are acceptable" rule will not stop
another rule from flagging. An exemption is part of a rule, not a neighbour to
it: name the permitted cases in the `good_examples` of the rule that would
otherwise flag them.

## Criteria: is the rule clear and specific?

A rule is only effective if it is understandable and unambiguous. These are
Qodo's own
[best practices for setting rules](https://docs.qodo.ai/governance/rule-enforcement/best-practices-for-setting-rules),
applied to this repo's YAML.

**Does `content` say what it checks, why it matters, and when it applies?** The
"why" is what earns compliance rather than a workaround.

- Weak: "Timeouts are important for reliability."
- Strong: "Every outbound HTTP request must pass an explicit timeout. Client
  defaults are frequently unbounded, so one slow dependency exhausts the
  caller's connection pool and spreads the outage."

That is enough for a rule decidable from the changed lines. Two other shapes
need more from this field.

**Does it warn that the diff may not be enough?** If deciding the rule means
reading something the change does not touch, `content` has to say so, or the
rule matches on the visible pattern and flags correct code.

- Thin: "Queries must not run once per row."
- Strong: "…the queryset that feeds the loop must eager-load that relation at
  its origin — which is often in a different function or module than the loop
  itself."

Note where the actual instruction goes. `content` raises the flag; the
imperative belongs with the conditions, in both example fields, because that is
where the reviewer is deciding. `no-n-plus-one-queries` puts "trace the origin
before reporting, following it across functions and modules" alongside its
passing cases, and "the loop and the queryset origin being in different modules
does not excuse the violation — read the origin and report it" alongside its
failing ones.

**Does it name the evidence required, when the pattern is allowed with a
caveat?** For a rule that permits something conditionally, the condition is the
rule. State it here, not only in the examples.

- Thin: "Suppressions need a good reason."
- Strong: "…each must state why the check is wrong at this specific site, and
  its comment must carry a ticket or issue identifier so the suppression can be
  found and removed later."

**Would someone searching for this rule find it?** `content` is what the
duplicate check searches — the example fields are not searched — so the phrase
that distinguishes this rule from its neighbours has to appear here. If the
rule requires or forbids a specific artifact, name the artifact in the words
someone would use looking for it. A rule whose distinguishing requirement lives
only in its examples is findable by name and nothing else, which is how
near-duplicates and rules that contradict each other get written.

**Does it have a single, measurable goal?** A developer must be able to tell
whether a given diff passes or fails. If describing the purpose needs an "and",
split it into two rules.

**Is the phrasing free of vague quality words?** "Clean", "readable", "properly
handled", "appropriately" — each pushes the judgment onto the reviewer and
produces inconsistent findings. Say exactly what the code must do in this
context.

- Weak: "Error handling should be done properly."
- Specific: "Every `except` block must either re-raise or log the exception with
  its stack trace; a bare `except: pass` silently discards failures."

**Do both fields state a test, and illustrate it?** Both are required and the PR
check enforces it. A bare snippet is not enough — a reviewer needs a condition it
can decide — so lead with the test, then show it in the language the rule
targets, drawn from this codebase's actual patterns. `bad_examples` should be the
mistake someone would plausibly make, not a strawman, and `good_examples` should
name every case that ought to pass, not only the ideal one.

**Does severity match consequence, not strength of feeling?** `error` for
correctness, security, or outage risk; `warning` for comply-by-default;
`recommendation` for preference. Marking a preference as `error` teaches people
to ignore the whole ruleset.

## Before handing back

```bash
python3 scripts/validate_rules.py          # offline; same checks as the PR gate
DRY_RUN=1 python3 scripts/sync_rules.py    # read-only; confirms create vs update
```

The dry run distinguishes the two outcomes that matter: `would create` means a
new rule, `would update` means you matched an existing name and will change it.
If you expected the first and see the second, stop and tell the user.

Then open a PR — CODEOWNERS review is the gate, so don't merge it yourself.

## Changing or retiring a rule

- **Edit** — change the file in place, keeping `name:` untouched. Renaming is
  not an edit: it creates a second rule and leaves the first live.
- **Retire** — deleting the file does *not* remove the rule. Delete it, and tell
  the user to deactivate the live one by id:

  ```bash
  qodo rules set-state --args '{"rule_ids":[123],"state":"inactive"}' --json
  ```

  The `--rule-ids` flag rejects a bare integer; the JSON form above works.
