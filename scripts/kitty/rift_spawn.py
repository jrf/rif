"""No-UI Kitty kitten: spawn a new rift-attached tab or split.

If the source pane is local, launch rift-pane directly with --cwd=current.

If the source pane is running ssh (or kitty's ssh kitten wrapping ssh): open
a new local pane that SSHs back to the same host and execs rift-pane on the
remote. Remote cwd is not preserved.

Save as ~/.config/kitty/rift_spawn.py and bind from kitty.conf with:
    map cmd+shift+t      kitten rift_spawn.py tab
    map cmd+shift+enter  kitten rift_spawn.py split
"""

import os

from kittens.tui.handler import result_handler


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    win = boss.window_id_map.get(target_window_id)
    if win is None:
        return

    is_split = len(args) > 1 and args[1] == "split"
    placement = ["--location=split"] if is_split else ["--type=tab"]

    ssh_cmd = _build_ssh_relaunch(win)
    launch = ["launch", f"--match=id:{win.id}", *placement]
    if ssh_cmd is not None:
        boss.call_remote_control(win, (*launch, "--", *ssh_cmd))
        return

    boss.call_remote_control(
        win,
        (*launch, "--cwd=current", "--", "rift-pane"),
    )


# Single-letter ssh flags that consume the next argv token.
_SSH_FLAGS_WITH_VALUE = {
    "-B",
    "-b",
    "-c",
    "-D",
    "-E",
    "-e",
    "-F",
    "-I",
    "-i",
    "-J",
    "-L",
    "-l",
    "-m",
    "-O",
    "-o",
    "-p",
    "-Q",
    "-R",
    "-S",
    "-W",
    "-w",
}


def _build_ssh_relaunch(win):
    """If the source pane is running ssh, return an argv that re-runs ssh to
    the same host and execs rift-pane there. Otherwise None."""
    for proc in win.child.foreground_processes or []:
        cmdline = proc.get("cmdline") or []
        if not cmdline:
            continue
        name = os.path.basename(cmdline[0])
        if name == "kitten" and len(cmdline) >= 2 and cmdline[1] == "ssh":
            command = cmdline[:2]
            command_args = cmdline[2:]
        elif name != "ssh" and not name.endswith("-ssh"):
            continue
        else:
            command = [cmdline[0]]
            command_args = cmdline[1:]

        head = list(command)
        host = None
        i = 0
        while i < len(command_args):
            a = command_args[i]
            if a in _SSH_FLAGS_WITH_VALUE and i + 1 < len(command_args):
                head += [a, command_args[i + 1]]
                i += 2
                continue
            if a.startswith("-"):
                head.append(a)
                i += 1
                continue
            host = a
            break
        if host is None:
            return None
        if not any(x in ("-t", "-tt") for x in head):
            head.append("-t")
        return [*head, host, "bash", "-lc", "rift-pane"]
    return None
