use chrono_tz::Tz;
use std::str::FromStr;

// Get browser timezone name (e.g., "Asia/Shanghai", "America/New_York")
#[cfg(target_arch = "wasm32")]
pub fn get_timezone_name() -> Option<String> {
    web_sys::js_sys::eval("Intl.DateTimeFormat().resolvedOptions().timeZone")
        .ok()
        .and_then(|v| v.as_string())
}

#[cfg(not(target_arch = "wasm32"))]
pub fn get_timezone_name() -> Option<String> {
    std::env::var("TZ").ok()
}

// Get timezone name with fallback to "UTC"
#[allow(dead_code)]
pub fn get_timezone_name_or_utc() -> String {
    get_timezone_name().unwrap_or_else(|| "UTC".to_string())
}

// Get timezone name and validate it's supported by chrono-tz
#[allow(dead_code)]
pub fn get_supported_timezone() -> Option<Tz> {
    get_timezone_name()
        .and_then(|tz_name| Tz::from_str(&tz_name).ok())
}

// Get timezone name or return UTC timezone if not supported
#[allow(dead_code)]
pub fn get_timezone_or_utc() -> Tz {
    get_supported_timezone().unwrap_or(chrono_tz::UTC)
}
