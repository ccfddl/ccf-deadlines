use leptos::prelude::*;
use std::collections::HashSet;
use thaw::*;
use wasm_bindgen::prelude::*;
use web_sys::js_sys;
use web_sys::window;

#[derive(Clone, Debug, PartialEq)]
pub struct SubscriptionLink {
    pub url: String,
    pub description: String,
}

pub type IcsSubscription = SubscriptionLink;

fn sanitize_filter_value(value: &str) -> String {
    value.replace('*', "star")
}

fn format_rank_label(system: &str, rank: &str) -> String {
    match (system, rank) {
        ("CCF", "N") => "Non-CCF".to_string(),
        ("CORE", "N") => "Non-CORE".to_string(),
        ("THCPL", "N") => "Non-THCPL".to_string(),
        _ => format!("{} {}", system, rank),
    }
}

fn format_rank_summary_value(system: &str, rank: &str) -> String {
    match (system, rank) {
        ("CCF", "N") => "Non-CCF".to_string(),
        ("CORE", "N") => "Non-CORE".to_string(),
        ("THCPL", "N") => "Non-THCPL".to_string(),
        _ => rank.to_string(),
    }
}

fn sorted_values(values: &HashSet<String>) -> Vec<String> {
    let mut sorted: Vec<_> = values.iter().cloned().collect();
    sorted.sort();
    sorted
}

fn build_subscription_urls(
    base_url: &str,
    extension: &str,
    lang: &str,
    subs: &HashSet<String>,
    ccf_ranks: &HashSet<String>,
    core_ranks: &HashSet<String>,
    thcpl_ranks: &HashSet<String>,
) -> Vec<SubscriptionLink> {
    if subs.is_empty() && ccf_ranks.is_empty() && core_ranks.is_empty() && thcpl_ranks.is_empty() {
        return vec![SubscriptionLink {
            url: format!("{}/deadlines_{}.{}", base_url, lang, extension),
            description: if lang == "zh" {
                "所有会议".to_string()
            } else {
                "All Conferences".to_string()
            },
        }];
    }

    let sub_tokens: Vec<Option<(String, String)>> = if subs.is_empty() {
        vec![None]
    } else {
        sorted_values(subs)
            .into_iter()
            .map(|sub| Some((sub.clone(), sub)))
            .collect()
    };
    let ccf_tokens: Vec<Option<(String, String)>> = if ccf_ranks.is_empty() {
        vec![None]
    } else {
        sorted_values(ccf_ranks)
            .into_iter()
            .map(|rank| {
                Some((
                    format!("ccf_{}", sanitize_filter_value(&rank)),
                    format_rank_label("CCF", &rank),
                ))
            })
            .collect()
    };
    let core_tokens: Vec<Option<(String, String)>> = if core_ranks.is_empty() {
        vec![None]
    } else {
        sorted_values(core_ranks)
            .into_iter()
            .map(|rank| {
                Some((
                    format!("core_{}", sanitize_filter_value(&rank)),
                    format_rank_label("CORE", &rank),
                ))
            })
            .collect()
    };
    let thcpl_tokens: Vec<Option<(String, String)>> = if thcpl_ranks.is_empty() {
        vec![None]
    } else {
        sorted_values(thcpl_ranks)
            .into_iter()
            .map(|rank| {
                Some((
                    format!("thcpl_{}", sanitize_filter_value(&rank)),
                    format_rank_label("THCPL", &rank),
                ))
            })
            .collect()
    };

    let mut urls = Vec::new();

    for ccf in &ccf_tokens {
        for core in &core_tokens {
            for thcpl in &thcpl_tokens {
                for sub in &sub_tokens {
                    let mut filename_parts = vec![format!("deadlines_{}", lang)];
                    let mut description_parts = Vec::new();

                    if let Some((token, label)) = ccf {
                        filename_parts.push(token.clone());
                        description_parts.push(label.clone());
                    }
                    if let Some((token, label)) = core {
                        filename_parts.push(token.clone());
                        description_parts.push(label.clone());
                    }
                    if let Some((token, label)) = thcpl {
                        filename_parts.push(token.clone());
                        description_parts.push(label.clone());
                    }
                    if let Some((token, label)) = sub {
                        filename_parts.push(token.clone());
                        description_parts.push(label.clone());
                    }

                    if description_parts.is_empty() {
                        continue;
                    }

                    urls.push(SubscriptionLink {
                        url: format!("{}/{}.{}", base_url, filename_parts.join("_"), extension),
                        description: description_parts.join(" | "),
                    });
                }
            }
        }
    }

    urls
}

