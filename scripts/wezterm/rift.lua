-- rift keybindings for WezTerm.
--
-- Add to ~/.wezterm.lua (or require this file from it). Adjust the key
-- assignments to taste. Requires `rift`, `rift-pane`, and the
-- `rift-wezterm` tool (scripts/wezterm/rift-wezterm) on PATH.
--
-- What you get:
--   CMD+SHIFT+t / CMD+SHIFT+Enter  new tab / split running a fresh rift session
--   CMD+SHIFT+s                    save the current window's rift panes as a layout
--   CMD+SHIFT+r                    restore the "default" rift layout
--
-- Layouts are stored under $RIFT_DIR/wezterm (default ~/.local/state/rift).

local wezterm = require("wezterm")
local act = wezterm.action

local M = {}

-- Spawn `rift-pane` (allocates the next free <cwd-basename>.<N> session and
-- attaches) in a new tab or split, inheriting the source pane's cwd.
local function rift_pane_args()
  return { "rift-pane" }
end

function M.apply(config)
  config.keys = config.keys or {}

  local keys = {
    {
      key = "t",
      mods = "CMD|SHIFT",
      action = act.SpawnCommandInNewTab({ args = rift_pane_args() }),
    },
    {
      key = "Enter",
      mods = "CMD|SHIFT",
      action = act.SplitHorizontal({ args = rift_pane_args() }),
    },
    {
      key = "s",
      mods = "CMD|SHIFT",
      action = act.PromptInputLine({
        description = "Save rift layout as:",
        action = wezterm.action_callback(function(window, pane, line)
          if not line or line == "" then
            return
          end
          wezterm.background_child_process({ "rift-wezterm", "save", line })
          window:toast_notification("rift", "saved layout '" .. line .. "'", nil, 3000)
        end),
      }),
    },
    {
      key = "r",
      mods = "CMD|SHIFT",
      action = act.PromptInputLine({
        description = "Restore rift layout (name, default 'default'):",
        action = wezterm.action_callback(function(window, pane, line)
          local name = (line == nil or line == "") and "default" or line
          wezterm.background_child_process({ "rift-wezterm", "restore", name })
        end),
      }),
    },
  }

  for _, k in ipairs(keys) do
    table.insert(config.keys, k)
  end
end

return M
