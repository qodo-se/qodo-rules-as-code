# Examples

Nothing here is synced — `scripts/sync_rules.py` only reads `rules/`. Copy one
into `rules/`, adjust it, open a PR.

Directories match the `category:` field, so browse by the category you are
writing for.

| Rule | Category | Severity |
|---|---|---|
| `noqa-prohibited-suppressions` | Maintainability | error |
| `noqa-conditional-suppressions` | Maintainability | warning |
| `no-n-plus-one-queries` | Performance | error |
| `no-hardcoded-secrets` | Security | error |
| `money-integer-minor-units` | Correctness | error |

Each has been exercised against real diffs — including cases that must produce
**silence** — and its header notes which details are doing the work. Rules that
have not been through that are in `drafts/`, not here.

## Three shapes worth knowing

Each is a different shape, and the shape decides where the rule's substance
goes:

- **An absolute ban on a pattern** — decidable from the changed lines alone.
  `noqa-prohibited-suppressions`, and `no-hardcoded-secrets`, which is the same
  shape with one carve-out folded in.
- **A pattern allowed only with evidence** — what is checked is the reason
  attached to it, not the pattern. `noqa-conditional-suppressions`.
- **A violation not visible in the diff** — the compliant and violating changes
  look the same; what separates them lives in a file the change never touches,
  so the rule has to say to go and read it. `no-n-plus-one-queries`, and
  `money-integer-minor-units`, where a bare `float` means nothing until you
  read the declaration it came from.

Three habits they share:

**Name every case that should pass** in `good_examples`, not just the ideal one.
A rule that only ever fires is a rule nobody trusts.

**Keep exemptions inside the rule they exempt.** A separate "these are
acceptable" rule will not stop another rule from flagging.

**Bound the reviewer against work it cannot do.** Left unbounded it attempts
the verification anyway and reports on the result — so
`no-hardcoded-secrets` says outright not to judge whether a credential is still
valid, and `no-n-plus-one-queries` says how far to trace before reporting.

## Validating one before you adopt it

A rule is worth trusting once it has been run against diffs that must produce
**silence**, not just diffs that must produce a finding. For each rule, seed a
violation and at least one control that contains the banned shape in a context
the rule permits — money divided but with the remainder allocated, a key read
from the environment, a placeholder in a test. A rule that has only ever fired
has not been tested.

Two things to know before you start:

- **Check scope at every tier.** A rule's `scopeElements` carry a `kind` of
  `repo`, `org`, or `global`. A rule list filtered on repository paths passes
  straight over the org tier, so an org-wide rule on the same subject as the one
  you are writing is easy to miss until it shows up in a review.
- **Score conditions covered, not findings counted.** A rule with several
  failure conditions reports one consolidated finding that names them all, so an
  expectation written as "2 findings" reads as a half-miss against correct
  behaviour.
