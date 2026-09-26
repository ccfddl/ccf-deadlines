use crate::components::checkbox_button::*;
use crate::components::conf::ConfItem;
use crate::components::conf::*;
use crate::components::countdown::{CountDown, urgency_class_for};
use crate::components::subscription_modal::*;
use crate::components::timeline::TimeLine;
use crate::components::timezone::*;
use chrono::{DateTime, Datelike, Duration, FixedOffset, NaiveDate};
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};
use serde_json;
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;
use thaw::*;
use urlencoding::encode;
use wasm_bindgen_futures::spawn_local;
use web_sys::{console, window};

#[component]
pub fn ShowTable(use_english: RwSignal<bool>) -> impl IntoView {
    // mobile
    let is_mobile = RwSignal::new(is_narrow_viewport());
    let show_filters = RwSignal::new(false);
    let resize_listener = window_event_listener(ev::resize, move |_| {
        is_mobile.set(is_narrow_viewport());
    });
    on_cleanup(move || resize_listener.remove());

    // switch
    let show_past = RwSignal::new(
        get_from_local_storage("show_past")
            .as_deref()
            .and_then(|s| s.parse::<bool>().ok())
            .unwrap_or(false),
    );

    // checkbox
    let sub_list = RwSignal::new(get_categories());
    let stored_check_list: HashSet<String> = get_from_local_storage("types")
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_default();
    let all_categories: HashSet<String> = sub_list
        .get_untracked()
        .iter()
        .map(|item| item.sub.clone())
        .collect();
    let cached_check_list = if stored_check_list == all_categories {
        HashSet::new()
    } else {
        stored_check_list
    };
    let check_list = RwSignal::new(cached_check_list);
    // input
    let input_value = RwSignal::new(String::new());

    // checkboxbutton
    let mut cached_rank_list: HashSet<String> = get_from_local_storage("ranks")
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(|| HashSet::new());
    normalize_rank_filter_selection(&mut cached_rank_list);
    let rank_list = RwSignal::new(cached_rank_list);
    let mut cached_core_rank_list: HashSet<String> = get_from_local_storage("core_ranks")
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(|| HashSet::new());
    normalize_rank_filter_selection(&mut cached_core_rank_list);
    let core_rank_list = RwSignal::new(cached_core_rank_list);
    let mut cached_thcpl_rank_list: HashSet<String> = get_from_local_storage("thcpl_ranks")
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(|| HashSet::new());
    normalize_rank_filter_selection(&mut cached_thcpl_rank_list);
    let thcpl_rank_list = RwSignal::new(cached_thcpl_rank_list);
    let open_dropdown = RwSignal::new(None::<String>);

    // liked
    let cached_like_list: HashSet<String> = get_from_local_storage("likes")
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(|| HashSet::new());
    let like_list = RwSignal::new(cached_like_list);

    let show_subscription_modal = RwSignal::new(false);
    let show_conf_detail = RwSignal::new(false);
    let selected_conf = RwSignal::new(None::<ConfItem>);
    let is_list_view = RwSignal::new(
        get_from_local_storage("conference_view")
            .as_deref()
            .map(|view| view == "list")
            .unwrap_or(false),
    );

    // pagination
    let page = RwSignal::new(1);
    let page_size = RwSignal::new(12);
    let page_count = RwSignal::new(1);
    let is_filter_change = RwSignal::new(false);

    // table
    let all_conf_list = RwSignal::new(Vec::<ConfItem>::new());
    let acceptance_rates = RwSignal::new(AcceptanceRateMap::new());

    // timezone
    let time_zone = RwSignal::new(String::new());

    Effect::new(move |_| {
        let _ = check_list.get();
        let _ = input_value.get();
        let _ = rank_list.get();
        let _ = core_rank_list.get();
        let _ = thcpl_rank_list.get();
        let _ = show_past.get();

        if is_filter_change.get_untracked() {
            page.set(1);
        } else {
            is_filter_change.set(true);
        }
    });

    Effect::new(move |_| {
        set_in_local_storage("show_past", &show_past.get().to_string());
        set_in_local_storage("types", &serde_json::to_string(&check_list.get()).unwrap());
        set_in_local_storage("ranks", &serde_json::to_string(&rank_list.get()).unwrap());
        set_in_local_storage(
            "core_ranks",
            &serde_json::to_string(&core_rank_list.get()).unwrap(),
        );
        set_in_local_storage(
            "thcpl_ranks",
            &serde_json::to_string(&thcpl_rank_list.get()).unwrap(),
        );
    });

    Effect::new(move |previous: Option<bool>| {
        let english = use_english.get();
        if previous.is_some() {
            set_in_local_storage("language_preference", if english { "en" } else { "zh" });
        }
        english
    });

    Effect::new(move |_| {
        set_in_local_storage("likes", &serde_json::to_string(&like_list.get()).unwrap());
    });

    Effect::new(move |_| {
        set_in_local_storage(
            "conference_view",
            if is_list_view.get() { "list" } else { "cards" },
        );
    });

    Effect::new(move || {
        time_zone.set(get_timezone_name().unwrap_or_else(|| "UTC".to_string()));
        let categories = sub_list.get_untracked();
        let likes = like_list.get_untracked();

        spawn_local(async move {
            let Some(base_url) = browser_origin() else {
                return;
            };
            match fetch_all_conf(&base_url).await {
                Ok(conferences) => {
                    let rates = acceptance_rates.get_untracked();
                    all_conf_list.set(build_conf_items(conferences, &categories, &likes, &rates));
                }
                Err(error) => {
                    console::error_1(&format!("Error: {error:?}").into());
                }
            }
        });

        spawn_local(async move {
            let Some(base_url) = browser_origin() else {
                return;
            };
            match fetch_all_acc(&base_url).await {
                Ok(all_acc) => {
                    let rates = build_acceptance_rate_map(all_acc);
                    acceptance_rates.set(rates.clone());
                    all_conf_list.update(|items| apply_acceptance_rates(items, &rates));
                    selected_conf.update(|selected| {
                        if let Some(item) = selected.as_mut() {
                            apply_acceptance_rate(item, &rates);
                        }
                    });
                }
                Err(error) => {
                    console::error_1(&format!("Error loading acceptance rates: {error:?}").into());
                }
            }
        });
    });

    let paginated_list = Memo::new(move |_| {
        all_conf_list.with(|conferences| {
            let mut filtered_list: Vec<&ConfItem> = conferences.iter().collect();

            if !show_past.get() {
                filtered_list.retain(|item| item.status != "FIN");
            }

            // Filtering
            let checkbox_val = check_list.get();
            if !checkbox_val.is_empty() {
                filtered_list.retain(|item| checkbox_val.contains(&item.sub.to_uppercase()));
            }

            let rank_val = rank_list.get();
            if !rank_val.is_empty() {
                filtered_list.retain(|item| rank_val.contains(&item.rank));
            }
            let core_rank_val = core_rank_list.get();
            if !core_rank_val.is_empty() {
                filtered_list.retain(|item| {
                    let core_rank = item.corerank.as_deref().unwrap_or("N");
                    core_rank_val.contains(core_rank)
                });
            }
            let thcpl_rank_val = thcpl_rank_list.get();
            if !thcpl_rank_val.is_empty() {
                filtered_list.retain(|item| {
                    let thcpl_rank = item.thcplrank.as_deref().unwrap_or("N");
                    thcpl_rank_val.contains(thcpl_rank)
                });
            }

            let input_val = input_value.get();
            if !input_val.is_empty() {
                let input_lower = input_val.to_lowercase();
                filtered_list.retain(|item| {
                    item.id.to_lowercase().contains(&input_lower)
                        || item.title.to_lowercase().contains(&input_lower)
                });
            }

            // Sorting and Grouping
            let mut run_list: Vec<_> = filtered_list
                .iter()
                .copied()
                .filter(|item| item.status == "RUN")
                .collect();
            let tbd_list: Vec<_> = filtered_list
                .iter()
                .copied()
                .filter(|item| item.status == "TBD")
                .collect();
            let mut fin_list: Vec<_> = filtered_list
                .iter()
                .copied()
                .filter(|item| item.status == "FIN")
                .collect();

            run_list.sort_by(|a, b| a.remain.cmp(&b.remain));
            fin_list.sort_by(|a, b| b.year.cmp(&a.year));

            let mut all_list = Vec::new();
            all_list.extend(run_list);
            all_list.extend(tbd_list);
            all_list.extend(fin_list);

            let (liked_list, unliked_list): (Vec<_>, Vec<_>) =
                all_list.into_iter().partition(|conf| conf.is_like);

            let mut final_list = liked_list;
            final_list.extend(unliked_list);

            // Pagination
            let total_count = final_list.len();
            let page_val = page.get();
            let page_size_val = page_size.get();
            let start = (page_val - 1) as usize * page_size_val as usize;
            let end = (start + page_size_val as usize).min(total_count);
            page_count.set((total_count + page_size_val - 1) / page_size_val);

            let paginated_list: Vec<ConfItem> = if start < total_count {
                final_list[start..end]
                    .iter()
                    .map(|item| (*item).clone())
                    .collect()
            } else {
                Vec::new()
            };

            paginated_list
        })
    });

    view! {
        <section>
            <div class="language-switches">
                <div class="el-switch">
                    <span class=("is_active", move || !use_english.get())>"中文"</span>
                    <Switch checked=use_english />
                    <span class=("is_active", move || use_english.get())>"English"</span>
                </div>
                <div
                    class="el-switch past-switch"
                    on:click=move |_| show_past.update(|value| *value = !*value)
                >
                    <Switch checked=show_past />
                    <span class="past-label">
                        {move || if use_english.get() {
                            "Show past conferences"
                        } else {
                            "显示往期会议"
                        }}
                    </span>
                </div>
            </div>

            <CheckboxGroup value=check_list>
                <div class="category-filter-grid">
                    <For
                        each=move || {
                            sub_list
                                .get()
                                .into_iter()
                                .enumerate()
                                .collect::<Vec<(usize, Category)>>()
                        }
                        key=|(_, item)| item.sub.clone()
                        children=move |(_, item)| {
                            let sub = item.sub.clone();
                            let selected_sub = sub.clone();
                            let label = Memo::new(move |_| {
                                if is_mobile.get() {
                                    sub.clone()
                                } else if use_english.get() {
                                    item.name_en.clone()
                                } else {
                                    item.name.clone()
                                }
                            });

                            view! {
                                <div class=move || {
                                    if check_list.get().contains(&selected_sub) {
                                        "checkbox-item filter-selected"
                                    } else {
                                        "checkbox-item"
                                    }
                                }>
                                    <label>
                                        <Checkbox
                                            size=CheckboxSize::Large
                                            label=label
                                            value=item.sub.clone()
                                        />
                                    </label>
                                </div>
                            }
                        }
                    />
                    {move || {
                        if check_list.get().is_empty() {
                            view! {}.into_any()
                        } else {
                            view! {
                                <button
                                    type="button"
                                    class="clear-filter"
                                    on:click=move |_| check_list.set(HashSet::new())
                                >
                                    {move || if use_english.get() { "Clear ×" } else { "清除 ×" }}
                                </button>
                            }
                                .into_any()
                        }
                    }}
                </div>
            </CheckboxGroup>

            <div class="timezone toolbar">
                <div class="toolbar-main">
                    <div class="toolbar-timezone">
                        "Countdowns are shown in "{move || time_zone.get()}" time."
                    </div>
                    <div class="toolbar-search">
                        <Input
                            value=input_value
                            placeholder="search conference"
                            size=InputSize::Small
                            class="custom-search-input"
                        >
                            <InputPrefix slot>
                                <Icon icon=icondata::FiSearch style="color: lightgray;" />
                            </InputPrefix>
                        </Input>
                    </div>
                </div>

                <div class="toolbar-actions">
                    <Button
                        class="view-mode-toggle"
                        size=ButtonSize::Small
                        appearance=ButtonAppearance::Subtle
                        on_click=move |_| is_list_view.update(|value| *value = !*value)
                        attr:title=move || {
                            if is_list_view.get() {
                                if use_english.get() {
                                    "switch UI 2.0"
                                } else {
                                    "切换新版UI"
                                }
                            } else if use_english.get() {
                                "switch UI 1.0"
                            } else {
                                "切换旧版UI"
                            }
                        }
                    >
                        {move || {
                            if is_list_view.get() {
                                view! { <Icon icon=icondata::BsGrid style="margin-right: 4px;" /> }
                                    .into_any()
                            } else {
                                view! { <Icon icon=icondata::BsList style="margin-right: 4px;" /> }
                                    .into_any()
                            }
                        }}
                        {move || {
                            if is_list_view.get() {
                                if use_english.get() { "switch UI 2.0" } else { "切换新版UI" }
                            } else if use_english.get() {
                                "switch UI 1.0"
                            } else {
                                "切换旧版UI"
                            }
                        }}
                    </Button>
                    <Button
                        size=ButtonSize::Small
                        appearance=ButtonAppearance::Subtle
                        on_click=move |_| show_subscription_modal.set(true)
                    >
                        <Icon icon=icondata::AiCalendarOutlined style="margin-right: 4px;" />
                        {move || if use_english.get() { "Subscribe" } else { "订阅" }}
                    </Button>
                    {move || {
                        if is_mobile.get() {
                            view! {
                                <Button
                                    size=ButtonSize::Small
                                    appearance=ButtonAppearance::Subtle
                                    on_click=move |_| show_filters.update(|v| *v = !*v)
                                >
                                    <Icon icon=icondata::FiFilter style="margin-right: 4px;" />
                                    {move || if use_english.get() { "Filters" } else { "筛选" }}
                                    {move || if show_filters.get() {
                                        view! { <Icon icon=icondata::BsChevronUp style="margin-left: 4px;" /> }.into_any()
                                    } else {
                                        view! { <Icon icon=icondata::BsChevronDown style="margin-left: 4px;" /> }.into_any()
                                    }}
                                </Button>
                                {move || {
                                    if show_filters.get() {
                                        view! {
                                            <div
                                                style="position: absolute; top: 100%; right: 0; z-index: 100; background: white; border: 1px solid #dcdfe6; border-radius: 4px; padding: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); display: flex; flex-direction: column; gap: 8px; min-width: 200px;"
                                            >
                                                <MultiSelectDropdown
                                                    dropdown_id="ccf".to_string()
                                                    title="CCF".to_string()
                                                    options=ccf_filter_options()
                                                    selected_values=rank_list
                                                    use_english=use_english
                                                    panel_width="180px".to_string()
                                                    open_dropdown=open_dropdown
                                                />
                                                <MultiSelectDropdown
                                                    dropdown_id="core".to_string()
                                                    title="CORE".to_string()
                                                    options=core_filter_options()
                                                    selected_values=core_rank_list
                                                    use_english=use_english
                                                    panel_width="188px".to_string()
                                                    open_dropdown=open_dropdown
                                                />
                                                <MultiSelectDropdown
                                                    dropdown_id="thcpl".to_string()
                                                    title="THCPL".to_string()
                                                    options=thcpl_filter_options()
                                                    selected_values=thcpl_rank_list
                                                    use_english=use_english
                                                    panel_width="196px".to_string()
                                                    open_dropdown=open_dropdown
                                                />
                                            </div>
                                        }
                                            .into_any()
                                    } else {
                                        view! {}.into_any()
                                    }
                                }}
                            }
                                .into_any()
                        } else {
                            view! {
                                <div
                                    style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end;"
                                >
                                    <MultiSelectDropdown
                                        dropdown_id="ccf".to_string()
                                        title="CCF".to_string()
                                        options=ccf_filter_options()
                                        selected_values=rank_list
                                        use_english=use_english
                                        panel_width="180px".to_string()
                                        open_dropdown=open_dropdown
                                    />
                                    <MultiSelectDropdown
                                        dropdown_id="core".to_string()
                                        title="CORE".to_string()
                                        options=core_filter_options()
                                        selected_values=core_rank_list
                                        use_english=use_english
                                        panel_width="188px".to_string()
                                        open_dropdown=open_dropdown
                                    />
                                    <MultiSelectDropdown
                                        dropdown_id="thcpl".to_string()
                                        title="THCPL".to_string()
                                        options=thcpl_filter_options()
                                        selected_values=thcpl_rank_list
                                        use_english=use_english
                                        panel_width="196px".to_string()
                                        open_dropdown=open_dropdown
                                    />
                                </div>
                            }
                                .into_any()
                        }
                    }}
                </div>
            </div>

            <SubscriptionModal
                show=show_subscription_modal
                use_english=use_english
                check_list=check_list
                rank_list=rank_list
                core_rank_list=core_rank_list
                thcpl_rank_list=thcpl_rank_list
            />

            <Dialog open=show_conf_detail>
                <DialogSurface class="conference-detail-dialog">
                    <DialogBody>
                        <Show when=move || selected_conf.get().is_some()>
                            {move || {
                                selected_conf.get().map(|conf| {
                                    let is_tbd = conf.status == "TBD";
                                    let estimated_next_labels = conf
                                        .estimated_deadlines
                                        .iter()
                                        .map(|estimate| {
                                            let kind = if estimate.is_abstract {
                                                "abstract"
                                            } else {
                                                "paper"
                                            };
                                            format!(
                                                "Est. {}: {} · {}",
                                                if kind == "abstract" {
                                                    "Abstract"
                                                } else {
                                                    "Paper"
                                                },
                                                format_estimated_deadline_date(&estimate.deadline),
                                                conf.timezone,
                                            )
                                        })
                                        .collect::<Vec<_>>();
                                    let estimated_details = conf
                                        .estimated_deadlines
                                        .iter()
                                        .map(|estimate| {
                                            let kind = if estimate.is_abstract {
                                                "abstract"
                                            } else {
                                                "paper"
                                            };
                                            (
                                                format!("Estimated {kind} submission deadline"),
                                                format!(
                                                    "{} · {}",
                                                    format_estimated_deadline_date(
                                                        &estimate.deadline,
                                                    ),
                                                    conf.timezone,
                                                ),
                                                format!("based on {}", estimate.source_year),
                                            )
                                        })
                                        .collect::<Vec<_>>();
                                    let mut deadlines = conf.ddls.clone();
                                    deadlines.sort_by_key(|point| point.timepoint);
                                    let now = chrono::Utc::now();
                                    let next_index = deadlines
                                        .iter()
                                        .position(|point| point.timepoint > now);
                                    let next_remain = next_index.map(|index| {
                                        deadlines[index]
                                            .timepoint
                                            .signed_duration_since(now)
                                            .num_milliseconds()
                                            .max(0) as u64
                                    });
                                    let first_timeline_date = deadlines
                                        .first()
                                        .map(|point| point.timepoint.format("%b %-d, %Y").to_string());
                                    let last_timeline_date = deadlines
                                        .last()
                                        .map(|point| point.timepoint.format("%b %-d, %Y").to_string());
                                    let ics_filename = format!("{}-{}.ics", conf.title, conf.year);
                                    let (google_calendar_url, icloud_calendar_url) =
                                        build_calendar_urls(&conf, &time_zone.get_untracked());
                                    let core_rank = conf.corerank.as_deref().unwrap_or("N");
                                    let core_label = if core_rank == "N" {
                                        "Non-CORE".to_string()
                                    } else {
                                        format!("CORE {core_rank}")
                                    };
                                    let thcpl_rank = conf.thcplrank.as_deref().unwrap_or("N");
                                    let thcpl_label = if thcpl_rank == "N" {
                                        "Non-THCPL".to_string()
                                    } else {
                                        format!("THCPL {thcpl_rank}")
                                    };
                                    let show_round = deadlines.iter().filter(|point| point.r#type == 1).count() > 1;
                                    let mut round = 1;
                                    let deadline_cards = deadlines
                                        .iter()
                                        .enumerate()
                                        .map(|(index, point)| {
                                            let label = if point.r#type == 0 {
                                                "Abstract submission deadline"
                                            } else {
                                                "Paper submission deadline"
                                            };
                                            let label = if show_round {
                                                format!("Round {round} {label}")
                                            } else {
                                                label.to_string()
                                            };
                                            if point.r#type == 1 {
                                                round += 1;
                                            }
                                            let is_next = next_index == Some(index);
                                            let is_passed = point.timepoint <= now;
                                            let remaining = point.timepoint.signed_duration_since(now);
                                            let remaining_ms = remaining.num_milliseconds().max(0) as u64;
                                            let days = remaining.num_days();
                                            let status_class = format!(
                                                "conference-detail-deadline-status {}",
                                                urgency_class_for(remaining_ms / 1000),
                                            );
                                            let date = point.timepoint.format("%b %-d, %Y · UTC%:z").to_string();
                                            view! {
                                                <div class=if is_next { "conference-detail-deadline is-next" } else if is_passed { "conference-detail-deadline is-passed" } else { "conference-detail-deadline" }>
                                                    <div class="conference-detail-deadline-main">
                                                        <div class="conference-detail-deadline-name">
                                                            {label}
                                                            {is_next.then(|| view! { <small>"NEXT"</small> })}
                                                        </div>
                                                        <div class="conference-detail-deadline-date">{date}</div>
                                                    </div>
                                                    <span class=status_class>
                                                        {if is_passed {
                                                            view! { "passed" }.into_any()
                                                        } else if days < 1 {
                                                            view! { <CountDown remain=remaining_ms /> }.into_any()
                                                        } else if days == 1 {
                                                            view! { "1 day" }.into_any()
                                                        } else {
                                                            view! { {format!("{days} days")} }.into_any()
                                                        }}
                                                    </span>
                                                </div>
                                            }
                                        })
                                        .collect_view();
                                    view! {
                                        <DialogTitle class="conference-detail-title">
                                            {conf.title.clone()} " " {conf.year}
                                        </DialogTitle>
                                        <button
                                            type="button"
                                            class="conference-detail-close"
                                            aria-label="Close"
                                            on:click=move |_| show_conf_detail.set(false)
                                        >"×"</button>
                                        <DialogContent>
                                            <div class="conference-detail-description">
                                                <span>{conf.description.clone()}</span>
                                                <a
                                                    class="conference-detail-dblp"
                                                    href=format!(
                                                        "https://dblp.org/db/conf/{}",
                                                        conf.dblp,
                                                    )
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    title="View on DBLP"
                                                    aria-label="View conference on DBLP"
                                                >
                                                    <img
                                                        src="https://dblp.org/img/favicon.ico"
                                                        alt=""
                                                        aria-hidden="true"
                                                    />
                                                </a>
                                            </div>
                                            {conf.acc_str.clone().map(|rate| view! {
                                                <div class="conference-detail-acceptance">
                                                    "Acc. Rate: " {rate}
                                                </div>
                                            })}
                                            <div class="conference-detail-section">
                                                <span class="conference-detail-label">"DATES"</span>
                                                <div>{conf.date.clone()}</div>
                                            </div>
                                            <div class="conference-detail-section">
                                                <span class="conference-detail-label">"VENUE"</span>
                                                <div>{conf.place.clone()}</div>
                                            </div>
                                            {conf.comment.clone().map(|comment| view! {
                                                <div class="conference-detail-note">
                                                    "NOTE: " {comment}
                                                </div>
                                            })}
                                            <div class="conference-detail-next">
                                                <span class="conference-detail-label">"NEXT DEADLINE IN"</span>
                                                <strong>
                                                    {if is_tbd {
                                                        view! { "TBD" }.into_any()
                                                    } else if let Some(remain) = next_remain {
                                                        view! { <CountDown remain detailed=true /> }.into_any()
                                                    } else {
                                                        view! { "Passed" }.into_any()
                                                    }}
                                                </strong>
                                                {estimated_next_labels
                                                    .into_iter()
                                                    .map(|label| view! {
                                                        <small class="conference-detail-next-estimate">
                                                            {label}
                                                        </small>
                                                    })
                                                    .collect_view()}
                                            </div>
                                            <div class="conference-detail-section">
                                                <span class="conference-detail-label">"IMPORTANT DEADLINES"</span>
                                                {(!is_tbd && conf.status != "FIN" && !conf.ddls.is_empty()).then(|| view! {
                                                    <div class="conference-detail-timeline">
                                                        <TimeLine time_points=conf.ddls.clone() />
                                                        <div class="conference-detail-timeline-range">
                                                            <span>{first_timeline_date.clone()}</span>
                                                            <span>{last_timeline_date.clone()}</span>
                                                        </div>
                                                    </div>
                                                })}
                                                {deadline_cards}
                                                {is_tbd.then(|| {
                                                    if estimated_details.is_empty() {
                                                        view! {
                                                            <div class="conference-detail-deadline">
                                                                "Dates to be announced"
                                                            </div>
                                                        }
                                                            .into_any()
                                                    } else {
                                                        estimated_details
                                                            .into_iter()
                                                            .map(|(label, date, source)| view! {
                                                                <div class="conference-detail-deadline is-estimated">
                                                                    <div class="conference-detail-deadline-main">
                                                                        <div class="conference-detail-deadline-name">
                                                                            {label}
                                                                            <small>"EST."</small>
                                                                        </div>
                                                                        <div class="conference-detail-deadline-date">{date}</div>
                                                                    </div>
                                                                    <span class="conference-detail-deadline-status conference-detail-estimate-source">
                                                                        {source}
                                                                    </span>
                                                                </div>
                                                            })
                                                            .collect_view()
                                                            .into_any()
                                                    }
                                                })}
                                            </div>
                                            <div class="conference-detail-tags">
                                                <span>{conf.displayrank.clone()}</span>
                                                <span>{core_label}</span>
                                                <span>{thcpl_label}</span>
                                                <span>{conf.subname.clone()}</span>
                                            </div>
                                            <div class="conference-detail-actions">
                                                <a class="conference-detail-website" href=conf.link.clone() target="_blank">"Visit website ↗"</a>
                                                {google_calendar_url.map(|url| view! {
                                                    <a class="conference-detail-calendar-link" href=url target="_blank">
                                                        <img
                                                            src="https://ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_31_2x.png"
                                                            alt=""
                                                            aria-hidden="true"
                                                        />
                                                        <span>"Google Calendar"</span>
                                                    </a>
                                                })}
                                                {icloud_calendar_url.map(|url| view! {
                                                    <a class="conference-detail-calendar-link" href=url download=ics_filename.clone()>
                                                        <img
                                                            src="https://help.apple.com/assets/61526E8E1494760B754BD308/61526E8F1494760B754BD30F/zh_CN/2162f7d3de310d2b3503c0bbebdc3d56.png"
                                                            alt=""
                                                            aria-hidden="true"
                                                        />
                                                        <span>"iCloud Calendar"</span>
                                                    </a>
                                                })}
                                            </div>
                                        </DialogContent>
                                    }
                                })
                            }}
                        </Show>
                    </DialogBody>
                </DialogSurface>
            </Dialog>

            <div class=move || {
                if is_list_view.get() {
                    "conference-list conference-list--rows"
                } else {
                    "conference-list"
                }
            }>
                <div class="conference-list-hint">
                    {move || if use_english.get() {
                        "Click over cells for more information"
                    } else {
                        "点击卡片查看详情"
                    }}
                </div>
                <Table>
                    <TableBody>
                        {move || {
                            if paginated_list.get().is_empty() {
                                view! {
                                    <TableRow class="no-data-row">
                                        <TableCell>
                                            <div class="no-data-message">
                                                {move || {
                                                    if use_english.get() {
                                                        "No data available."
                                                    } else {
                                                        "暂无数据"
                                                    }
                                                }}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                }
                                    .into_any()
                            } else {
                                view! {
                                    <For
                                        each=move || paginated_list.get()
                                        key=|conf| (conf.id.clone(), conf.is_like)
                                        children=move |conf| {
                                            let is_finished = conf.status == "FIN";
                                            let is_tbd = conf.status == "TBD";
                                            let conf_for_detail = conf.clone();
                                            let ccf_rank_value = conf.rank.clone();
                                            let ccf_rank_label = conf.displayrank.clone();
                                            let core_rank_value = conf
                                                .corerank
                                                .clone()
                                                .unwrap_or_else(|| "N".to_string());
                                            let core_tag_label = if core_rank_value == "N" {
                                                "Non-CORE".to_string()
                                            } else {
                                                format!("CORE {}", core_rank_value.clone())
                                            };
                                            let thcpl_rank_value = conf
                                                .thcplrank
                                                .clone()
                                                .unwrap_or_else(|| "N".to_string());
                                            let thcpl_tag_label = if thcpl_rank_value == "N" {
                                                "Non-THCPL".to_string()
                                            } else {
                                                format!("THCPL {}", thcpl_rank_value.clone())
                                            };
                                            let deadline_kind = if conf.abstract_deadline.is_some() {
                                                "Abstract submission"
                                            } else {
                                                "Paper submission"
                                            };
                                            let list_deadline_kind = if conf.abstract_deadline.is_some() {
                                                "Abstract deadline"
                                            } else {
                                                "Paper deadline"
                                            };
                                            let deadline_date = conf.abstract_deadline
                                                .clone()
                                                .unwrap_or_else(|| conf.deadline.clone());
                                            let deadline_timezone = conf.timezone.clone();
                                            let list_deadline = deadline_date.clone();
                                            let list_timezone = deadline_timezone.clone();
                                            let list_deadline_display = format_legacy_deadline_display(
                                                &list_deadline,
                                                &list_timezone,
                                                &time_zone.get_untracked(),
                                            );
                                            let list_website = conf.link.clone();
                                            let list_timeline = conf.ddls.clone();
                                            let estimated_deadline_display = conf
                                                .estimated_deadlines
                                                .iter()
                                                .map(|estimate| {
                                                    let kind = if estimate.is_abstract {
                                                        "abstract"
                                                    } else {
                                                        "paper"
                                                    };
                                                    let date = format_estimated_deadline_date(
                                                        &estimate.deadline,
                                                    );
                                                    (
                                                        format!(
                                                            "Est. {}: {date}",
                                                            if kind == "abstract" {
                                                                "Abstract"
                                                            } else {
                                                                "Paper"
                                                            },
                                                        ),
                                                        format!(
                                                            "Estimated from the {} deadline schedule",
                                                            estimate.source_year,
                                                        ),
                                                    )
                                                })
                                                .collect::<Vec<_>>();
                                            view! {
                                                <TableRow
                                                    on:click=move |_| {
                                                        let mut detail_conf = conf_for_detail.clone();
                                                        let rates = acceptance_rates.get_untracked();
                                                        apply_acceptance_rate(&mut detail_conf, &rates);
                                                        selected_conf.set(Some(detail_conf));
                                                        show_conf_detail.set(true);
                                                    }
                                                >
                                                    <TableCell>
                                                        <TableCellLayout>
                                                            <div class=("conf-fin", is_finished)>
                                                                <div class="conference-card-heading">
                                                                    <div class="conf-title">
                                                                        {conf.title.clone()}
                                                                        " "
                                                                        {conf.year.clone()}
                                                                    </div>
                                                                    <a
                                                                        class="conference-card-website"
                                                                        href=conf.link.clone()
                                                                        on:click=move |event| event.stop_propagation()
                                                                        target="_blank"
                                                                        aria-label="Visit conference website"
                                                                        title="Visit conference website"
                                                                    >
                                                                        <Icon icon=icondata::FiExternalLink />
                                                                    </a>
                                                                    {move || {
                                                                        let conf_title = conf.title.clone();
                                                                        let conf_year = conf.year.clone();
                                                                        let current_like = conf.is_like;
                                                                        if !current_like {
                                                                            view! {
                                                                             <div
                                                                                     class="conference-like-toggle"
                                                                                     style="display: inline; cursor: pointer; transition: transform 0.15s ease;"
                                                                                     on:click=move |_| {
                                                                                         all_conf_list
                                                                                             .update(|conferences| {
                                                                                                 for item in conferences.iter_mut() {
                                                                                                     if item.title == conf_title && item.year == conf_year {
                                                                                                         item.is_like = true;
                                                                                                         like_list
                                                                                                             .update(|mut list| {
                                                                                                                 list.insert(item.id.clone());
                                                                                                             });
                                                                                                         break;
                                                                                                     }
                                                                                                 }
                                                                                             });
                                                                                     }
                                                                                 >
                                                                                     <Icon icon=icondata::BsStar style="font-size: 18px; color: #909399;" />
                                                                                 </div>
                                                                            }
                                                                                .into_any()
                                                                        } else {
                                                                            view! {
                                                                             <div
                                                                                     class="conference-like-toggle is-liked"
                                                                                     style="display: inline; cursor: pointer; transition: transform 0.15s ease;"
                                                                                     on:click=move |_| {
                                                                                         all_conf_list
                                                                                             .update(|conferences| {
                                                                                                 for item in conferences.iter_mut() {
                                                                                                     if item.title == conf_title && item.year == conf_year {
                                                                                                         item.is_like = false;
                                                                                                         like_list
                                                                                                             .update(|mut list| {
                                                                                                                 list.remove(&item.id.clone());
                                                                                                             });
                                                                                                         break;
                                                                                                     }
                                                                                                 }
                                                                                             });
                                                                                     }
                                                                                 >
                                                                                     <Icon
                                                                                         icon=icondata::BsStarFill
                                                                                         style="color: rgb(251, 202, 4); font-size: 18px;"
                                                                                     />
                                                                                 </div>
                                                                            }
                                                                                .into_any()
                                                                        }
                                                                    }}
                                                                </div>

                                                                <div class="conference-card-date" style="font-size: 13px; color: #606266; margin-top: 3px;">
                                                                    <div>{conf.date.clone()}</div>
                                                                    <div class="conference-card-place">{display_place(&conf.place)}</div>
                                                                    <div class="conference-list-place">{conf.place.clone()}</div>
                                                                </div>

                                                                <div class="conference-list-description">
                                                                    {conf.description.clone()}
                                                                </div>

                                                                <div class="tag-container">
                                                                    <span class=move || {
                                                                        if rank_list.get().contains(&ccf_rank_value) {
                                                                            "tag-highlight"
                                                                        } else {
                                                                            ""
                                                                        }
                                                                    }>
                                                                        <Tag class="plain-tag">
                                                                            {ccf_rank_label.clone()}
                                                                        </Tag>
                                                                    </span>
                                                                    " "
                                                                    <span class=move || {
                                                                        if core_rank_list.get().contains(&core_rank_value) {
                                                                            "tag-highlight"
                                                                        } else {
                                                                            ""
                                                                        }
                                                                    }>
                                                                        <Tag class="plain-tag">
                                                                            {core_tag_label.clone()}
                                                                        </Tag>
                                                                    </span>
                                                                    " "
                                                                    <span class=move || {
                                                                        if thcpl_rank_list.get().contains(&thcpl_rank_value) {
                                                                            "tag-highlight"
                                                                        } else {
                                                                            ""
                                                                        }
                                                                    }>
                                                                        <Tag class="plain-tag">
                                                                            {thcpl_tag_label.clone()}
                                                                        </Tag>
                                                                    </span>
                                                                    " "
                                                                    {conf.comment.clone().map(|comment| view! {
                                                                        <span class="conference-list-note">
                                                                            <b>"NOTE: "</b>{comment}
                                                                        </span>
                                                                    })}
                                                                </div>

                                                                <div class="conference-card-acceptance">
                                                                    <span class=move || {
                                                                        if check_list.get().contains(&conf.sub) {
                                                                            "conference-card-category category-highlight"
                                                                        } else {
                                                                            "conference-card-category"
                                                                        }
                                                                    }>
                                                                        {move || {
                                                                            if use_english.get() {
                                                                                conf.subname_en.clone()
                                                                            } else {
                                                                                conf.subname.clone()
                                                                            }
                                                                        }}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </TableCellLayout>
                                                    </TableCell>

                                                    <TableCell>
                                                        <TableCellLayout>

                                                            <div class=(
                                                                "conf-fin",
                                                                is_finished,
                                                            )>
                                                                {if is_finished {
                                                                    view! {
                                                                        <div class="conference-card-passed">
                                                                            "Deadline passed"
                                                                        </div>
                                                                    }
                                                                        .into_any()
                                                                } else {
                                                                    view! {
                                                                        <div class="conference-card-deadline-row">
                                                                            {if is_tbd {
                                                                                view! {
                                                                                    <div class="countdown-container">
                                                                                        <div class="countdown-display">
                                                                                            <span class="countdown-value">"TBD"</span>
                                                                                        </div>
                                                                                        {estimated_deadline_display
                                                                                            .clone()
                                                                                            .into_iter()
                                                                                            .map(|(label, title)| view! {
                                                                                                <div class="conference-card-estimate" title=title>
                                                                                                    {label}
                                                                                                </div>
                                                                                            })
                                                                                            .collect_view()}
                                                                                    </div>
                                                                                }
                                                                                    .into_any()
                                                                            } else {
                                                                                view! {
                                                                                    <div class="countdown-container">
                                                                                        <div class="countdown-display">
                                                                                            <span class="countdown-value">
                                                                                                {move || {
                                                                                                    if is_list_view.get() {
                                                                                                        view! {
                                                                                                            <CountDown remain=conf.remain legacy=true />
                                                                                                        }
                                                                                                            .into_any()
                                                                                                    } else {
                                                                                                        view! {
                                                                                                            <CountDown remain=conf.remain />
                                                                                                        }
                                                                                                            .into_any()
                                                                                                    }
                                                                                                }}
                                                                                                {move || {
                                                                                                    if is_list_view.get() {
                                                                                                        view! {
                                                                                                            <span class="conference-list-calendar" aria-hidden="true">
                                                                                                                <Icon icon=icondata::VsCalendar />
                                                                                                            </span>
                                                                                                        }
                                                                                                            .into_any()
                                                                                                    } else {
                                                                                                        view! {}.into_any()
                                                                                                    }
                                                                                                }}
                                                                                            </span>
                                                                                        </div>
                                                                                    </div>
                                                                                }
                                                                                    .into_any()
                                                                            }}
                                                                            <div class="conference-card-deadline" style="font-size: 11px; color: #606266; margin-top: 3px;">
                                                                                {if is_tbd {
                                                                                    view! {}.into_any()
                                                                                } else {
                                                                                    view! {
                                                                                        <span>
                                                                                            <b>{deadline_kind}</b>
                                                                                            <small>{format_deadline_display(&deadline_date, &deadline_timezone)}</small>
                                                                                        </span>
                                                                                    }
                                                                                        .into_any()
                                                                                }}
                                                                            </div>
                                                                        </div>
                                                                    }
                                                                        .into_any()
                                                                }}
                                                                {move || {
                                                                    if is_list_view.get() {
                                                                        let timeline = if is_finished || is_tbd {
                                                                            view! {}.into_any()
                                                                        } else {
                                                                            view! {
                                                                                <TimeLine time_points=list_timeline.clone() />
                                                                            }
                                                                                .into_any()
                                                                        };
                                                                        view! {
                                                                            <div class="conference-list-deadline-meta">
                                                                                {if is_tbd {
                                                                                    view! {}.into_any()
                                                                                } else {
                                                                                    view! {
                                                                                        <span>
                                                                                            {list_deadline_kind}": "
                                                                                            {list_deadline_display.clone()}
                                                                                        </span>
                                                                                    }
                                                                                        .into_any()
                                                                                }}
                                                                            </div>
                                                                            <div class="conference-list-website">
                                                                                "Website: "
                                                                                <a
                                                                                    href=list_website.clone()
                                                                                    on:click=move |event| event.stop_propagation()
                                                                                    target="_blank"
                                                                                >
                                                                                    {list_website.clone()}
                                                                                </a>
                                                                            </div>
                                                                            {timeline}
                                                                        }
                                                                            .into_any()
                                                                    } else {
                                                                        view! {}.into_any()
                                                                    }
                                                                }}
                                                            </div>
                                                        </TableCellLayout>
                                                    </TableCell>
                                                </TableRow>
                                            }
                                        }
                                    />
                                }
                                    .into_any()
                            }
                        }}
                    </TableBody>
                </Table>
            </div>

            <div class="footer">
                <div class="footer-text">
                    <span>
                        "Maintained by @ccfddl. If you find it useful, star or follow "
                        <a style="color: #666666" href="https://github.com/ccfddl" target="_blank">
                            "@ccfddl"
                        </a> " on Github."
                    </span>
                </div>
                <div class="footer-pagination">
                    <Pagination page page_count />
                </div>
            </div>

            <style>
                {r#"
                .tag-container .tag-highlight .plain-tag {
                                    background: #e9f2fa !important;
                                    color: #356d9e !important;
                                    border: 1px solid #b8d2e8 !important;
                  font-weight: 600;
                }
                "#}
            </style>
        </section>
    }
}

