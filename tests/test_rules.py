#!/usr/bin/env python3
"""Unit tests for the pure logic in scripts/sync_rules.py.

Everything here runs offline: no `qodo` CLI, no network, no mocking. The parts
that talk to the API (`find_existing`, `create`, `update`) are deliberately not
covered — exercise those with `DRY_RUN=1 python3 scripts/sync_rules.py`.

    python3 -m unittest discover -s tests -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_rules import (  # noqa: E402
    EXAMPLE_MARKER,
    RULES_DIR,
    in_sync,
    is_example,
    load_rule,
    parse_scopes,
)

VALID = """\
name: "A test rule"
category: Security
severity: error
content: "Do the thing."
good_examples: "ok()"
bad_examples: "bad()"
"""


def write(text):
    """Write text to a temp .yaml file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


class TestLoadRule(unittest.TestCase):
    def test_valid_rule_loads_with_defaults(self):
        rule = load_rule(write(VALID))
        self.assertEqual(rule["name"], "A test rule")
        self.assertEqual(rule["severity"], "error")
        # Absent scopes means the universal scope, represented as [].
        self.assertEqual(rule["scopes"], [])

    def test_examples_default_to_empty_string(self):
        text = VALID.replace('good_examples: "ok()"\n', "").replace(
            'bad_examples: "bad()"\n', ""
        )
        rule = load_rule(write(text))
        self.assertEqual(rule["good_examples"], "")
        self.assertEqual(rule["bad_examples"], "")

    def test_missing_required_field_is_rejected(self):
        for field in ("name", "category", "severity", "content"):
            text = "\n".join(
                l for l in VALID.splitlines() if not l.startswith(f"{field}:")
            )
            with self.subTest(field=field), self.assertRaises(ValueError) as cm:
                load_rule(write(text))
            self.assertIn("missing fields", str(cm.exception))

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            load_rule(write(VALID + 'good_exmaples: "typo"\n'))
        self.assertIn("unknown fields", str(cm.exception))

    def test_bad_severity_is_rejected(self):
        text = VALID.replace("severity: error", "severity: critical")
        with self.assertRaises(ValueError) as cm:
            load_rule(write(text))
        self.assertIn("severity must be one of", str(cm.exception))

    def test_category_outside_the_workspace_list_is_rejected(self):
        text = VALID.replace("category: Security", "category: Securty")
        with self.assertRaises(ValueError) as cm:
            load_rule(write(text))
        self.assertIn("not a workspace category", str(cm.exception))

    def test_overlong_name_is_rejected(self):
        text = VALID.replace('"A test rule"', '"' + "x" * 129 + '"')
        with self.assertRaises(ValueError) as cm:
            load_rule(write(text))
        self.assertIn("exceeds 128 chars", str(cm.exception))

    def test_non_mapping_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            load_rule(write("- just\n- a list\n"))
        self.assertIn("not a YAML mapping", str(cm.exception))


class TestParseScopes(unittest.TestCase):
    def test_absent_means_universal(self):
        self.assertEqual(parse_scopes(None), [])

    def test_valid_paths_pass_through(self):
        scopes = ["/owner/repo/", "/owner/repo/src/module/"]
        self.assertEqual(parse_scopes(scopes), scopes)

    def test_a_bare_string_is_rejected(self):
        # Easy to write in YAML as `scopes: /owner/repo/`, and iterating the
        # string would otherwise validate character by character.
        with self.assertRaises(ValueError) as cm:
            parse_scopes("/owner/repo/")
        self.assertIn("must be a YAML list", str(cm.exception))

    def test_missing_leading_or_trailing_slash_is_rejected(self):
        for bad in ("owner/repo/", "/owner/repo", "owner/repo"):
            with self.subTest(scope=bad), self.assertRaises(ValueError) as cm:
                parse_scopes([bad])
            self.assertIn("starting and ending with", str(cm.exception))

    def test_non_string_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_scopes([123])

    def test_too_many_scopes_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            parse_scopes([f"/owner/repo{i}/" for i in range(26)])
        self.assertIn("at most 25", str(cm.exception))

    def test_universal_mixed_with_specific_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            parse_scopes(["/", "/owner/repo/"])
        self.assertIn("already universal", str(cm.exception))

    def test_universal_alone_is_allowed(self):
        self.assertEqual(parse_scopes(["/"]), ["/"])