pub fn generate_ics_urls(
    lang: &str,
    subs: &HashSet<String>,
    ccf_ranks: &HashSet<String>,
    core_ranks: &HashSet<String>,
    thcpl_ranks: &HashSet<String>,
) -> Vec<IcsSubscription> {
    build_subscription_urls(
        "webcal://ccfddl.com/conference",
        "ics",
        lang,
        subs,
        ccf_ranks,
        core_ranks,
        thcpl_ranks,
    )
}

pub fn generate_rss_urls(
    lang: &str,
    subs: &HashSet<String>,
    ccf_ranks: &HashSet<String>,
    core_ranks: &HashSet<String>,
    thcpl_ranks: &HashSet<String>,
) -> Vec<SubscriptionLink> {
    build_subscription_urls(
        "https://ccfddl.com/conference",
        "xml",
        lang,
        subs,
        ccf_ranks,
        core_ranks,
        thcpl_ranks,
    )
}

fn copy_text_to_clipboard(text: &str) {
    if let Some(w) = window() {
        let nav: JsValue = w.navigator().into();
        if let Ok(clipboard) = js_sys::Reflect::get(&nav, &JsValue::from_str("clipboard")) {
            if !clipboard.is_undefined() && !clipboard.is_null() {
                if let Ok(write_fn) =
                    js_sys::Reflect::get(&clipboard, &JsValue::from_str("writeText"))
                {
                    let func: js_sys::Function = write_fn.unchecked_into();
                    let _ = func.call1(&clipboard, &JsValue::from_str(text));
                }
            }
        }
    }
}

fn get_platform_instruction(use_english: bool) -> String {
    if let Some(w) = window() {
        let ua = w.navigator().user_agent().unwrap_or_default();
        if ua.contains("iPhone") || ua.contains("iPad") {
            return if use_english {
                "iOS: Settings > Calendar > Accounts > Add Account > Other > Add Subscribed Calendar"
            } else {
                "iOS: 设置 > 日历 > 账户 > 添加账户 > 其他 > 添加已订阅的日历"
            }
            .to_string();
        } else if ua.contains("Android") {
            return if use_english {
                "Android: Google Calendar > Settings > Add calendar > From URL"
            } else {
                "Android: Google 日历 > 设置 > 添加日历 > 通过 URL"
            }
            .to_string();
        } else if ua.contains("Mac") {
            return if use_english {
                "macOS: Calendar app > File > New Calendar Subscription"
            } else {
                "macOS: 日历应用 > 文件 > 新建日历订阅"
            }
            .to_string();
        } else if ua.contains("Windows") {
            return if use_english {
                "Windows: Outlook > Calendar > Add Calendar > Subscribe from web"
            } else {
                "Windows: Outlook > 日历 > 添加日历 > 从 Web 订阅"
            }
            .to_string();
        }
    }
    if use_english {
        "Copy the link and paste it into your calendar app".to_string()
    } else {
        "复制链接并粘贴到日历应用的订阅功能中".to_string()
    }
}