static UTC_MAP: OnceLock<HashMap<String, String>> = OnceLock::new();
type AcceptanceRateMap = HashMap<String, Vec<(i32, String)>>;

fn browser_origin() -> Option<String> {
    window().and_then(|browser| browser.location().origin().ok())
}

fn build_conf_items(
    conferences: Vec<Conference>,
    categories: &[Category],
    likes: &HashSet<String>,
    acceptance_rates: &AcceptanceRateMap,
) -> Vec<ConfItem> {
    let (current_time, current_timezone) = get_browser_time_and_timezone();
    let mut items = Vec::new();

    for conference in conferences {
        for edition in &conference.confs {
            let Some(last_timeline) = edition.timeline.last() else {
                continue;
            };
            let mut deadline = last_timeline.deadline.clone();
            let mut abstract_deadline = None;
            let mut comment = last_timeline.comment.clone();
            let mut deadlines = Vec::<TimePoint>::new();
            let mut upcoming_deadlines = Vec::new();

            for timeline_item in &edition.timeline {
                if let Some(abstract_value) = timeline_item.abstract_deadline.clone() {
                    if let Some(value) =
                        parse_deadline_to_rfc3339(&abstract_value, &edition.timezone)
                            .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
                    {
                        deadlines.push(TimePoint {
                            timepoint: value.with_timezone(&current_timezone),
                            r#type: 0,
                        });
                        if value > current_time {
                            upcoming_deadlines.push((
                                value,
                                abstract_value,
                                true,
                                timeline_item.comment.clone(),
                            ));
                        }
                    }
                }

                if let Some(value) =
                    parse_deadline_to_rfc3339(&timeline_item.deadline, &edition.timezone)
                        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
                {
                    deadlines.push(TimePoint {
                        timepoint: value.with_timezone(&current_timezone),
                        r#type: 1,
                    });
                    if value > current_time {
                        upcoming_deadlines.push((
                            value,
                            timeline_item.deadline.clone(),
                            false,
                            timeline_item.comment.clone(),
                        ));
                    }
                }
            }

            if let Some((_, next_deadline, is_abstract, next_comment)) = upcoming_deadlines
                .into_iter()
                .min_by(|left, right| left.0.cmp(&right.0))
            {
                deadline = next_deadline.clone();
                abstract_deadline = is_abstract.then_some(next_deadline);
                comment = next_comment;
            }

            let category = categories
                .iter()
                .find(|category| category.sub == conference.sub);
            let display_rank = RANK_OPTIONS
                .iter()
                .find(|(rank, _)| *rank == conference.rank.ccf)
                .map(|(_, label)| *label)
                .unwrap_or("Non-CCF")
                .to_string();
            let mut item = ConfItem {
                title: conference.title.clone(),
                description: conference.description.clone(),
                sub: conference.sub.clone(),
                rank: conference.rank.ccf.clone(),
                corerank: conference.rank.core.clone(),
                thcplrank: conference.rank.thcpl.clone(),
                displayrank: display_rank,
                dblp: conference.dblp.clone(),
                year: edition.year,
                id: edition.id.clone(),
                link: edition.link.clone(),
                abstract_deadline,
                deadline,
                comment,
                timezone: edition.timezone.clone(),
                date: edition.date.clone(),
                place: edition.place.clone(),
                status: String::new(),
                is_like: likes.contains(&edition.id),
                remain: 0,
                subname: category.map(|value| value.name.clone()).unwrap_or_default(),
                subname_en: category
                    .map(|value| value.name_en.clone())
                    .unwrap_or_default(),
                acc_str: recent_acceptance_rates(&conference.title, edition.year, acceptance_rates),
                ddls: deadlines,
                estimated_deadlines: Vec::new(),
            };

            if item.deadline == "TBD" {
                item.status = "TBD".to_string();
                item.estimated_deadlines = estimate_deadlines(&conference, edition);
                items.push(item);
                continue;
            }

            if let Some(deadline_time) = parse_deadline_to_rfc3339(&item.deadline, &item.timezone)
                .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
            {
                let remaining = deadline_time.signed_duration_since(current_time);
                if remaining.num_milliseconds() <= 0 {
                    item.status = "FIN".to_string();
                } else {
                    item.remain = remaining.num_milliseconds() as u64;
                    item.status = "RUN".to_string();
                }
            }
            items.push(item);
        }
    }

    items
}

