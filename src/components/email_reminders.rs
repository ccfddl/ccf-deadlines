use crate::components::favorites::api_url;
use crate::components::timezone::get_timezone_name_or_utc;
use gloo_net::http::Request;
use leptos::prelude::*;
use serde::Deserialize;
use thaw::*;
use wasm_bindgen_futures::spawn_local;
use web_sys::window;

const TIMEZONES: &[&str] = &[
    "UTC",
    "Pacific/Honolulu",
    "America/Los_Angeles",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Africa/Cairo",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Bangkok",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Pacific/Auckland",
];

#[derive(Clone, Deserialize)]
struct ReminderSettings {
    available: bool,
    enabled: bool,
    email: Option<String>,
    timezone: Option<String>,
    language: Option<String>,
    #[serde(default)]
    daily_enabled: bool,
}

async fn load_settings() -> Result<ReminderSettings, String> {
    let response = Request::get(&api_url("/api/email/reminders"))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(format!("HTTP {}", response.status()));
    }
    response.json().await.map_err(|error| error.to_string())
}

async fn save_settings(
    timezone: &str,
    language: &str,
    daily_enabled: bool,
) -> Result<ReminderSettings, String> {
    let response = Request::put(&api_url("/api/email/reminders"))
        .json(&serde_json::json!({ "timezone": timezone, "language": language, "daily_enabled": daily_enabled }))
        .map_err(|error| error.to_string())?
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(format!("HTTP {}", response.status()));
    }
    response.json().await.map_err(|error| error.to_string())
}

async fn disable_reminders() -> Result<(), String> {
    let response = Request::delete(&api_url("/api/email/reminders"))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if response.ok() {
        Ok(())
    } else {
        Err(format!("HTTP {}", response.status()))
    }
}

fn authorize_email(timezone: &str, language: &str) {
    let url = format!(
        "{}?purpose=email&timezone={}&language={}&return_to={}",
        api_url("/api/auth/github"),
        urlencoding::encode(timezone),
        urlencoding::encode(language),
        urlencoding::encode("/?email_reminders=1"),
    );
    if let Some(browser) = window() {
        let _ = browser.location().set_href(&url);
    }
}

