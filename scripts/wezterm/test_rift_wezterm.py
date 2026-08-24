"""Unit tests for the rift-wezterm layout tool.

Run: python3 scripts/wezterm/test_rift_wezterm.py
"""

import importlib.util
import unittest
from pathlib import Path


def load_tool():
    path = Path(__file__).with_name("rift-wezterm")
    spec = importlib.util.spec_from_loader(
        "rift_wezterm", loader=None, origin=str(path)
    )
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


rw = load_tool()


class SessionFromArgv(unittest.TestCase):
    def test_attach_form(self):
        self.assertEqual(rw.session_from_rift_argv(["rift", "attach", "dev.2"]), "dev.2")

    def test_attach_alias(self):
        self.assertEqual(rw.session_from_rift_argv(["rift", "a", "dev.2"]), "dev.2")

    def test_attach_with_flags(self):
        self.assertEqual(
            rw.session_from_rift_argv(["rift", "attach", "--fish", "dev.2"]),
            "dev.2",
        )

    def test_attach_detached_is_ignored(self):
        self.assertIsNone(rw.session_from_rift_argv(["rift", "attach", "-d", "dev.2"]))

    def test_bare_name(self):
        self.assertEqual(rw.session_from_rift_argv(["rift", "main"]), "main")

    def test_absolute_path_binary(self):
        self.assertEqual(
            rw.session_from_rift_argv(["/usr/local/bin/rift", "attach", "x"]),
            "x",
        )

    def test_non_session_subcommands_ignored(self):
        for sub in ("list", "ls", "kill", "new", "detach", "version", "help", "last"):
            self.assertIsNone(
                rw.session_from_rift_argv(["rift", sub, "foo"]), sub
            )

    def test_non_rift_ignored(self):
        self.assertIsNone(rw.session_from_rift_argv(["vim", "attach", "x"]))

    def test_leading_flag_ignored(self):
        self.assertIsNone(rw.session_from_rift_argv(["rift", "--new", "top"]))

    def test_empty(self):
        self.assertIsNone(rw.session_from_rift_argv([]))


class CwdPath(unittest.TestCase):
    def test_file_url(self):
        self.assertEqual(
            rw.cwd_path("file://host/Users/me/repos/rift"),
            "/Users/me/repos/rift",
        )

    def test_percent_encoding(self):
        self.assertEqual(
            rw.cwd_path("file://host/Users/me/my%20dir"),
            "/Users/me/my dir",
        )

    def test_plain_path(self):
        self.assertEqual(rw.cwd_path("/tmp/x"), "/tmp/x")

    def test_empty(self):
        self.assertIsNone(rw.cwd_path(""))


def pane(session, x0, y0, cols, rows):
    return {
        "session": session,
        "cwd": None,
        "left_col": x0,
        "top_row": y0,
        "cols": cols,
        "rows": rows,
    }


def leaves(tree):
    if isinstance(tree, rw.Pane):
        return [tree.session]
    _, _, a, b = tree
    return leaves(a) + leaves(b)


class BuildTree(unittest.TestCase):
    def test_single(self):
        tree = rw.build_tree([rw.Pane(pane("a", 0, 0, 80, 24))])
        self.assertIsInstance(tree, rw.Pane)
        self.assertEqual(tree.session, "a")

    def test_side_by_side(self):
        # a | b  (vertical cut at col 40)
        panes = [rw.Pane(pane("a", 0, 0, 40, 24)), rw.Pane(pane("b", 40, 0, 40, 24))]
        tree = rw.build_tree(panes)
        self.assertEqual(tree[0], "right")
        self.assertEqual(leaves(tree), ["a", "b"])
        self.assertAlmostEqual(tree[1], 0.5, places=2)

    def test_stacked(self):
        # a over b (horizontal cut at row 12)
        panes = [rw.Pane(pane("a", 0, 0, 80, 12)), rw.Pane(pane("b", 0, 12, 80, 12))]
        tree = rw.build_tree(panes)
        self.assertEqual(tree[0], "bottom")
        self.assertEqual(leaves(tree), ["a", "b"])

    def test_three_pane_nested(self):
        # left column 'a' full height; right column split b (top) / c (bottom)
        panes = [
            rw.Pane(pane("a", 0, 0, 40, 24)),
            rw.Pane(pane("b", 40, 0, 40, 12)),
            rw.Pane(pane("c", 40, 12, 40, 12)),
        ]
        tree = rw.build_tree(panes)
        self.assertEqual(tree[0], "right")
        self.assertEqual(leaves(tree), ["a", "b", "c"])
        # right subtree is a vertical stack
        right = tree[3]
        self.assertEqual(right[0], "bottom")
        self.assertEqual(leaves(right), ["b", "c"])

    def test_ratio_uneven(self):
        # a is 60 cols, b is 20 cols -> second subtree gets 25%
        panes = [rw.Pane(pane("a", 0, 0, 60, 24)), rw.Pane(pane("b", 60, 0, 20, 24))]
        tree = rw.build_tree(panes)
        self.assertEqual(tree[0], "right")
        self.assertAlmostEqual(tree[1], 0.25, places=2)


class RealizeOrder(unittest.TestCase):
    def test_split_commands_for_three_panes(self):
        panes = [
            rw.Pane(pane("a", 0, 0, 40, 24)),
            rw.Pane(pane("b", 40, 0, 40, 12)),
            rw.Pane(pane("c", 40, 12, 40, 12)),
        ]
        tree = rw.build_tree(panes)
        calls = []
        counter = [100]

        def fake_run(cmd, dry):
            calls.append(cmd)
            counter[0] += 1
            return str(counter[0])

        first = rw.top_left_leaf(tree)
        self.assertEqual(first.session, "a")
        rw.realize(tree, "10", fake_run, dry=False)
        # Two splits for three panes.
        self.assertEqual(len(calls), 2)
        # First split: 'a' pane (id 10) split right, running rift attach b.
        self.assertIn("--right", calls[0])
        self.assertEqual(calls[0][-3:], ["rift", "attach", "b"])
        self.assertIn("10", calls[0])
        # Second split: within the right subtree, split bottom running attach c.
        self.assertIn("--bottom", calls[1])
        self.assertEqual(calls[1][-3:], ["rift", "attach", "c"])


if __name__ == "__main__":
    unittest.main()