fn estimate_deadlines(conference: &Conference, edition: &ConferenceYear) -> Vec<EstimatedDeadline> {
    let Some(previous) = conference
        .confs
        .iter()
        .find(|candidate| candidate.year == edition.year - 1)
    else {
        return Vec::new();
    };

    let abstract_deadline = previous
        .timeline
        .iter()
        .filter_map(|timeline| timeline.abstract_deadline.as_deref())
        .filter(|deadline| *deadline != "TBD")
        .filter_map(shift_deadline_one_year)
        .min()
        .map(|deadline| EstimatedDeadline {
            deadline,
            is_abstract: true,
            source_year: previous.year,
        });
    let paper_deadline = previous
        .timeline
        .iter()
        .map(|timeline| timeline.deadline.as_str())
        .filter(|deadline| *deadline != "TBD")
        .filter_map(shift_deadline_one_year)
        .min()
        .map(|deadline| EstimatedDeadline {
            deadline,
            is_abstract: false,
            source_year: previous.year,
        });

    [abstract_deadline, paper_deadline]
        .into_iter()
        .flatten()
        .collect()
}

fn shift_deadline_one_year(deadline: &str) -> Option<String> {
    let (date_value, time_value) = deadline
        .split_once(' ')
        .map_or((deadline, None), |(date, time)| (date, Some(time)));
    let date = NaiveDate::parse_from_str(date_value, "%Y-%m-%d").ok()?;
    let next_year = date.year() + 1;
    let shifted = date
        .with_year(next_year)
        .or_else(|| date.with_day(28)?.with_year(next_year))?;

    Some(match time_value {
        Some(time) => format!("{} {time}", shifted.format("%Y-%m-%d")),
        None => shifted.format("%Y-%m-%d").to_string(),
    })
}

