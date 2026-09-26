use crate::components::checkbox_button::*;
use crate::components::conf::ConfItem;
use crate::components::conf::*;
use crate::components::countdown::{CountDown, urgency_class_for, use_interval};
use crate::components::subscription_modal::*;
use crate::components::timeline::TimeLine;
use crate::components::timezone::*;
use chrono::{DateTime, Datelike, Duration, FixedOffset, NaiveDate, Utc};
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};
use serde_json;
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;
use thaw::*;
use urlencoding::encode;
use wasm_bindgen::JsCast;
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
    let raw_conferences = RwSignal::new(Vec::<Conference>::new());
    let all_conf_list = RwSignal::new(Vec::<ConfItem>::new());
    let acceptance_rates = RwSignal::new(AcceptanceRateMap::new());
    let base_time = RwSignal::new(None::<DateTime<Utc>>);
    let base_time_input = RwSignal::new(String::new());
    let base_time_editing = RwSignal::new(false);
    let base_time_input_ref = NodeRef::<leptos::html::Input>::new();

    // timezone
    let browser_time_zone = RwSignal::new(get_timezone_name().unwrap_or_else(|| "UTC".to_string()));
    let stored_timezone = get_from_local_storage("display_timezone")
        .filter(|value| is_supported_display_timezone(value, &browser_time_zone.get_untracked()))
        .unwrap_or_else(|| browser_time_zone.get_untracked());
    let selected_timezone = RwSignal::new(stored_timezone.clone());
    let time_zone = RwSignal::new(stored_timezone);

    use_interval(1_000, move || {
        if base_time.get_untracked().is_none() && !base_time_editing.get_untracked() {
            base_time_input.set(format_datetime_local(
                Utc::now(),
                &selected_timezone.get_untracked(),
            ));
        }
    });

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
        let selection = selected_timezone.get();
        set_in_local_storage("display_timezone", &selection);
        time_zone.set(selection.clone());
        base_time_input.set(format_datetime_local(
            base_time.get_untracked().unwrap_or_else(Utc::now),
            &selection,
        ));
    });

    Effect::new(move |_| {
        set_in_local_storage(
            "conference_view",
            if is_list_view.get() { "list" } else { "cards" },
        );
    });

    Effect::new(move || {
        spawn_local(async move {
            let Some(base_url) = browser_origin() else {
                return;
            };
            match fetch_all_conf(&base_url).await {
                Ok(conferences) => {
                    raw_conferences.set(conferences);
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
                    acceptance_rates.set(rates);
                }
                Err(error) => {
                    console::error_1(&format!("Error loading acceptance rates: {error:?}").into());
                }
            }
        });
    });

    Effect::new(move |_| {
        let conferences = raw_conferences.get();
        if conferences.is_empty() {
            return;
        }

        let selected_id = selected_conf
            .get_untracked()
            .as_ref()
            .map(|item| item.id.clone());
        let items = build_conf_items(
            conferences,
            &sub_list.get_untracked(),
            &like_list.get(),
            &acceptance_rates.get(),
            &selected_timezone.get(),
            base_time.get().unwrap_or_else(Utc::now),
        );

        if let Some(selected_id) = selected_id {
            selected_conf.set(items.iter().find(|item| item.id == selected_id).cloned());
        }
        all_conf_list.set(items);
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
                    <div class=move || {
                        if base_time.get().is_some() {
                            "toolbar-base-time is-custom"
                        } else {
                            "toolbar-base-time"
                        }
                    }>
                        <button
                            type="button"
                            class="toolbar-base-time-trigger"
                            aria-label=move || if use_english.get() {
                                "Set countdown base time"
                            } else {
                                "设置倒计时基准时间"
                            }
                            on:click=move |_| {
                                if let Some(input) = base_time_input_ref.get() {
                                    let element: &web_sys::HtmlElement = input.unchecked_ref();
                                    let _ = element.focus();
                                    if input.show_picker().is_err() {
                                        base_time_editing.set(false);
                                    }
                                }
                            }
                        >
                            <strong class="toolbar-base-time-value">
                                {move || format_base_time_display(&base_time_input.get())}
                            </strong>
                        </button>
                        <input
                            node_ref=base_time_input_ref
                            id="base-time-input"
                            type="datetime-local"
                            step="1"
                            tabindex="-1"
                            lang=move || if use_english.get() { "en" } else { "zh-CN" }
                            prop:value=move || base_time_input.get()
                            aria-label=move || if use_english.get() {
                                "Set countdown base time"
                            } else {
                                "设置倒计时基准时间"
                            }
                            on:focus=move |_| base_time_editing.set(true)
                            on:input=move |event| {
                                base_time_input.set(event_target_value(&event));
                            }
                            on:change=move |event| {
                                base_time_editing.set(false);
                                let value = event_target_value(&event);
                                if value.trim().is_empty() {
                                    base_time.set(None);
                                    base_time_input.set(format_datetime_local(
                                        Utc::now(),
                                        &selected_timezone.get_untracked(),
                                    ));
                                    page.set(1);
                                } else if let Some(parsed) = parse_datetime_local(
                                    &value,
                                    &selected_timezone.get_untracked(),
                                ) {
                                    base_time_input.set(value);
                                    base_time.set(Some(parsed));
                                    page.set(1);
                                }
                            }
                            on:blur=move |_| base_time_editing.set(false)
                        />
                    </div>
                    <div class="toolbar-timezone">
                        <span>"Deadlines are shown in"</span>
                        <div class="toolbar-timezone-picker">
                            <button
                                type="button"
                                class="toolbar-timezone-trigger"
                                aria-label="Select display timezone"
                                aria-haspopup="listbox"
                                aria-expanded=move || {
                                    open_dropdown.get().as_deref() == Some("timezone")
                                }
                                on:click=move |_| {
                                    if open_dropdown.get_untracked().as_deref() == Some("timezone") {
                                        open_dropdown.set(None);
                                    } else {
                                        open_dropdown.set(Some("timezone".to_string()));
                                    }
                                }
                            >
                                <span>{move || time_zone.get()}</span>
                                <span class="toolbar-timezone-arrow" aria-hidden="true">"⌄"</span>
                            </button>
                            <Show when=move || open_dropdown.get().as_deref() == Some("timezone")>
                                <div
                                    class="toolbar-timezone-backdrop"
                                    on:click=move |_| open_dropdown.set(None)
                                ></div>
                                <div class="toolbar-timezone-menu" role="listbox">
                                    {display_timezone_options(&browser_time_zone.get_untracked())
                                        .into_iter()
                                        .map(|timezone| {
                                            let value = timezone.clone();
                                            let selected_value = timezone.clone();
                                            view! {
                                                <button
                                                    type="button"
                                                    class="toolbar-timezone-option"
                                                    role="option"
                                                    aria-selected=move || {
                                                        selected_timezone.get() == selected_value
                                                    }
                                                    on:click=move |_| {
                                                        selected_timezone.set(value.clone());
                                                        open_dropdown.set(None);
                                                    }
                                                >
                                                    {timezone}
                                                </button>
                                            }
                                        })
                                        .collect_view()}
                                </div>
                            </Show>
                        </div>
                        <span>"time"</span>
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
                                    let display_timezone = time_zone.get();
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
                                    let custom_base_time = base_time.get();
                                    let countdown_running = custom_base_time.is_none();
                                    let now = custom_base_time.unwrap_or_else(Utc::now);
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
                                        .map(|point| {
                                            if point.timepoint > now {
                                                now.with_timezone(point.timepoint.offset())
                                                    .format("%b %-d, %Y")
                                                    .to_string()
                                            } else {
                                                point.timepoint.format("%b %-d, %Y").to_string()
                                            }
                                        });
                                    let last_timeline_date = deadlines
                                        .last()
                                        .map(|point| {
                                            if point.timepoint < now {
                                                now.with_timezone(point.timepoint.offset())
                                                    .format("%b %-d, %Y")
                                                    .to_string()
                                            } else {
                                                point.timepoint.format("%b %-d, %Y").to_string()
                                            }
                                        });
                                    let ics_filename = format!("{}-{}.ics", conf.title, conf.year);
                                    let (google_calendar_url, icloud_calendar_url) =
                                        build_calendar_urls(
                                            &conf,
                                            &browser_time_zone.get_untracked(),
                                        );
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
                                    let show_round = deadlines
                                        .iter()
                                        .map(|point| point.round)
                                        .max()
                                        .unwrap_or_default()
                                        > 1;
                                    let deadline_cards = deadlines
                                        .iter()
                                        .enumerate()
                                        .map(|(index, point)| {
                                            let label = deadline_detail_label(point.r#type);
                                            let label = if show_round {
                                                format!("Round {} {label}", point.round)
                                            } else {
                                                label.to_string()
                                            };
                                            let is_next = next_index == Some(index);
                                            let is_passed = point.timepoint <= now;
                                            let remaining = point.timepoint.signed_duration_since(now);
                                            let remaining_ms = remaining.num_milliseconds().max(0) as u64;
                                            let days = remaining.num_days();
                                            let status_class = format!(
                                                "conference-detail-deadline-status {}",
                                                urgency_class_for(remaining_ms / 1000),
                                            );
                                            let date = format!(
                                                "{} · {}",
                                                point.timepoint.format("%H:%M, %b %-d, %Y"),
                                                display_timezone,
                                            );
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
                                                            view! { <CountDown remain=remaining_ms running=countdown_running /> }.into_any()
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
                                                        view! { <CountDown remain detailed=true running=countdown_running /> }.into_any()
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
                                                        <TimeLine
                                                            time_points=conf.ddls.clone()
                                                            reference_time=now
                                                            custom_reference=!countdown_running
                                                        />
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
                                        key=move |conf| {
                                            (
                                                conf.id.clone(),
                                                conf.is_like,
                                                selected_timezone.get(),
                                                base_time.get().map(|value| value.timestamp_millis()),
                                            )
                                        }
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
                                            let deadline_kind =
                                                deadline_summary_label(conf.deadline_type);
                                            let list_deadline_kind =
                                                deadline_short_label(conf.deadline_type);
                                            let deadline_date = conf.deadline.clone();
                                            let deadline_timezone = conf.timezone.clone();
                                            let countdown_remain = remaining_until_deadline(
                                                &deadline_date,
                                                &deadline_timezone,
                                                base_time.get_untracked().unwrap_or_else(Utc::now),
                                            )
                                            .unwrap_or(conf.remain);
                                            let countdown_running = base_time.get_untracked().is_none();
                                            let list_deadline = deadline_date.clone();
                                            let list_timezone = deadline_timezone.clone();
                                            let timezone_selection =
                                                selected_timezone.get_untracked();
                                            let display_timezone = time_zone.get_untracked();
                                            let list_deadline_display = format_legacy_deadline_display(
                                                &list_deadline,
                                                &list_timezone,
                                                &timezone_selection,
                                                &display_timezone,
                                            );
                                            let list_website = conf.link.clone();
                                            let list_timeline = conf.ddls.clone();
                                            let timeline_reference = base_time
                                                .get_untracked()
                                                .unwrap_or_else(Utc::now);
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
                                            let estimated_deadline_card =
                                                estimated_deadline_display.clone();
                                            let estimated_deadline_list =
                                                estimated_deadline_display.clone();
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
                                                                                                            <CountDown remain=countdown_remain legacy=true running=countdown_running />
                                                                                                        }
                                                                                                            .into_any()
                                                                                                    } else {
                                                                                                        view! {
                                                                                                            <CountDown remain=countdown_remain running=countdown_running />
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
                                                                                    if estimated_deadline_card.is_empty() {
                                                                                        view! {
                                                                                            <span>
                                                                                                <a
                                                                                                    href="https://github.com/ccfddl/ccf-deadlines/pulls"
                                                                                                    on:click=move |event| event.stop_propagation()
                                                                                                    target="_blank"
                                                                                                >
                                                                                                    "pull request to update"
                                                                                                </a>
                                                                                            </span>
                                                                                        }
                                                                                            .into_any()
                                                                                    } else {
                                                                                        view! {
                                                                                            <span>
                                                                                                {estimated_deadline_card
                                                                                                    .into_iter()
                                                                                                    .map(|(label, title)| view! {
                                                                                                        <span class="conference-card-estimate" title=title>
                                                                                                            {label}
                                                                                                        </span>
                                                                                                    })
                                                                                                    .collect_view()}
                                                                                            </span>
                                                                                        }
                                                                                            .into_any()
                                                                                    }
                                                                                } else {
                                                                                    view! {
                                                                                        <span>
                                                                                            <b>{deadline_kind}</b>
                                                                                            <small>{format_deadline_display(
                                                                                                &deadline_date,
                                                                                                &deadline_timezone,
                                                                                            )}</small>
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
                                                                                <TimeLine
                                                                                    time_points=list_timeline.clone()
                                                                                    reference_time=timeline_reference
                                                                                    custom_reference=!countdown_running
                                                                                />
                                                                            }
                                                                                .into_any()
                                                                        };
                                                                        view! {
                                                                            <div class="conference-list-deadline-meta">
                                                                                {if is_tbd {
                                                                                    if estimated_deadline_list.is_empty() {
                                                                                        view! {
                                                                                            <span>
                                                                                                <a
                                                                                                    href="https://github.com/ccfddl/ccf-deadlines/pulls"
                                                                                                    on:click=move |event| event.stop_propagation()
                                                                                                    target="_blank"
                                                                                                >
                                                                                                    "pull request to update"
                                                                                                </a>
                                                                                            </span>
                                                                                        }
                                                                                            .into_any()
                                                                                    } else {
                                                                                        view! {
                                                                                            <span>
                                                                                                {estimated_deadline_list
                                                                                                    .clone()
                                                                                                    .into_iter()
                                                                                                    .map(|(label, title)| view! {
                                                                                                        <span class="conference-card-estimate" title=title>
                                                                                                            {label}
                                                                                                        </span>
                                                                                                    })
                                                                                                    .collect_view()}
                                                                                            </span>
                                                                                        }
                                                                                            .into_any()
                                                                                    }
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
                    <span class="footer-credit">
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

const DISPLAY_TIMEZONES: &[&str] = &[
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

#[cfg(target_arch = "wasm32")]
fn display_timezone_options(browser_timezone: &str) -> Vec<String> {
    use wasm_bindgen::JsCast;
    use web_sys::js_sys::Array;

    let mut options =
        web_sys::js_sys::eval("Intl.supportedValuesOf ? Intl.supportedValuesOf('timeZone') : []")
            .ok()
            .and_then(|value| value.dyn_into::<Array>().ok())
            .map(|values| {
                values
                    .iter()
                    .filter_map(|value| value.as_string())
                    .collect()
            })
            .unwrap_or_else(|| fallback_display_timezone_options());
    options.retain(|timezone| timezone != browser_timezone);
    options.insert(0, browser_timezone.to_string());
    options
}

#[cfg(not(target_arch = "wasm32"))]
fn display_timezone_options(browser_timezone: &str) -> Vec<String> {
    let mut options = fallback_display_timezone_options();
    options.retain(|timezone| timezone != browser_timezone);
    options.insert(0, browser_timezone.to_string());
    options
}

fn fallback_display_timezone_options() -> Vec<String> {
    DISPLAY_TIMEZONES
        .iter()
        .map(|timezone| (*timezone).to_string())
        .collect()
}

fn is_supported_display_timezone(value: &str, browser_timezone: &str) -> bool {
    display_timezone_options(browser_timezone)
        .iter()
        .any(|timezone| timezone == value)
}

#[cfg(target_arch = "wasm32")]
fn display_timezone_offset_at(timezone: &str, timestamp_millis: i64) -> FixedOffset {
    timezone_offset_from_intl(timezone, timestamp_millis)
        .unwrap_or_else(|| FixedOffset::east_opt(0).expect("UTC offset is valid"))
}

#[cfg(target_arch = "wasm32")]
fn timezone_offset_from_intl(timezone: &str, timestamp_millis: i64) -> Option<FixedOffset> {
    use web_sys::js_sys::{Array, Date, Intl, Object, Reflect};

    let locales = Array::new();
    locales.push(&"en-US".into());
    let options = Object::new();
    for (key, value) in [
        ("timeZone", timezone),
        ("year", "numeric"),
        ("month", "2-digit"),
        ("day", "2-digit"),
        ("hour", "2-digit"),
        ("minute", "2-digit"),
        ("second", "2-digit"),
        ("hourCycle", "h23"),
    ] {
        Reflect::set(&options, &key.into(), &value.into()).ok()?;
    }

    let formatter = Intl::DateTimeFormat::new(&locales, &options);
    let date = Date::new(&wasm_bindgen::JsValue::from_f64(timestamp_millis as f64));
    let parts = formatter.format_to_parts(&date);
    let mut values = HashMap::new();
    for part in parts.iter() {
        let kind = Reflect::get(&part, &"type".into()).ok()?.as_string()?;
        let value = Reflect::get(&part, &"value".into()).ok()?.as_string()?;
        values.insert(kind, value);
    }

    let number = |name: &str| values.get(name)?.parse::<u32>().ok();
    let local_time =
        NaiveDate::from_ymd_opt(number("year")? as i32, number("month")?, number("day")?)?
            .and_hms_opt(number("hour")?, number("minute")?, number("second")?)?;
    let instant_millis = timestamp_millis.div_euclid(1000) * 1000;
    let offset_minutes =
        (local_time.and_utc().timestamp_millis() - instant_millis).div_euclid(60_000);
    FixedOffset::east_opt((offset_minutes * 60) as i32)
}

#[cfg(not(target_arch = "wasm32"))]
fn display_timezone_offset_at(timezone: &str, _timestamp_millis: i64) -> FixedOffset {
    let seconds = match timezone {
        "Pacific/Honolulu" => -10 * 3600,
        "America/Los_Angeles" => -8 * 3600,
        "America/Denver" => -7 * 3600,
        "America/Chicago" => -6 * 3600,
        "America/New_York" => -5 * 3600,
        "America/Sao_Paulo" => -3 * 3600,
        "Europe/Paris" | "Europe/Berlin" | "Africa/Cairo" => 3600,
        "Asia/Dubai" => 4 * 3600,
        "Asia/Kolkata" => 5 * 3600 + 1800,
        "Asia/Bangkok" => 7 * 3600,
        "Asia/Shanghai" => 8 * 3600,
        "Asia/Tokyo" => 9 * 3600,
        "Australia/Sydney" => 10 * 3600,
        "Pacific/Auckland" => 12 * 3600,
        _ => 0,
    };
    FixedOffset::east_opt(seconds).expect("display timezone offset is valid")
}

fn build_conf_items(
    conferences: Vec<Conference>,
    categories: &[Category],
    likes: &HashSet<String>,
    acceptance_rates: &AcceptanceRateMap,
    display_timezone: &str,
    reference_time: DateTime<Utc>,
) -> Vec<ConfItem> {
    let current_time = reference_time.fixed_offset();
    let mut items = Vec::new();

    for conference in conferences {
        for edition in &conference.confs {
            let Some(last_timeline) = edition.timeline.last() else {
                continue;
            };
            let mut deadline = last_timeline.deadline.clone();
            let mut deadline_type = 1;
            let mut abstract_deadline = None;
            let mut comment = last_timeline.comment.clone();
            let mut deadlines = Vec::<TimePoint>::new();
            let mut upcoming_deadlines = Vec::new();
            let mut latest_deadline = None;

            for (round_index, timeline_item) in edition.timeline.iter().enumerate() {
                let timeline_deadlines = [
                    (0, timeline_item.abstract_deadline.as_deref()),
                    (1, Some(timeline_item.deadline.as_str())),
                    (2, timeline_item.rebuttal_deadline.as_deref()),
                    (3, timeline_item.decision_deadline.as_deref()),
                ];

                for (kind, raw_deadline) in timeline_deadlines {
                    let Some(raw_deadline) = raw_deadline else {
                        continue;
                    };
                    let Some(value) = parse_deadline_to_rfc3339(raw_deadline, &edition.timezone)
                        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
                    else {
                        continue;
                    };
                    let display_offset =
                        display_timezone_offset_at(display_timezone, value.timestamp_millis());
                    deadlines.push(TimePoint {
                        timepoint: value.with_timezone(&display_offset),
                        r#type: kind,
                        round: round_index + 1,
                    });

                    let candidate = (
                        value,
                        raw_deadline.to_string(),
                        kind,
                        timeline_item.comment.clone(),
                    );
                    if latest_deadline.as_ref().is_none_or(
                        |latest: &(DateTime<FixedOffset>, String, i32, Option<String>)| {
                            candidate.0 > latest.0
                        },
                    ) {
                        latest_deadline = Some(candidate.clone());
                    }
                    if value > current_time {
                        upcoming_deadlines.push(candidate);
                    }
                }
            }

            deadlines.sort_by_key(|point| point.timepoint);

            let selected_deadline = upcoming_deadlines
                .into_iter()
                .min_by(|left, right| left.0.cmp(&right.0))
                .or(latest_deadline);
            if let Some((_, next_deadline, next_type, next_comment)) = selected_deadline {
                deadline = next_deadline.clone();
                deadline_type = next_type;
                abstract_deadline = (next_type == 0).then_some(next_deadline);
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
                deadline_type,
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

fn format_datetime_local(time: DateTime<Utc>, timezone: &str) -> String {
    let offset = display_timezone_offset_at(timezone, time.timestamp_millis());
    time.with_timezone(&offset)
        .format("%Y-%m-%dT%H:%M:%S")
        .to_string()
}

fn parse_datetime_local(value: &str, timezone: &str) -> Option<DateTime<Utc>> {
    let local_time = chrono::NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%S")
        .or_else(|_| chrono::NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M"))
        .ok()?;
    let tentative_utc = local_time.and_utc();
    let offset = display_timezone_offset_at(timezone, tentative_utc.timestamp_millis());
    Some(tentative_utc - Duration::seconds(offset.local_minus_utc().into()))
}

fn format_base_time_display(value: &str) -> String {
    let mut display = value.replace('-', "/").replace('T', " ");
    if display.matches(':').count() == 1 {
        display.push_str(":00");
    }
    display
}

fn remaining_until_deadline(
    deadline: &str,
    timezone: &str,
    reference_time: DateTime<Utc>,
) -> Option<u64> {
    let deadline_time = parse_deadline_to_rfc3339(deadline, timezone)
        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())?;
    Some(
        deadline_time
            .signed_duration_since(reference_time)
            .num_milliseconds()
            .max(0) as u64,
    )
}

fn deadline_summary_label(deadline_type: i32) -> &'static str {
    match deadline_type {
        0 => "Abstract submission",
        2 => "Rebuttal Submission",
        3 => "Final Decisions",
        _ => "Paper submission",
    }
}

fn deadline_short_label(deadline_type: i32) -> &'static str {
    match deadline_type {
        0 => "Abstract deadline",
        2 => "Rebuttal Submission",
        3 => "Final Decisions",
        _ => "Paper deadline",
    }
}

fn deadline_detail_label(deadline_type: i32) -> &'static str {
    match deadline_type {
        0 => "Abstract submission deadline",
        2 => "Rebuttal Submission",
        3 => "Final Decisions",
        _ => "Paper submission deadline",
    }
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
        .map(|value| format!("{} ({})", value.format("%H:%M, %b %-d, %Y"), timezone))
        .unwrap_or_else(|| format!("{} ({})", deadline, timezone))
}

fn format_legacy_deadline_display(
    deadline: &str,
    timezone: &str,
    display_timezone: &str,
    display_timezone_label: &str,
) -> String {
    let Some(origin_time) = parse_deadline_to_rfc3339(deadline, timezone)
        .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
    else {
        return format!("{} ({})", deadline, normalize_timezone(timezone));
    };

    let selected_offset =
        display_timezone_offset_at(display_timezone, origin_time.timestamp_millis());
    let local_time = origin_time.with_timezone(&selected_offset);
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
    let local_timezone = match display_timezone_label {
        "Asia/Shanghai" | "Asia/Chongqing" => "CST".to_string(),
        "UTC" | "Etc/UTC" | "Etc/GMT" => "UTC".to_string(),
        "" => format_utc_offset(selected_offset.local_minus_utc()),
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
        for i in -12..=14 {
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
