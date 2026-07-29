import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_kitten():
    handler = types.ModuleType("kittens.tui.handler")

    def result_handler(**options):
        def decorate(function):
            function.result_handler_options = options
            return function

        return decorate

    handler.result_handler = result_handler
    sys.modules["kittens"] = types.ModuleType("kittens")
    sys.modules["kittens.tui"] = types.ModuleType("kittens.tui")
    sys.modules["kittens.tui.handler"] = handler

    path = Path(__file__).with_name("rift_spawn.py")
    spec = importlib.util.spec_from_file_location("rift_spawn", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Child:
    def __init__(self, processes):
        self.foreground_processes = processes


class Window:
    def __init__(self, processes):
        self.id = 42
        self.child = Child(processes)


class Boss:
    def __init__(self, window):
        self.window_id_map = {window.id: window}
        self.calls = []

    def call_remote_control(self, window, command):
        self.calls.append((window, command))


class RiftSpawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kitten = load_kitten()

    def test_handler_runs_without_an_overlay(self):
        self.assertEqual(
            self.kitten.handle_result.result_handler_options,
            {"no_ui": True},
        )

    def test_local_tab_launches_rift_pane_in_current_directory(self):
        window = Window([{"cmdline": ["fish"]}])
        boss = Boss(window)

        self.kitten.handle_result(["rift_spawn.py", "tab"], "", window.id, boss)

        self.assertEqual(
            boss.calls,
            [
                (
                    window,
                    (
                        "launch",
                        "--match=id:42",
                        "--type=tab",
                        "--cwd=current",
                        "--",
                        "rift-pane",
                    ),
                )
            ],
        )

    def test_split_relaunches_plain_ssh_with_options(self):
        window = Window([{"cmdline": ["ssh", "-F", "config", "-p", "2222", "devbox"]}])
        boss = Boss(window)

        self.kitten.handle_result(["rift_spawn.py", "split"], "", window.id, boss)

        self.assertEqual(
            boss.calls[0][1],
            (
                "launch",
                "--match=id:42",
                "--location=split",
                "--",
                "ssh",
                "-F",
                "config",
                "-p",
                "2222",
                "-t",
                "devbox",
                "bash",
                "-lc",
                "rift-pane",
            ),
        )

    def test_relaunch_preserves_kitty_ssh_kitten(self):
        window = Window([{"cmdline": ["kitten", "ssh", "-J", "jump", "devbox"]}])

        command = self.kitten._build_ssh_relaunch(window)

        self.assertEqual(
            command,
            [
                "kitten",
                "ssh",
                "-J",
                "jump",
                "-t",
                "devbox",
                "bash",
                "-lc",
                "rift-pane",
            ],
        )

    def test_bindings_use_filtered_native_sessions_without_global_control(self):
        bindings = Path(__file__).with_name("bindings.conf").read_text()

        self.assertNotIn("allow_remote_control yes", bindings)
        self.assertNotIn("allow_cloning yes", bindings)
        self.assertIn("save_as_session --save-only --use-foreground-process", bindings)
        self.assertIn("--match=cmdline:rift", bindings)
        self.assertIn("goto_session ~/.local/state/rift/sessions", bindings)


if __name__ == "__main__":
    unittest.main()