fn build_acceptance_rate_map(all_acc: Vec<ConfAccRate>) -> AcceptanceRateMap {
    let mut rates = AcceptanceRateMap::new();
    for conference in all_acc {
        let conference_rates = rates.entry(conference.title).or_default();
        for rate in conference.accept_rates {
            conference_rates.push((rate.year, rate.label));
        }
        conference_rates.sort_by(|left, right| right.0.cmp(&left.0));
        conference_rates.dedup_by(|left, right| left.0 == right.0);
    }
    rates
}

fn apply_acceptance_rates(items: &mut [ConfItem], rates: &AcceptanceRateMap) {
    for item in items {
        apply_acceptance_rate(item, rates);
    }
}

fn apply_acceptance_rate(item: &mut ConfItem, rates: &AcceptanceRateMap) {
    item.acc_str = recent_acceptance_rates(&item.title, item.year, rates);
}

fn recent_acceptance_rates(
    conference_title: &str,
    conference_year: i32,
    rates: &AcceptanceRateMap,
) -> Option<String> {
    let recent_rates = rates
        .get(conference_title)?
        .iter()
        .filter(|(year, _)| *year <= conference_year)
        .take(2)
        .map(|(_, label)| label.as_str())
        .collect::<Vec<_>>();

    (!recent_rates.is_empty()).then(|| recent_rates.join("  ·  "))
}