#[component]
pub fn EmailReminderModal(show: RwSignal<bool>, use_english: RwSignal<bool>) -> impl IntoView {
    let settings = RwSignal::new(None::<ReminderSettings>);
    let timezone = RwSignal::new(get_timezone_name_or_utc());
    let language = RwSignal::new(if use_english.get_untracked() {
        "en".to_string()
    } else {
        "zh".to_string()
    });
    let loading = RwSignal::new(false);
    let busy = RwSignal::new(false);
    let error = RwSignal::new(None::<String>);
    let saved = RwSignal::new(false);
    let mut options: Vec<String> = TIMEZONES.iter().map(|value| (*value).to_string()).collect();
    if !options.contains(&timezone.get_untracked()) {
        options.push(timezone.get_untracked());
    }
    options.sort();
    let options = RwSignal::new(options);

    Effect::new(move |_| {
        if !show.get() {
            return;
        }
        loading.set(true);
        error.set(None);
        saved.set(false);
        spawn_local(async move {
            match load_settings().await {
                Ok(value) => {
                    if let Some(zone) = &value.timezone {
                        timezone.set(zone.clone());
                        if !options.with_untracked(|items| items.contains(zone)) {
                            options.update(|items| {
                                items.push(zone.clone());
                                items.sort();
                            });
                        }
                    }
                    if let Some(lang) = &value.language {
                        language.set(lang.clone());
                    }
                    settings.set(Some(value));
                }
                Err(message) => error.set(Some(message)),
            }
            loading.set(false);
        });
    });

    let status = window()
        .and_then(|browser| browser.location().search().ok())
        .unwrap_or_default();

    view! {
        <Dialog open=show>
            <DialogSurface class="conference-detail-dialog email-reminder-dialog">
                <DialogBody>
                    <DialogTitle class="conference-detail-title">
                        <Icon icon=icondata::BsEnvelope />
                        <span>{move || if use_english.get() { "Email Reminders" } else { "邮件提醒" }}</span>
                    </DialogTitle>
                    <button type="button" class="conference-detail-close"
                        aria-label=move || if use_english.get() { "Close" } else { "关闭" }
                        on:click=move |_| show.set(false)>"×"</button>
                    <DialogContent>
                        <p class="email-reminder-intro">{move || {
                            let daily = settings.get().is_some_and(|value| value.daily_enabled);
                            match (use_english.get(), daily) {
                                (true, true) => "One email each day at 9 AM (selected time zone) with all upcoming deadlines from starred conferences.",
                                (false, true) => "每天上午 9 点（所选时区）汇总发送收藏会议所有尚未截止的节点。",
                                (true, false) => "One email at 9 AM (selected time zone), 7 and 1 days before starred deadlines.",
                                (false, false) => "收藏会议截止前 7 天、1 天，所选时区上午 9 点合并发送邮件。",
                            }
                        }}</p>
                        <p class="email-reminder-notice">{move || if use_english.get() {
                            "Free email delivery is limited, so some reminders may not be sent."
                        } else {
                            "邮件通知的免费额度有限，可能出现提醒未发出的情况。"
                        }}</p>
                        {move || if status.contains("email_status=denied") {
                            Some(view! { <p class="email-reminder-message">{if use_english.get() { "GitHub email access was not granted." } else { "未授予 GitHub 邮箱权限。" }}</p> })
                        } else if status.contains("email_status=email_unavailable") {
                            Some(view! { <p class="email-reminder-message">{if use_english.get() { "No verified primary GitHub email is available." } else { "GitHub 账号没有可用的已验证主邮箱。" }}</p> })
                        } else if status.contains("email_status=account_mismatch") {
                            Some(view! { <p class="email-reminder-message">{if use_english.get() { "Please authorize the GitHub account currently signed in." } else { "请授权当前登录的 GitHub 账号。" }}</p> })
                        } else { None }}
                        <Show when=move || !loading.get() fallback=move || view! { <p>{move || if use_english.get() { "Loading..." } else { "加载中……" }}</p> }>
                            {move || settings.get().map(|current| {
                                let enabled = current.enabled;
                                let daily_enabled = current.daily_enabled;
                                let daily_switch = RwSignal::new(daily_enabled);
                                view! {
                                    <div class="email-reminder-settings">
                                        {enabled.then(|| view! {
                                            <p>{move || if use_english.get() { "Sending to" } else { "发送到" }} " " <strong>{current.email.clone().unwrap_or_default()}</strong></p>
                                        })}
                                        <label>
                                            {move || if use_english.get() { "Time zone" } else { "时区" }}
                                            <select prop:value=move || timezone.get() on:change=move |event| timezone.set(event_target_value(&event))>
                                                {move || options.get().into_iter().map(|zone| view! { <option value=zone.clone()>{zone.clone()}</option> }).collect_view()}
                                            </select>
                                        </label>
                                        <label>
                                            {move || if use_english.get() { "Email language" } else { "邮件语言" }}
                                            <select prop:value=move || language.get() on:change=move |event| language.set(event_target_value(&event))>
                                                <option value="en">"English"</option>
                                                <option value="zh">"中文"</option>
                                            </select>
                                        </label>
                                        {enabled.then(|| view! {
                                            <div class="email-reminder-daily-option">
                                                <div class="el-switch email-reminder-daily-control"
                                                    class:email-reminder-daily-control--busy=move || busy.get()
                                                    on:change=move |_| {
                                                        if busy.get_untracked() {
                                                            daily_switch.set(daily_enabled);
                                                            return;
                                                        }
                                                        busy.set(true);
                                                        error.set(None);
                                                        saved.set(false);
                                                        spawn_local(async move {
                                                            match save_settings(&timezone.get_untracked(), &language.get_untracked(), !daily_enabled).await {
                                                                Ok(value) => settings.set(Some(value)),
                                                                Err(message) => {
                                                                    daily_switch.set(daily_enabled);
                                                                    error.set(Some(message));
                                                                }
                                                            }
                                                            busy.set(false);
                                                        });
                                                    }>
                                                    <Switch checked=daily_switch label=Signal::derive(move || if use_english.get() {
                                                        "Daily reminders (send an email every day when enabled)".to_string()
                                                    } else {
                                                        "🔥每日提醒 (开启后将每日进行邮件提醒)".to_string()
                                                    }) />
                                                </div>
                                            </div>
                                        })}
                                        {if enabled {
                                            view! {
                                                <div class="email-reminder-actions">
                                                    <button type="button" disabled=move || busy.get() on:click=move |_| {
                                                        busy.set(true);
                                                        error.set(None);
                                                        saved.set(false);
                                                        spawn_local(async move {
                                                            match save_settings(&timezone.get_untracked(), &language.get_untracked(), daily_enabled).await {
                                                                Ok(value) => { settings.set(Some(value)); saved.set(true); }
                                                                Err(message) => error.set(Some(message)),
                                                            }
                                                            busy.set(false);
                                                        });
                                                    }>{move || if use_english.get() { "Save time zone and language" } else { "保存时区和语言" }}</button>
                                                    <button type="button" disabled=move || busy.get() on:click=move |_| {
                                                        authorize_email(&timezone.get_untracked(), &language.get_untracked());
                                                    }>{move || if use_english.get() { "Refresh GitHub email" } else { "更新 GitHub 邮箱" }}</button>
                                                    <button type="button" disabled=move || busy.get() on:click=move |_| {
                                                        busy.set(true);
                                                        error.set(None);
                                                        spawn_local(async move {
                                                            match disable_reminders().await {
                                                                Ok(()) => match load_settings().await {
                                                                    Ok(value) => settings.set(Some(value)),
                                                                    Err(message) => error.set(Some(message)),
                                                                },
                                                                Err(message) => error.set(Some(message)),
                                                            }
                                                            busy.set(false);
                                                        });
                                                    }>{move || if use_english.get() { "Turn off all email reminders" } else { "关闭所有邮件提醒" }}</button>
                                                </div>
                                            }.into_any()
                                        } else if current.available {
                                            view! { <button type="button" class="email-reminder-enable" on:click=move |_| {
                                                authorize_email(&timezone.get_untracked(), &language.get_untracked());
                                            }>{move || if use_english.get() { "Authorize GitHub email and enable" } else { "授权 GitHub 邮箱并开启" }}</button> }.into_any()
                                        } else {
                                            view! { <p class="email-reminder-message">{move || if use_english.get() { "Email sending is not configured yet." } else { "邮件发送服务尚未配置。" }}</p> }.into_any()
                                        }}
                                    </div>
                                }
                            })}
                        </Show>
                        <Show when=move || saved.get()><p class="email-reminder-message">{move || if use_english.get() { "Time zone and email language saved." } else { "时区和邮件语言已保存。" }}</p></Show>
                        {move || error.get().map(|message| view! { <p class="email-reminder-message" role="alert">{message}</p> })}
                    </DialogContent>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    }
}
