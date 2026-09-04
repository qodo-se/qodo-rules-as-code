# Examples

Nothing here is synced. `scripts/sync_rules.py` only reads `rules/`, so these
are reference material: copy one into `rules/`, adjust it, and open a PR.

## By type

The type of a rule tends to settle where its substance goes, so these three are
organised that way. Each file's header notes the details doing the real work.

| Directory | Type | The rule is decidable from… |
|---|---|---|
| `prohibition/` | absolute ban on a pattern | the changed lines alone |
| `qualified-permission/` | pattern allowed, but only with evidence | the reason attached to the pattern |
| `contextual/` | violation not visible in the diff | a file the change never touches |

There is a fourth shape people reach for that does not work: a separate
"these are acceptable" rule. It will not stop another rule from flagging.
Exemptions belong in the `good_examples` of the rule that would otherwise flag
them — both NOQA examples do this rather than leaning on a neighbour.

## Starters

`starters/` holds shorter, shape-only rules — correct in form, but not yet
classified by type and not tightened. They are a faster read than the typed
examples and a reasonable place to start from, provided you finish the job:
decide the type, then make sure `good_examples` names every case that should
pass, not just the ideal one. A rule that only ever fires is a rule nobody
trusts.

`starters/scoped-example-no-direct-sql-in-handlers.yaml` additionally shows a
`scopes:` block; the others are org-wide.