fn build_calendar_urls(
    conf: &ConfItem,
    browser_timezone: &str,
) -> (Option<String>, Option<String>) {
    let Some(deadline_time) = parse_deadline_to_rfc3339(&conf.deadline, &conf.timezone)
        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
    else {
        return (None, None);
    };
    let (_, current_timezone) = get_browser_time_and_timezone();
    let iso_string = deadline_time
        .with_timezone(&current_timezone)
        .format("%Y%m%dT%H%M%S")
        .to_string();
    let google = format!(
        "https://www.google.com/calendar/render?action=TEMPLATE&text={}&dates={}/{}&details={}&location=Online&ctz={}&sf=true&output=xml",
        encode(&format!("{} {}", conf.title, conf.year)),
        iso_string,
        iso_string,
        encode(&format!(
            "{} provided by @ccfddl",
            conf.comment.as_deref().unwrap_or("")
        )),
        browser_timezone,
    );
    let icloud = format!(
        "data:text/calendar;charset=utf8,BEGIN:VCALENDAR\n\
        VERSION:2.0\n\
        BEGIN:VEVENT\n\
        URL:{}\n\
        DTSTART:{}\n\
        DTEND:{}\n\
        SUMMARY:{}\n\
        DESCRIPTION:{}\n\
        LOCATION:{}\n\
        END:VEVENT\n\
        END:VCALENDAR",
        encode("https://ccfddl.github.io/"),
        iso_string,
        iso_string,
        encode(&format!("{} {} Deadline", conf.title, conf.year)),
        encode(conf.comment.as_deref().unwrap_or("")),
        encode(""),
    );
    (Some(google), Some(icloud))
}

