# Drafts

Not examples. These are shape-only rules — correct in form, never exercised
against real diffs — held here until they are validated, at which point they
move to `examples/<category>/`.

The gap in all of them is the same: they show the ideal case and little else, so
a reviewer has nothing to pass over and no stated test for the ambiguous case.

## Promoting one

1. Decide its shape. Is it an absolute ban, a pattern allowed only with
   evidence, or a violation not visible in the diff? See `examples/README.md`.
2. Rewrite `good_examples` to name every case that should **pass**, not just the
   ideal one, and `bad_examples` to state the test rather than show a snippet.
3. Check what already governs the target repo — from **two** places, not one.
   `qodo rules list` shows user-authored rules, but rules auto-derived from a
   skill never appear in it, and an org-wide skill's rules are the easiest
   overlap to miss. Also run `qodo review-skills list`, enumerating every skill
   and filtering on its own `scopes`: a skill's name rarely contains the subject
   word, so a name-filtered search returns a clean result that is just a missed
   search. Skipping this is how a second secrets rule gets authored for a repo an
   org-wide one already covers.
4. Exercise it: sync it to a scratch workspace scoped to a throwaway repo, open
   one pull request per case — including at least one that must produce
   **silence** — and confirm each verdict. Make the silent cases *near-misses*:
   each should contain the shape the rule bans, in a context the rule permits.
   A silence over unrelated code proves nothing.
5. Move the file to `examples/<category>/` and note in its header which details
   are doing the work.

Step 4 is the one that matters. Every rule in `examples/` earned its place by
staying quiet where it should, not by firing.

When you score it, count **conditions covered, not findings**. A rule with
several failure conditions reports one consolidated finding naming them all.
