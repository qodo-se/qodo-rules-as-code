# Drafts

Not examples. These are shape-only rules — correct in form, never exercised
against real diffs — held here until they are validated, at which point they
move to `examples/<category>/`.

The gap in all six is the same: they show the ideal case and little else, so a
reviewer has nothing to pass over and no stated test for the ambiguous case.

## Promoting one

1. Decide its shape. Is it an absolute ban, a pattern allowed only with
   evidence, or a violation not visible in the diff? See `examples/README.md`.
2. Rewrite `good_examples` to name every case that should **pass**, not just the
   ideal one, and `bad_examples` to state the test rather than show a snippet.
3. Exercise it: sync it to a scratch workspace scoped to a throwaway repo, open
   one pull request per case — including at least one that must produce
   **silence** — and confirm each verdict.
4. Move the file to `examples/<category>/` and note in its header which details
   are doing the work.

Step 3 is the one that matters. Every rule in `examples/` earned its place by
staying quiet where it should, not by firing.