fn normalize_timezone(tz: &str) -> String {
    match tz {
        "AoE" => "UTC-12".to_string(),
        "UTC" => "UTC+0".to_string(),
        _ => tz.to_string(),
    }
}

fn display_place(place: &str) -> String {
    if place.chars().count() <= 28 {
        return place.to_string();
    }

    place
        .split(',')
        .last()
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .unwrap_or(place)
        .to_string()
}

fn format_estimated_deadline_date(deadline: &str) -> String {
    deadline
        .split_whitespace()
        .next()
        .and_then(|date| NaiveDate::parse_from_str(date, "%Y-%m-%d").ok())
        .map(|date| date.format("%b %-d, %Y").to_string())
        .unwrap_or_else(|| deadline.to_string())
}

fn format_deadline_display(deadline: &str, timezone: &str) -> String {
    parse_deadline_to_rfc3339(deadline, timezone)
        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
        .map(|value| format!("{} ({})", value.format("%b %-d, %Y"), timezone))
        .unwrap_or_else(|| format!("{} ({})", deadline, timezone))
}

fn format_legacy_deadline_display(
    deadline: &str,
    timezone: &str,
    browser_timezone: &str,
) -> String {
    let Some(origin_time) = parse_deadline_to_rfc3339(deadline, timezone)
        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
    else {
        return format!("{} ({})", deadline, normalize_timezone(timezone));
    };

    let (_, browser_offset) = get_browser_time_and_timezone();
    let local_time = origin_time.with_timezone(&browser_offset);
    let day = local_time.day();
    let suffix = match day % 100 {
        11..=13 => "th",
        _ => match day % 10 {
            1 => "st",
            2 => "nd",
            3 => "rd",
            _ => "th",
        },
    };
    let local_timezone = match browser_timezone {
        "Asia/Shanghai" | "Asia/Chongqing" => "CST".to_string(),
        "UTC" | "Etc/UTC" | "Etc/GMT" => "UTC".to_string(),
        "" => format_utc_offset(browser_offset.local_minus_utc()),
        value => value.to_string(),
    };

    format!(
        "{} {} {}{} {} {} {} ({} {})",
        local_time.format("%a"),
        local_time.format("%b"),
        day,
        suffix,
        local_time.year(),
        local_time.format("%H:%M:%S"),
        local_timezone,
        origin_time.format("%Y-%m-%d %H:%M:%S"),
        normalize_timezone(timezone),
    )
}

