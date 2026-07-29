# scripts/

End-to-end integration recipe for using rift with Kitty and SSH. The scoped
kitten opens a local or remote rift pane without global remote-control
permission. Kitty 0.43 or newer saves and restores matching rift panes using
its native session format.

## Layout

| Path | Purpose |
|---|---|
| `rift-pane` | Allocates the next free `<basename($PWD)>.<N>` session and attaches. Lives in `~/.local/bin/` or `~/.bin/`. |
| `kitty/rift_spawn.py` | No-UI Kitty kitten: detects whether the source pane is ssh'd and launches `rift-pane` locally or through the same SSH client. Lives in `~/.config/kitty/`. |
| `kitty/bindings.conf` | The lines to add to `~/.config/kitty/kitty.conf`. |
| `fish/conf.d/rift-autostart.fish` | Optional compatibility hook for workflows that still launch a cloned shell with `RIFT_AUTOSTART=1`. |
| `fish/functions/r.fish` | `r <host> [project]` — attach to a rift pane on a remote host from a cold local shell. |
| `fish/functions/rift-restore.fish` | `rift-restore [host]` — open a local tab (or split with `--split`) for each rift session, local or on the remote. |
| `fish/functions/rift-pick.fish` | `rift-pick [host]` — fzf-pick a session and attach in a new tab/split. Picking `foo.<N>` also restores siblings (`--single` to disable). |
| `fish/functions/rift-snapshot.fish` | Legacy pre-Kitty-0.43 snapshot command; requires remote control. |
| `fish/functions/rift-load-snapshot.fish` | Legacy pre-Kitty-0.43 snapshot loader. |
| `kitty/rift-snapshot.py` | Legacy converter used by `rift-snapshot`. |
| `bash/rift-autostart.bash` | The equivalent autostart hook for remote bash. Append to the *top* of `~/.bashrc` on every host you ssh into. |
| `bash/rift-aliases.bash` | The complete set of bash aliases and functions. |

## Install (one-time, per machine)

```bash
# rift binary (built locally)
just install                                  # → ~/.local/bin/rift

# rift-pane script
install -m 0755 scripts/rift-pane ~/.local/bin/

# kitty kitten + bindings
cp scripts/kitty/rift_spawn.py ~/.config/kitty/
cat scripts/kitty/bindings.conf >> ~/.config/kitty/kitty.conf

# optional shell helpers
ln -s "$PWD/scripts/fish/functions/r.fish"                ~/.config/fish/functions/
ln -s "$PWD/scripts/fish/functions/rift-restore.fish"     ~/.config/fish/functions/
ln -s "$PWD/scripts/fish/functions/rift-pick.fish"        ~/.config/fish/functions/

# bash (if you use bash instead of fish)
# ln -s "$PWD/scripts/bash/rift-aliases.bash"            ~/.bash_aliases

# on each remote you ssh into:
scp scripts/rift-pane <host>:~/.local/bin/
ssh <host> chmod +x ~/.local/bin/rift-pane
# (also ensure `rift` itself is built/installed on the remote and on the
#  login PATH; check with `ssh <host> 'bash -lc "which rift rift-pane"'`)
```

## Reload

Restart Kitty to load the bindings. The core kitten does not require
`allow_remote_control` or `allow_cloning`.

## Daily use

| Where you are | Press | What you get |
|---|---|---|
| Local kitty pane (any cwd) | `cmd+shift+t` / `cmd+shift+enter` | New local tab/split, fresh rift session named `<cwd>.<N>` |
| Local kitty pane, ssh'd into a host | same | New local tab/split, SSH'd back, fresh rift session on the remote |
| Save rift pane layouts | `cmd+shift+s` | Prompt for a native Kitty session file under `~/.local/state/rift/sessions` |
| Restore a saved layout | `cmd+shift+r` | Browse native Kitty sessions and activate one |
| Cold local shell (no kitty pane needed) | `r <host>` | SSH + new rift session |
| After a local reboot | `rift-restore <host>` | One local tab per existing remote session |
| Want to grab one specific session | `rift-pick [host]` | fzf prompt; picking `foo.N` brings back all `foo.*` siblings |

## Notes

- The kitten extracts the remote host from the running ssh process's argv.
  It recognises plain `ssh` and preserves Kitty's `kitten ssh` client.
- Native saves use `--match=cmdline:rift`, so unrelated panes and foreground
  commands are excluded from the saved session.
- Remote cwd is *not* preserved when spawning a sibling SSH'd pane —
  rift-pane on the remote uses `$HOME`'s basename for the session name.
- `RIFT_DIR` defaults to `$HOME/.local/state/rift`, so sessions are visible
  the same way from any shell on the host (no macOS `$TMPDIR` confusion).
- The legacy `rift-snapshot`, `rift-load-snapshot`, `rift-restore`, and
  `rift-pick` shell helpers use `kitten @` and therefore require separately
  configured remote-control access.
