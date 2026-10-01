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