fn format_utc_offset(offset_seconds: i32) -> String {
    let sign = if offset_seconds >= 0 { '+' } else { '-' };
    let total_minutes = offset_seconds.unsigned_abs() / 60;
    let hours = total_minutes / 60;
    let minutes = total_minutes % 60;
    if minutes == 0 {
        format!("UTC{sign}{hours}")
    } else {
        format!("UTC{sign}{hours}:{minutes:02}")
    }
}

/// Nth (1-indexed) Sunday of the given month/year.
fn nth_sunday(year: i32, month: u32, n: u32) -> Option<NaiveDate> {
    let first = NaiveDate::from_ymd_opt(year, month, 1)?;
    let days_to_first_sunday = (7 - first.weekday().num_days_from_sunday()) % 7;
    Some(first + Duration::days(days_to_first_sunday as i64 + 7 * (n as i64 - 1)))
}

/// Whether the given date falls within US daylight saving time, which runs from
/// the second Sunday in March to the first Sunday in November.
fn is_us_dst(date: NaiveDate) -> bool {
    let year = date.year();
    match (nth_sunday(year, 3, 2), nth_sunday(year, 11, 1)) {
        (Some(start), Some(end)) => date >= start && date < end,
        _ => false,
    }
}

/// Resolve a timezone label to a fixed `+HH:MM` / `-HH:MM` offset for a given
/// deadline date. Labels with a constant offset (`UTC-8`, `AoE`, ...) ignore the
/// date; daylight-saving labels such as `PT` (US Pacific Time) pick UTC-7 during
/// DST and UTC-8 otherwise based on the deadline date.
fn resolve_tz_offset(tz: &str, date: &str) -> Option<String> {
    if tz == "PT" {
        let naive = NaiveDate::parse_from_str(date, "%Y-%m-%d").ok()?;
        return Some(if is_us_dst(naive) {
            "-07:00".to_string()
        } else {
            "-08:00".to_string()
        });
    }
    let tz_str = normalize_timezone(tz);
    get_utc_map().get(&tz_str).cloned()
}

