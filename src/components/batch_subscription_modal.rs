use crate::components::conf::Conference;
use crate::components::favorites::{FavoritesContext, start_github_login};
use crate::components::subscription_modal::copy_text_to_clipboard;
use leptos::prelude::*;
use std::collections::{HashMap, HashSet};
use thaw::*;

fn subscription_url(selected: &HashSet<String>, english: bool) -> Option<String> {
    if selected.is_empty() || selected.len() > 100 {
        return None;
    }
    let mut ids: Vec<_> = selected.iter().collect();
    ids.sort();
    let mut url = format!(
        "https://ccfddl.com/api/calendar/favorites.ics?lang={}",
        if english { "en" } else { "zh" }
    );
    for id in ids {
        url.push_str("&id=");
        url.push_str(&urlencoding::encode(id));
    }
    Some(url)
}

#[component]
pub fn BatchSubscriptionModal(
    show: RwSignal<bool>,
    use_english: RwSignal<bool>,
    conferences: RwSignal<Vec<Conference>>,
) -> impl IntoView {
    let favorites = expect_context::<FavoritesContext>();
    let selected = RwSignal::new(HashSet::<String>::new());
    let copied = RwSignal::new(false);
    let google_help = RwSignal::new(false);

    Effect::new(move |_| {
        if show.get() {
            selected.set(favorites.starred.get_untracked());
            copied.set(false);
            google_help.set(false);
        }
    });
    Effect::new(move |_| {
        use_english.get();
        copied.set(false);
        google_help.set(false);
    });

    view! {
        <Dialog open=show>
            <DialogSurface class="conference-detail-dialog batch-subscription-dialog">
                <DialogBody>
                    <DialogTitle class="conference-detail-title batch-subscription-title">
                        <Icon icon=icondata::BsCalendarPlus />
                        <span>{move || if use_english.get() { "Batch Subscribe" } else { "批量订阅" }}</span>
                    </DialogTitle>
                    <button
                        type="button"
                        class="conference-detail-close"
                        aria-label=move || if use_english.get() { "Close" } else { "关闭" }
                        on:click=move |_| show.set(false)
                    >"×"</button>
                    <DialogContent>
                        <p class="batch-subscription-intro">
                            {move || if use_english.get() {
                                "Select starred conference editions. Add the link once; your calendar app will refresh their deadlines when the site updates."
                            } else {
                                "选择收藏的会议，只需订阅一次；网站更新截止日期后，日历应用会在刷新订阅时同步。"
                            }}
                        </p>
                        {move || {
                            if favorites.user.get().is_none() {
                                return view! {
                                    <button type="button" class="batch-subscription-login" on:click=move |_| start_github_login()>
                                        {if use_english.get() { "Sign in with GitHub to create a calendar link" } else { "使用 GitHub 登录后生成订阅链接" }}
                                    </button>
                                }.into_any();
                            }
                            let starred = favorites.starred.get();
                            if starred.is_empty() {
                                return view! {
                                    <p class="batch-subscription-empty">
                                        {if use_english.get() { "Star a conference to subscribe to its deadlines." } else { "先收藏会议，再选择要订阅的会议。" }}
                                    </p>
                                }.into_any();
                            }
                            let labels: HashMap<String, String> = conferences.get()
                                .into_iter()
                                .flat_map(|conference| {
                                    conference.confs.into_iter().map(move |edition| {
                                        let label = format!("{} {}", conference.title, edition.year);
                                        (edition.id, label)
                                    })
                                })
                                .collect();
                            let mut entries: Vec<_> = starred.into_iter()
                                .map(|id| (labels.get(&id).cloned().unwrap_or_else(|| id.clone()), id))
                                .collect();
                            entries.sort();
                            view! {
                                <div class="batch-subscription-toolbar">
                                    <div class="batch-subscription-list" role="group" aria-label=move || if use_english.get() { "Select conferences" } else { "选择会议" }>
                                        <button
                                            type="button"
                                            class="favorites-timeline-legend"
                                            class:favorites-timeline-legend--active=move || selected.get() == favorites.starred.get()
                                            aria-pressed=move || selected.get() == favorites.starred.get()
                                            on:click=move |_| {
                                                selected.set(favorites.starred.get_untracked());
                                                copied.set(false);
                                                google_help.set(false);
                                            }
                                        >
                                            {move || if use_english.get() { "All conferences" } else { "全部会议" }}
                                        </button>
                                        {entries.into_iter().map(|(label, id)| {
                                            let checked_id = id.clone();
                                            let pressed_id = id.clone();
                                            let change_id = id.clone();
                                            view! {
                                                <button
                                                    type="button"
                                                    class="favorites-timeline-legend"
                                                    class:favorites-timeline-legend--active=move || selected.with(|ids| ids.contains(&checked_id))
                                                    aria-pressed=move || selected.with(|ids| ids.contains(&pressed_id))
                                                    on:click=move |_| {
                                                        selected.update(|ids| {
                                                            if !ids.insert(change_id.clone()) {
                                                                ids.remove(&change_id);
                                                            }
                                                        });
                                                        copied.set(false);
                                                        google_help.set(false);
                                                    }
                                                >
                                                    {label}
                                                </button>
                                            }
                                        }).collect_view()}
                                    </div>
                                    <span class="batch-subscription-count">{move || format!("{} / {}", selected.get().len(), favorites.starred.get().len())}</span>
                                    <button type="button" class="batch-subscription-clear" on:click=move |_| {
                                        selected.set(HashSet::new());
                                        copied.set(false);
                                        google_help.set(false);
                                    }>
                                        {move || if use_english.get() { "Clear" } else { "清空" }}
                                    </button>
                                </div>
                                {move || {
                                    let count = selected.get().len();
                                    if count > 100 {
                                        Some(view! { <p class="batch-subscription-warning">
                                            {if use_english.get() { "Select at most 100 conferences." } else { "最多选择 100 个会议。" }}
                                        </p> })
                                    } else {
                                        None
                                    }
                                }}
                                <div class="conference-detail-actions batch-subscription-submit">
                                    {move || {
                                        subscription_url(&selected.get(), use_english.get()).map(|url| {
                                            let webcal_url = url.replacen("https://", "webcal://", 1);
                                            let copy_url = url.clone();
                                            let google_url = url.clone();
                                            view! {
                                                <button type="button" class="conference-detail-calendar-link" on:click=move |_| {
                                                    copy_text_to_clipboard(&google_url);
                                                    copied.set(true);
                                                    google_help.set(true);
                                                }>
                                                    <img src="https://ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_31_2x.png" alt="" aria-hidden="true" />
                                                    <span>"Google Calendar"</span>
                                                </button>
                                                <a class="conference-detail-calendar-link" href=webcal_url>
                                                    <img src="https://help.apple.com/assets/61526E8E1494760B754BD308/61526E8F1494760B754BD30F/zh_CN/2162f7d3de310d2b3503c0bbebdc3d56.png" alt="" aria-hidden="true" />
                                                    <span>"iCloud Calendar"</span>
                                                </a>
                                                <button type="button" class="batch-subscription-copy" on:click=move |_| {
                                                    copy_text_to_clipboard(&copy_url);
                                                    copied.set(true);
                                                }>
                                                    {move || if copied.get() {
                                                        if use_english.get() { "Copied" } else { "已复制" }
                                                    } else if use_english.get() { "Copy subscription link" } else { "复制订阅链接" }}
                                                </button>
                                            }
                                        })
                                    }}
                                </div>
                                {move || subscription_url(&selected.get(), use_english.get()).map(|url| view! {
                                    <input
                                        class="batch-subscription-url"
                                        type="text"
                                        readonly
                                        value=url
                                        aria-label=move || if use_english.get() { "Subscription URL" } else { "订阅链接" }
                                    />
                                })}
                                <Show when=move || google_help.get()>
                                    <p class="batch-subscription-help">
                                        {move || if use_english.get() {
                                            "Link copied. In Google Calendar on a computer, choose Other calendars → From URL and paste it."
                                        } else {
                                            "链接已复制。请在电脑上的 Google 日历中选择“其他日历 → 通过网址添加”，然后粘贴链接。"
                                        }}
                                    </p>
                                </Show>
                            }.into_any()
                        }}
                    </DialogContent>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selected_editions_share_one_stable_calendar_url() {
        let selected = HashSet::from(["iclr27".to_string(), "cvpr27".to_string()]);
        assert_eq!(
            subscription_url(&selected, false),
            Some(
                "https://ccfddl.com/api/calendar/favorites.ics?lang=zh&id=cvpr27&id=iclr27"
                    .to_string()
            )
        );
    }
}
