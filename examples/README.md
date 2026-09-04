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

Each has been exercised against real diffs — including cases that must produce
**silence** — and its header notes which details are doing the work. Rules that
have not been through that are in `drafts/`, not here.

## Three shapes worth knowing

These three are each a different shape, and the shape decides where the rule's
substance goes:

- **An absolute ban on a pattern** — decidable from the changed lines alone.
  One condition. `noqa-prohibited-suppressions`.
- **A pattern allowed only with evidence** — what is checked is the reason
  attached to it, not the pattern. `noqa-conditional-suppressions`.
- **A violation not visible in the diff** — the compliant and violating changes
  look the same; what separates them lives in a file the change never touches,
  so the rule has to say to go and read it. `no-n-plus-one-queries`.

Two habits all three share:

**Name every case that should pass** in `good_examples`, not just the ideal one.
A rule that only ever fires is a rule nobody trusts.

**Keep exemptions inside the rule they exempt.** A separate "these are
acceptable" rule will not stop another rule from flagging.
