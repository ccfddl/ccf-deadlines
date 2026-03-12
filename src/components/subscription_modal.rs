use leptos::prelude::*;
use std::collections::HashSet;
use thaw::*;
use wasm_bindgen::prelude::*;
use web_sys::js_sys;
use web_sys::window;

#[derive(Clone, Debug, PartialEq)]
pub struct IcsSubscription {
    pub url: String,
    pub description: String,
}

pub fn generate_ics_urls(
    lang: &str,
    subs: &HashSet<String>,
    ranks: &HashSet<String>,
) -> Vec<IcsSubscription> {
    let base_url = "webcal://ccfddl.com/conference";
    let mut urls = Vec::new();

    if subs.is_empty() && ranks.is_empty() {
        urls.push(IcsSubscription {
            url: format!("{}/deadlines_{}.ics", base_url, lang),
            description: if lang == "zh" {
                "所有会议".to_string()
            } else {
                "All Conferences".to_string()
            },
        });
        return urls;
    }

    if !subs.is_empty() && !ranks.is_empty() {
        for sub in subs.iter() {
            for rank in ranks.iter() {
                let rank_prefix = get_rank_prefix(rank);
                urls.push(IcsSubscription {
                    url: format!(
                        "{}/deadlines_{}_{}_{}_{}.ics",
                        base_url, lang, rank_prefix, rank, sub
                    ),
                    description: format!("{} {} {}", sub, rank_prefix.to_uppercase(), rank),
                });
            }
        }
    } else if !subs.is_empty() {
        for sub in subs.iter() {
            urls.push(IcsSubscription {
                url: format!("{}/deadlines_{}_{}.ics", base_url, lang, sub),
                description: sub.clone(),
            });
        }
    } else if !ranks.is_empty() {
        for rank in ranks.iter() {
            let rank_prefix = get_rank_prefix(rank);
            urls.push(IcsSubscription {
                url: format!(
                    "{}/deadlines_{}_{}_{}.ics",
                    base_url, lang, rank_prefix, rank
                ),
                description: format!("{} {}", rank_prefix.to_uppercase(), rank),
            });
        }
    }

    urls
}

fn get_rank_prefix(rank: &str) -> &'static str {
    match rank {
        "A" | "B" | "C" | "N" => "ccf",
        _ => "ccf",
    }
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
    ranks: &HashSet<String>,
    use_english: bool,
) -> String {
    let mut parts = Vec::new();
    if !subs.is_empty() {
        let mut sorted: Vec<_> = subs.iter().cloned().collect();
        sorted.sort();
        let label = if use_english { "Categories" } else { "分类" };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if !ranks.is_empty() {
        let mut sorted: Vec<_> = ranks.iter().cloned().collect();
        sorted.sort();
        let label = if use_english { "Ranks" } else { "等级" };
        parts.push(format!("{}: {}", label, sorted.join(", ")));
    }
    if parts.is_empty() {
        if use_english {
            "All conferences (no filters)".to_string()
        } else {
            "所有会议（未筛选）".to_string()
        }
    } else {
        parts.join(" | ")
    }
}

#[component]
pub fn SubscriptionModal(
    show: RwSignal<bool>,
    use_english: RwSignal<bool>,
    check_list: RwSignal<HashSet<String>>,
    rank_list: RwSignal<HashSet<String>>,
) -> impl IntoView {
    let subscriptions = Memo::new(move |_| {
        let lang = if use_english.get() { "en" } else { "zh" };
        let subs = check_list.get();
        let ranks = rank_list.get();
        generate_ics_urls(lang, &subs, &ranks)
    });

    let platform_hint = get_platform_instruction(use_english.get_untracked());

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
                                    "Subscribe based on your current filters:"
                                } else {
                                    "根据当前筛选条件订阅："
                                }
                            }}
                        </div>

                        <div style="margin-bottom: 16px; padding: 12px; background: #f5f7fa; border-radius: 8px; font-size: 13px;">
                            {move || {
                                let subs = check_list.get();
                                let ranks = rank_list.get();
                                let en = use_english.get();
                                render_filter_summary(&subs, &ranks, en)
                            }}
                        </div>

                        <div style="margin-bottom: 16px;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">
                                {move || {
                                    if use_english.get() {
                                        "Subscription Links:"
                                    } else {
                                        "订阅链接："
                                    }
                                }}
                            </div>

                            {move || {
                                let subs = subscriptions.get();
                                if subs.len() > 10 {
                                    let msg = if use_english.get() {
                                        format!(
                                            "Too many filter combinations ({} links). Consider reducing filters or subscribe to all.",
                                            subs.len(),
                                        )
                                    } else {
                                        format!(
                                            "筛选组合过多（{} 个链接）。建议减少筛选条件或订阅全部。",
                                            subs.len(),
                                        )
                                    };
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
                        </div>

                        <div style="padding: 12px; background: #ecf5ff; border-radius: 8px; border-left: 4px solid #409eff;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px; color: #409eff;">
                                {move || {
                                    if use_english.get() {
                                        "How to Subscribe:"
                                    } else {
                                        "如何订阅："
                                    }
                                }}
                            </div>
                            <div style="font-size: 13px; line-height: 1.8; color: #606266;">
                                {move || {
                                    if use_english.get() {
                                        view! {
                                            <div>
                                                <div>"1. Click the Copy button next to the link"</div>
                                                <div>"2. Open your calendar app (Google Calendar, Apple Calendar, Outlook, etc.)"</div>
                                                <div>"3. Find Subscribe to Calendar or Add Calendar by URL"</div>
                                                <div>"4. Paste the copied link and confirm"</div>
                                                <div>"5. The calendar will automatically sync new deadlines"</div>
                                            </div>
                                        }
                                            .into_any()
                                    } else {
                                        view! {
                                            <div>
                                                <div>"1. 点击链接旁的 复制 按钮"</div>
                                                <div>"2. 打开日历应用（Google 日历、Apple 日历、Outlook 等）"</div>
                                                <div>"3. 找到 订阅日历 或 通过 URL 添加日历 选项"</div>
                                                <div>"4. 粘贴复制的链接并确认"</div>
                                                <div>"5. 日历将自动同步最新截止日期"</div>
                                            </div>
                                        }
                                            .into_any()
                                    }
                                }}
                            </div>
                            <div style="margin-top: 8px; font-size: 12px; color: #909399; font-style: italic;">
                                {platform_hint.clone()}
                            </div>
                        </div>

                        <div style="margin-top: 12px; font-size: 12px; color: #909399; text-align: center;">
                            {move || {
                                if use_english.get() {
                                    "Calendars typically update every 12-24 hours"
                                } else {
                                    "日历通常每 12-24 小时更新一次"
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
