//! Tracked environment variables.
//!
//! When a client attaches it sends a snapshot of a configurable set of
//! environment variables (`RIFT_TRACK_ENV`, or a built-in default list) to the
//! daemon. The daemon keeps the leader client's snapshot so `rift print-env`
//! can report the environment the interactive session is running under —
//! useful for reconnecting GUI/SSH/terminal integrations (`DISPLAY`,
//! `SSH_AUTH_SOCK`, `KITTY_WINDOW_ID`, …) from tools running inside the
//! session.
//!
//! Wire format (mirrors zmx): newline-separated lines, one per tracked key.
//! A set variable is `KEY=VALUE`; a variable that was unset in the client's
//! environment is `-KEY` so the reader can emit `unset KEY` in shell mode.

/// Default set of environment variables to track, matching zmx's defaults.
pub const DEFAULT_TRACKED: &[&str] = &[
    "DISPLAY",
    "SSH_AUTH_SOCK",
    "SSH_AGENT_PID",
    "SSH_CONNECTION",
    "WINDOWID",
    "XAUTHORITY",
    "KITTY_LISTEN_ON",
    "KITTY_PID",
    "KITTY_WINDOW_ID",
];

/// The list of keys to track: `RIFT_TRACK_ENV` (comma-separated) if set,
/// otherwise the built-in defaults.
pub fn tracked_keys() -> Vec<String> {
    match std::env::var("RIFT_TRACK_ENV") {
        Ok(value) => value
            .split(',')
            .map(str::trim)
            .filter(|key| !key.is_empty())
            .map(str::to_string)
            .collect(),
        Err(_) => DEFAULT_TRACKED.iter().map(|key| key.to_string()).collect(),
    }
}

/// Build the wire payload from the current process environment for `keys`.
pub fn snapshot(keys: &[String]) -> String {
    let mut out = String::new();
    for key in keys {
        if key.is_empty() {
            continue;
        }
        match std::env::var(key) {
            Ok(value) => {
                out.push_str(key);
                out.push('=');
                out.push_str(&value);
                out.push('\n');
            }
            Err(_) => {
                out.push('-');
                out.push_str(key);
                out.push('\n');
            }
        }
    }
    out
}

/// A single tracked entry decoded from the wire payload.
#[derive(Debug, PartialEq, Eq)]
pub struct Entry<'a> {
    pub key: &'a str,
    /// `Some(value)` when set in the client, `None` when it was unset.
    pub value: Option<&'a str>,
}

/// Iterate the entries encoded in `payload`.
pub fn entries(payload: &str) -> impl Iterator<Item = Entry<'_>> {
    payload.lines().filter_map(|line| {
        if line.is_empty() {
            None
        } else if let Some(key) = line.strip_prefix('-') {
            Some(Entry { key, value: None })
        } else if let Some((key, value)) = line.split_once('=') {
            Some(Entry {
                key,
                value: Some(value),
            })
        } else {
            None
        }
    })
}

/// Look up a single key's value in `payload`. Returns `None` if the key is
/// absent or was unset in the client's environment.
pub fn value_of<'a>(payload: &'a str, key: &str) -> Option<&'a str> {
    entries(payload)
        .find(|entry| entry.key == key)
        .and_then(|entry| entry.value)
}

/// Render `payload` as POSIX `export`/`unset` statements for `eval`.
pub fn to_shell(payload: &str) -> String {
    let mut out = String::new();
    for entry in entries(payload) {
        match entry.value {
            Some(value) => {
                out.push_str("export ");
                out.push_str(entry.key);
                out.push_str("='");
                // Single-quote escaping: close, insert an escaped quote, reopen.
                out.push_str(&value.replace('\'', "'\\''"));
                out.push_str("';\n");
            }
            None => {
                out.push_str("unset ");
                out.push_str(entry.key);
                out.push_str(";\n");
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tracked_keys_defaults_when_unset() {
        // Note: relies on RIFT_TRACK_ENV being unset in the test environment.
        unsafe {
            std::env::remove_var("RIFT_TRACK_ENV");
        }
        let keys = tracked_keys();
        assert!(keys.iter().any(|k| k == "SSH_AUTH_SOCK"));
        assert_eq!(keys.len(), DEFAULT_TRACKED.len());
    }

    #[test]
    fn snapshot_marks_set_and_unset() {
        unsafe {
            std::env::set_var("RIFT_ENV_TEST_SET", "hello");
            std::env::remove_var("RIFT_ENV_TEST_MISSING");
        }
        let payload = snapshot(&[
            "RIFT_ENV_TEST_SET".to_string(),
            "RIFT_ENV_TEST_MISSING".to_string(),
        ]);
        assert_eq!(payload, "RIFT_ENV_TEST_SET=hello\n-RIFT_ENV_TEST_MISSING\n");
    }

    #[test]
    fn entries_roundtrip() {
        let payload = "DISPLAY=:1\n-WINDOWID\nSSH_AUTH_SOCK=/tmp/ssh\n";
        let got: Vec<Entry> = entries(payload).collect();
        assert_eq!(
            got,
            vec![
                Entry {
                    key: "DISPLAY",
                    value: Some(":1")
                },
                Entry {
                    key: "WINDOWID",
                    value: None
                },
                Entry {
                    key: "SSH_AUTH_SOCK",
                    value: Some("/tmp/ssh")
                },
            ]
        );
    }

    #[test]
    fn value_of_handles_set_unset_absent() {
        let payload = "DISPLAY=:1\n-WINDOWID\n";
        assert_eq!(value_of(payload, "DISPLAY"), Some(":1"));
        assert_eq!(value_of(payload, "WINDOWID"), None);
        assert_eq!(value_of(payload, "NOPE"), None);
    }

    #[test]
    fn shell_mode_exports_and_unsets_with_escaping() {
        let payload = "DISPLAY=:1\n-WINDOWID\nWEIRD=a'b\n";
        let shell = to_shell(payload);
        assert!(shell.contains("export DISPLAY=':1';\n"));
        assert!(shell.contains("unset WINDOWID;\n"));
        assert!(shell.contains("export WEIRD='a'\\''b';\n"));
    }
}
