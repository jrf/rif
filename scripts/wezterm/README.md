# scripts/wezterm/

WezTerm layout save/restore for rift, mirroring what `scripts/kitty` does with
Kitty 0.43's native sessions. WezTerm has no built-in session format, so
`rift-wezterm` reconstructs the split geometry itself.

## Layout

| Path | Purpose |
|---|---|
| `rift-wezterm` | `save` / `restore` / `list` rift-pane layouts. Install into `~/.local/bin/`. |
| `rift.lua` | WezTerm config module adding `CMD+SHIFT+t/Enter/s/r` keybindings. `require` it from `~/.wezterm.lua`. |
| `test_rift_wezterm.py` | Unit tests for the argv/cwd parsing and split-tree reconstruction. |

`rift-wezterm` also relies on `rift-pane` (from `scripts/`) for spawning fresh
sessions; keep both on `PATH`.

## How it works

WezTerm's `wezterm cli list --format json` reports each pane's rectangle
(`left_col`, `top_row`, `size.cols`, `size.rows`), tab, window, and
`tty_name` — but **not** the pane's command. So, analogous to Kitty's
`--match=cmdline:rift`, `save` identifies rift panes by scanning each pane's
controlling tty (`ps -t <tty>`) for a `rift attach <name>` client and records
which session sits in which rectangle.

`restore` reduces each tab's rectangles to a binary guillotine split tree,
then replays it with `wezterm cli spawn`/`split-pane --percent`, running
`rift attach <name>` in every pane. Because the rift daemons kept the shells
alive, each pane reconnects and replays its scrollback — geometry from
WezTerm, live process state from rift.

## Install

```bash
# tools (rift + rift-pane installed per scripts/README.md)
install -m 0755 scripts/wezterm/rift-wezterm ~/.local/bin/

# keybindings: in ~/.wezterm.lua
#   local rift = dofile(os.getenv("HOME") .. "/repos/rift/scripts/wezterm/rift.lua")
#   rift.apply(config)
```

Or drive it manually / from your own bindings:

```bash
rift-wezterm save work        # snapshot current rift panes -> work.json
rift-wezterm list             # list saved layouts
rift-wezterm restore work     # rebuild the layout in a new window
rift-wezterm restore work --dry-run   # print the wezterm commands only
```

Layouts are stored under `$RIFT_DIR/wezterm` (default
`~/.local/state/rift/wezterm`), the same `RIFT_DIR` rift itself uses.

## Daily use

| Where you are | Press | What you get |
|---|---|---|
| Any WezTerm pane | `CMD+SHIFT+t` / `CMD+SHIFT+Enter` | New tab/split running a fresh `<cwd>.<N>` rift session |
| Window with rift panes | `CMD+SHIFT+s` | Prompt for a layout name; saves the rift panes' geometry |
| Anywhere | `CMD+SHIFT+r` | Prompt for a layout name; rebuilds it in a new window |

## Notes

- Detection is by tty command line, so unrelated panes (editors, plain
  shells) are excluded from a save, just like Kitty's `--match`.
- `restore` builds each saved window as a fresh WezTerm window. Split ratios
  are approximate (WezTerm splits by percentage of available space, and
  rounding compounds across nested splits).
- Only tiled (guillotine-splittable) layouts are reconstructable; that covers
  every layout WezTerm itself can produce with splits.
- Remote/SSH panes are saved by their local rift session name; cross-host
  restore is out of scope here (see the Kitty kitten for SSH spawning).

## Tests

```bash
python3 scripts/wezterm/test_rift_wezterm.py
```
