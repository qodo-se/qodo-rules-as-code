# Examples

Nothing here is synced — `scripts/sync_rules.py` only reads `rules/`. Copy one
into `rules/`, adjust it, open a PR.

Directories match the `category:` field, so browse by the category you are
writing for.

| Rule | Category | Severity | State |
|---|---|---|---|
| `noqa-prohibited-suppressions` | Maintainability | error | worked through |
| `noqa-conditional-suppressions` | Maintainability | warning | worked through |
| `no-n-plus-one-queries` | Performance | error | worked through |
| `never-hardcode-secrets` | Security | error | shape only |
| `no-floating-point-for-money` | Correctness | error | shape only |
| `outbound-calls-must-set-a-timeout` | Reliability | error | shape only |
| `log-errors-with-correlation-id` | Observability | warning | shape only |
| `cover-new-branches-with-tests` | Testability | warning | shape only |
| `scoped-example-no-direct-sql-in-handlers` | Architecture | recommendation | shape only, also demos `scopes:` |

**Worked through** means the criteria have been exercised against real diffs, and
the file's header notes which details are doing the work. **Shape only** means
correct in form but thin: they show the ideal case and little else, so a reviewer
has nothing to pass over. Tighten before adopting.

## Three shapes worth knowing

The three worked-through examples are each a different shape, and the shape
decides where the rule's substance goes:

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