fn render_filter_summary(
    subs: &HashSet<String>,
    ccf_ranks: &HashSet<String>,
    core_ranks: &HashSet<String>,
    thcpl_ranks: &HashSet<String>,
    use_english: bool,
) -> String {
    let mut parts = Vec::new();
    if !subs.is_empty() {
        let sorted = sorted_values(subs);
        let label = if use_english { "Categories" } else { "分类" };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if !ccf_ranks.is_empty() {
        let sorted = sorted_values(ccf_ranks)
            .into_iter()
            .map(|rank| format_rank_summary_value("CCF", &rank))
            .collect::<Vec<_>>();
        let label = if use_english {
            "CCF Ranks"
        } else {
            "CCF 等级"
        };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if !core_ranks.is_empty() {
        let sorted = sorted_values(core_ranks)
            .into_iter()
            .map(|rank| format_rank_summary_value("CORE", &rank))
            .collect::<Vec<_>>();
        let label = if use_english {
            "CORE Ranks"
        } else {
            "CORE 等级"
        };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if !thcpl_ranks.is_empty() {
        let sorted = sorted_values(thcpl_ranks)
            .into_iter()
            .map(|rank| format_rank_summary_value("THCPL", &rank))
            .collect::<Vec<_>>();
        let label = if use_english {
            "THCPL Ranks"
        } else {
            "THCPL 等级"
        };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if parts.is_empty() {
        if use_english {
            "All conferences".to_string()
        } else {
            "全部会议".to_string()
        }
    } else {
        parts.join(" · ")
    }
}

fn render_link_limit_message(link_count: usize, use_english: bool) -> String {
    if use_english {
        format!(
            "{} links generated. Narrow the filters or subscribe to all instead.",
            link_count
        )
    } else {
        format!(
            "已生成 {} 个链接。建议缩小筛选范围，或直接订阅全部。",
            link_count
        )
    }
}

#[component]
pub fn SubscriptionModal(
    show: RwSignal<bool>,
    use_english: RwSignal<bool>,
    check_list: RwSignal<HashSet<String>>,
    rank_list: RwSignal<HashSet<String>>,
    core_rank_list: RwSignal<HashSet<String>>,
    thcpl_rank_list: RwSignal<HashSet<String>>,
) -> impl IntoView {
    let subscriptions = Memo::new(move |_| {
        let lang = if use_english.get() { "en" } else { "zh" };
        let subs = check_list.get();
        let ranks = rank_list.get();
        let core_ranks = core_rank_list.get();
        let thcpl_ranks = thcpl_rank_list.get();
        generate_ics_urls(lang, &subs, &ranks, &core_ranks, &thcpl_ranks)
    });

    let rss_subscriptions = Memo::new(move |_| {
        let lang = if use_english.get() { "en" } else { "zh" };
        let subs = check_list.get();
        let ranks = rank_list.get();
        let core_ranks = core_rank_list.get();
        let thcpl_ranks = thcpl_rank_list.get();
        generate_rss_urls(lang, &subs, &ranks, &core_ranks, &thcpl_ranks)
    });

    let has_multiple_subscriptions = Memo::new(move |_| subscriptions.get().len() > 1);
    let platform_hint = Memo::new(move |_| get_platform_instruction(use_english.get()));

    view! {
        <Dialog open=show>
            <DialogSurface>
                <DialogBody>
                    <DialogTitle>
                        {move || {
                            if use_english.get() {
                                "Subscribe to Conference Deadlines"
                            } else {
                                "订阅会议截止日期"
                            }
                        }}
                    </DialogTitle>
                    <DialogContent>
                        <div style="margin-bottom: 16px; color: #666; font-size: 14px;">
                            {move || {
                                if use_english.get() {
                                    "These links are generated from the filters currently active on this page."
                                } else {
                                    "下面的链接会直接继承你当前页面的筛选条件。"
                                }
                            }}
                        </div>

                        <div style="margin-bottom: 16px; padding: 12px; background: #f5f7fa; border-radius: 8px; font-size: 13px;">
                            <div style="font-size: 12px; font-weight: 600; color: #606266; margin-bottom: 6px;">
                                {move || {
                                    if use_english.get() {
                                        "This subscription will include"
                                    } else {
                                        "本次订阅将包含"
                                    }
                                }}
                            </div>
                            <div style="color: #303133;">
                                {move || {
                                    let subs = check_list.get();
                                    let ranks = rank_list.get();
                                    let core_ranks = core_rank_list.get();
                                    let thcpl_ranks = thcpl_rank_list.get();
                                    let en = use_english.get();
                                    render_filter_summary(
                                        &subs,
                                        &ranks,
                                        &core_ranks,
                                        &thcpl_ranks,
                                        en,
                                    )
                                }}
                            </div>
                            <Show when=move || has_multiple_subscriptions.get()>
                                <div style="margin-top: 8px; font-size: 12px; color: #909399; line-height: 1.6;">
                                    {move || {
                                        if use_english.get() {
                                            "Multiple links are shown because the current filters expand into separate subscription combinations."
                                        } else {
                                            "当前筛选会拆分出多个订阅组合，因此这里会显示多个链接。"
                                        }
                                    }}
                                </div>
                            </Show>
                        </div>

                        <div style="margin-bottom: 16px;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">
                                {move || {
                                    if use_english.get() {
                                        "Calendar Subscription"
                                    } else {
                                        "日历订阅"
                                    }
                                }}
                            </div>
                            <div style="font-size: 12px; color: #909399; margin-bottom: 10px; line-height: 1.6;">
                                {move || {
                                    if use_english.get() {
                                        "Use these webcal links in Apple Calendar, Outlook, Google Calendar, or any app that supports calendar subscriptions."
                                    } else {
                                        "将这些 webcal 链接粘贴到支持订阅日历的应用中，例如 Apple 日历、Outlook、Google 日历等。"
                                    }
                                }}
                            </div>

                            {move || {
                                let subs = subscriptions.get();
                                if subs.len() > 10 {
                                    let msg = render_link_limit_message(subs.len(), use_english.get());
                                    view! {
                                        <div style="color: #e6a23c; padding: 8px; background: #fdf6ec; border-radius: 4px; font-size: 13px;">
                                            {msg}
                                        </div>
                                    }
                                        .into_any()
                                } else {
                                    view! {
                                        <div>
                                            {subs
                                                .iter()
                                                .enumerate()
                                                .map(|(idx, sub)| {
                                                    let url = sub.url.clone();
                                                    let url_for_copy = url.clone();
                                                    let desc = sub.description.clone();
                                                    let label = format!("{}. {}", idx + 1, desc);
                                                    view! {
                                                        <div style="margin-bottom: 12px; padding: 10px; border: 1px solid #dcdfe6; border-radius: 6px; background: white;">
                                                            <div style="font-size: 13px; color: #333; margin-bottom: 6px; font-weight: 500;">
                                                                {label}
                                                            </div>
                                                            <div style="display: flex; align-items: center; gap: 8px;">
                                                                <input
                                                                    type="text"
                                                                    readonly
                                                                    value=url
                                                                    style="flex: 1; padding: 6px 8px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 12px; font-family: monospace; background: #f5f7fa; outline: none;"
                                                                />
                                                                <Button
                                                                    size=ButtonSize::Small
                                                                    on_click=move |_| {
                                                                        copy_text_to_clipboard(&url_for_copy);
                                                                    }
                                                                >
                                                                    {move || {
                                                                        if use_english.get() { "Copy" } else { "复制" }
                                                                    }}
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    }
                                                })
                                                .collect::<Vec<_>>()}
                                        </div>
                                    }
                                        .into_any()
                                }
                            }}

                            <div style="font-size: 12px; color: #909399; margin-top: 6px; line-height: 1.6;">
                                {move || {
                                    if use_english.get() {
                                        "Copy one link, then paste it into your calendar app's \"Subscribe by URL\" entry."
                                    } else {
                                        "复制一个链接，然后粘贴到日历应用的“通过 URL 订阅”入口。"
                                    }
                                }}
                            </div>
                        </div>

                        <div style="margin-bottom: 16px;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">
                                {move || {
                                    if use_english.get() {
                                        "RSS Feed"
                                    } else {
                                        "RSS 订阅："
                                    }
                                }}
                            </div>
                            <div style="font-size: 12px; color: #909399; margin-bottom: 10px; line-height: 1.6;">
                                {move || {
                                    if use_english.get() {
                                        "Use RSS if you prefer deadline updates in an RSS reader instead of a calendar app."
                                    } else {
                                        "如果你更习惯用 RSS 阅读器跟踪截止日期更新，可以使用下面的 RSS 链接。"
                                    }
                                }}
                            </div>

                            {move || {
                                let subs = rss_subscriptions.get();
                                if subs.len() > 10 {
                                    let msg = render_link_limit_message(subs.len(), use_english.get());
                                    view! {
                                        <div style="color: #e6a23c; padding: 8px; background: #fdf6ec; border-radius: 4px; font-size: 13px;">
                                            {msg}
                                        </div>
                                    }
                                        .into_any()
                                } else {
                                    view! {
                                        <div>
                                            {subs
                                                .iter()
                                                .enumerate()
                                                .map(|(idx, sub)| {
                                                    let url = sub.url.clone();
                                                    let url_for_copy = url.clone();
                                                    let desc = sub.description.clone();
                                                    let label = format!("{}. {}", idx + 1, desc);
                                                    view! {
                                                        <div style="margin-bottom: 12px; padding: 10px; border: 1px solid #dcdfe6; border-radius: 6px; background: white;">
                                                            <div style="font-size: 13px; color: #333; margin-bottom: 6px; font-weight: 500;">
                                                                {label}
                                                            </div>
                                                            <div style="display: flex; align-items: center; gap: 8px;">
                                                                <input
                                                                    type="text"
                                                                    readonly
                                                                    value=url
                                                                    style="flex: 1; padding: 6px 8px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 12px; font-family: monospace; background: #f5f7fa; outline: none;"
                                                                />
                                                                <Button
                                                                    size=ButtonSize::Small
                                                                    on_click=move |_| {
                                                                        copy_text_to_clipboard(&url_for_copy);
                                                                    }
                                                                >
                                                                    {move || {
                                                                        if use_english.get() { "Copy" } else { "复制" }
                                                                    }}
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    }
                                                })
                                                .collect::<Vec<_>>()}
                                        </div>
                                    }
                                        .into_any()
                                }
                            }}

                            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                {move || {
                                    if use_english.get() {
                                        "Paste the copied link into your RSS reader."
                                    } else {
                                        "将复制的链接粘贴到 RSS 阅读器中。"
                                    }
                                }}
                            </div>
                        </div>

                        <div style="padding: 12px; background: #ecf5ff; border-radius: 8px; border-left: 4px solid #409eff;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px; color: #409eff;">
                                {move || {
                                    if use_english.get() {
                                        "Quick tip"
                                    } else {
                                        "使用提示"
                                    }
                                }}
                            </div>
                            <div style="font-size: 13px; line-height: 1.8; color: #606266;">
                                {move || {
                                    if use_english.get() {
                                        view! {
                                            <div>
                                                <div>"Copy one link and paste it into your calendar app's Subscribe by URL entry."</div>
                                                <div>"If multiple links appear, each link matches a different filter combination."</div>
                                            </div>
                                        }
                                            .into_any()
                                    } else {
                                        view! {
                                            <div>
                                                <div>"复制一个链接，并粘贴到日历应用的“通过 URL 订阅”入口。"</div>
                                                <div>"如果这里出现多个链接，表示每个链接对应一个不同的筛选组合。"</div>
                                            </div>
                                        }
                                            .into_any()
                                    }
                                }}
                            </div>
                            <div style="margin-top: 8px; font-size: 12px; color: #909399; font-style: italic;">
                                {move || platform_hint.get()}
                            </div>
                        </div>

                        <div style="margin-top: 12px; font-size: 12px; color: #909399; text-align: center;">
                            {move || {
                                if use_english.get() {
                                    "Subscribed calendars usually refresh every 12-24 hours."
                                } else {
                                    "订阅的日历通常每 12-24 小时刷新一次。"
                                }
                            }}
                        </div>
                    </DialogContent>
                    <DialogActions>
                        <Button
                            appearance=ButtonAppearance::Secondary
                            on_click=move |_| show.set(false)
                        >
                            {move || if use_english.get() { "Close" } else { "关闭" }}
                        </Button>
                    </DialogActions>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    }
}