fn parse_deadline_to_rfc3339(deadline: &str, tz: &str) -> Option<String> {
    let date_part = deadline.split(' ').nth(0).unwrap_or(deadline);
    let tz_offset = resolve_tz_offset(tz, date_part)?;
    Some(if deadline.contains(' ') {
        format!(
            "{}T{}{}",
            date_part,
            deadline.split(' ').nth(1).unwrap_or("00:00:00"),
            tz_offset
        )
    } else {
        format!("{}T23:59:59{}", deadline, tz_offset)
    })
}

const RANK_OPTIONS: &[(&str, &str)] = &[
    ("A", "CCF A"),
    ("B", "CCF B"),
    ("C", "CCF C"),
    ("N", "Non-CCF"),
];

fn get_utc_map() -> &'static HashMap<String, String> {
    UTC_MAP.get_or_init(|| {
        let mut utc_map = HashMap::new();
        for i in -12..=12 {
            let offset_str = if i >= 0 {
                format!("+{:02}:00", i)
            } else {
                format!("-{:02}:00", -i)
            };
            let key = if i >= 0 {
                format!("UTC+{}", i)
            } else {
                format!("UTC{}", i)
            };
            utc_map.insert(key, offset_str);
        }
        utc_map.insert("AoE".to_string(), "-12:00".to_string());
        utc_map.insert("UTC".to_string(), "+00:00".to_string());
        utc_map
    })
}

#[cfg(target_arch = "wasm32")]
fn get_browser_time_and_timezone() -> (DateTime<FixedOffset>, FixedOffset) {
    let utc_now = chrono::Utc::now();
    let js_date = web_sys::js_sys::Date::new_0();
    let offset_minutes = -(js_date.get_timezone_offset() as i32);

    let timezone = FixedOffset::east_opt(offset_minutes * 60)
        .unwrap_or_else(|| FixedOffset::east_opt(0).unwrap());

    let current_time = utc_now.with_timezone(&timezone);

    (current_time, timezone)
}

#[cfg(not(target_arch = "wasm32"))]
fn get_browser_time_and_timezone() -> (DateTime<FixedOffset>, FixedOffset) {
    use chrono::Local;
    let local_time = Local::now();
    let timezone = *local_time.offset();
    (local_time.with_timezone(&timezone), timezone)
}

fn is_narrow_viewport() -> bool {
    window()
        .and_then(|browser| browser.inner_width().ok())
        .and_then(|width| width.as_f64())
        .is_some_and(|width| width <= 768.0)
}

fn get_from_local_storage(key: &str) -> Option<String> {
    window()
        .and_then(|window| window.local_storage().ok().flatten())
        .and_then(|storage| storage.get_item(key).ok().flatten())
}

fn set_in_local_storage(key: &str, value: &str) {
    if let Some(storage) = window().and_then(|window| window.local_storage().ok().flatten()) {
        let _ = storage.set_item(key, value);
    }
}
