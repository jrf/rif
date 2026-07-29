use std::collections::BTreeMap;

const RESERVED_KEYS: [&str; 3] = ["name", "start_dir", "cmd"];

pub fn parse_pair(pair: &str) -> Result<(&str, &str), String> {
    let Some((key, value)) = pair.split_once('=') else {
        return Err(format!("label must use key=value syntax: {pair}"));
    };
    validate(key, value)?;
    Ok((key, value))
}

pub fn validate_key(key: &str) -> Result<(), String> {
    validate(key, "")
}

fn validate(key: &str, value: &str) -> Result<(), String> {
    if key.is_empty() {
        return Err("label key cannot be empty".into());
    }
    if RESERVED_KEYS.contains(&key) {
        return Err(format!("\"{key}\" is a read-only built-in field"));
    }
    if !key.bytes().all(valid_character) {
        return Err(format!(
            "label key may only contain letters, numbers, '-', '_', and '.': {key}"
        ));
    }
    if !value.bytes().all(valid_character) {
        return Err(format!(
            "label value may only contain letters, numbers, '-', '_', and '.': {value}"
        ));
    }
    Ok(())
}

fn valid_character(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.')
}

pub fn encode(labels: &BTreeMap<String, String>) -> String {
    labels
        .iter()
        .map(|(key, value)| format!("{key}={value}"))
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn decode(labels: &str) -> BTreeMap<String, String> {
    labels
        .split_whitespace()
        .filter_map(|pair| {
            pair.split_once('=')
                .map(|(key, value)| (key.to_string(), value.to_string()))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn labels_are_validated() {
        assert_eq!(parse_pair("project=rift"), Ok(("project", "rift")));
        assert_eq!(parse_pair("env.prod=v1_2-3"), Ok(("env.prod", "v1_2-3")));
        assert!(parse_pair("missing-equals").is_err());
        assert!(parse_pair("bad key=value").is_err());
        assert!(parse_pair("key=bad value").is_err());
        assert!(parse_pair("name=reserved").is_err());
    }

    #[test]
    fn labels_encode_in_sorted_order() {
        let labels = BTreeMap::from([
            ("project".to_string(), "rift".to_string()),
            ("env".to_string(), "dev".to_string()),
        ]);
        assert_eq!(encode(&labels), "env=dev project=rift");
        assert_eq!(decode(&encode(&labels)), labels);
    }
}