def remote(**overrides):
    """A rule as `qodo rules list` returns it (camelCase keys)."""
    base = {
        "ruleId": 1,
        "category": "Security",
        "severity": "error",
        "content": "Do the thing.",
        "goodExamples": "ok()",
        "badExamples": "bad()",
        "scopes": ["/"],
        "state": "active",
        "sourceType": "User",
    }
    base.update(overrides)
    return base


class TestInSync(unittest.TestCase):
    def setUp(self):
        self.rule = load_rule(write(VALID))

    def test_identical_rule_is_in_sync(self):
        self.assertTrue(in_sync(self.rule, remote()))

    def test_trailing_newline_difference_is_not_a_change(self):
        # Regression: a YAML block scalar keeps the file's final newline, so
        # whether the file ends with one must not trigger a rewrite on every
        # single sync.
        self.assertTrue(in_sync(self.rule, remote(goodExamples="ok()\n")))
        self.assertTrue(in_sync(self.rule, remote(badExamples="bad()\n\n")))

    def test_empty_local_scopes_equals_remote_universal(self):
        self.assertEqual(self.rule["scopes"], [])
        self.assertTrue(in_sync(self.rule, remote(scopes=["/"])))

    def test_scope_order_does_not_matter(self):
        rule = load_rule(write(VALID + "scopes:\n  - /a/b/\n  - /c/d/\n"))
        self.assertTrue(in_sync(rule, remote(scopes=["/c/d/", "/a/b/"])))

    def test_differing_field_is_out_of_sync(self):
        for key, value in (
            ("content", "Do something else."),
            ("severity", "warning"),
            ("category", "Quality"),
            ("goodExamples", "different()"),
            ("badExamples", "different()"),
            ("scopes", ["/owner/repo/"]),
        ):
            with self.subTest(field=key):
                self.assertFalse(in_sync(self.rule, remote(**{key: value})))

    def test_missing_remote_field_is_treated_as_empty(self):
        rule = load_rule(
            write(VALID.replace('good_examples: "ok()"\n', 'good_examples: ""\n'))
        )
        self.assertTrue(in_sync(rule, remote(goodExamples=None)))


class TestIsExample(unittest.TestCase):
    def test_marker_on_the_first_line_is_detected(self):
        self.assertTrue(is_example(write(f"{EXAMPLE_MARKER} — delete me\n" + VALID)))

    def test_marker_below_the_first_line_is_not_a_marked_example(self):
        # The bulk-clear command in the README deletes line 1, so only a
        # first-line marker may count — otherwise clearing it would eat a real
        # line of YAML.
        self.assertFalse(is_example(write(VALID + f"{EXAMPLE_MARKER}\n")))

    def test_unmarked_file_is_not_an_example(self):
        self.assertFalse(is_example(write(VALID)))


def shipped_rule_files():
    """Every rule file this repo ships as reference material.

    `rules/` is deliberately empty for a consumer — it holds only `_template`
    until they add their own — so the shipped rules are the validated ones in
    `examples/<category>/` plus the shape-only ones in `drafts/`. Both must stay
    loadable: a consumer copies them into `rules/` verbatim.
    """
    root = Path(__file__).resolve().parent.parent
    return sorted(
        p
        for d in ("examples", "drafts", "rules")
        for p in (root / d).rglob("*.yaml")
        if not p.name.startswith("_")
    )


class TestShippedRules(unittest.TestCase):
    """The rules this repo ships must stay loadable — consumers copy them."""

    def test_every_shipped_rule_loads(self):
        files = shipped_rule_files()
        self.assertTrue(files, "no rule files found in examples/, drafts/ or rules/")
        for path in files:
            with self.subTest(rule=path.name):
                load_rule(path)

    def test_shipped_rule_names_are_unique(self):
        names = [load_rule(p)["name"] for p in shipped_rule_files()]
        self.assertEqual(
            len(names), len(set(names)),
            "two shipped rules share a name; the sync matches on exact name",
        )

    def test_promoted_examples_scope_to_a_placeholder(self):
        """A promoted example must not carry the scope it was validated against."""
        root = Path(__file__).resolve().parent.parent
        for path in sorted((root / "examples").rglob("*.yaml")):
            with self.subTest(rule=path.name):
                for scope in load_rule(path)["scopes"]:
                    self.assertNotIn(
                        "standards-poc", scope,
                        f"{path.name} still points at the validation repo",
                    )


if __name__ == "__main__":
    unittest.main()
