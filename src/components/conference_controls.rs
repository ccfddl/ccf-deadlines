//! The main site, tabular view and static directory mount these same controls.
use crate::components::checkbox_button::*;
use crate::components::conf::{Category, get_categories};
use crate::components::countdown::use_interval;
use crate::components::showtable::{
    display_timezone_options, format_base_time_display, format_datetime_local,
    is_supported_display_timezone,
};
use crate::components::timezone::get_timezone_name;
use chrono::Utc;
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};
use std::collections::HashSet;
use thaw::*;
use web_sys::{UrlSearchParams, window};

#[slot]
pub struct ToolbarClock {
    children: Children,
}

#[slot]
pub struct ToolbarActions {
    children: Children,
}

#[component]
pub fn ConferenceDivider() -> impl IntoView {
    view! { <hr class="conference-divider" /> }
}

#[component]
pub fn ConferenceControls(
    use_english: RwSignal<bool>,
    categories: RwSignal<Vec<Category>>,
    selected: RwSignal<HashSet<String>>,
    search: RwSignal<String>,
    rank_list: RwSignal<HashSet<String>>,
    core_rank_list: RwSignal<HashSet<String>>,
    thcpl_rank_list: RwSignal<HashSet<String>>,
    selected_timezone: RwSignal<String>,
    browser_timezone: String,
    open_dropdown: RwSignal<Option<String>>,
    toolbar_clock: ToolbarClock,
    #[prop(optional)] toolbar_actions: Option<ToolbarActions>,
    #[prop(optional_no_strip)] show_past: Option<RwSignal<bool>>,
) -> impl IntoView {
    view! {
        <div class="conference-controls">
            <LanguageControls use_english show_past=show_past />
            <CategoryFilters use_english categories selected />
            <div class="timezone toolbar">
                <div class="toolbar-main">
                    <div class="toolbar-clock">{(toolbar_clock.children)()}
                        <TimezonePicker use_english selected_timezone browser_timezone open_dropdown />
                    </div>
                    <ConferenceSearch search />
                </div>
                <div class="toolbar-actions">
                    {toolbar_actions.map(|actions| (actions.children)())}
                    <RankFilters use_english rank_list core_rank_list thcpl_rank_list open_dropdown />
                </div>
            </div>
        </div>
    }
}

#[component]
fn LanguageControls(
    use_english: RwSignal<bool>,
    #[prop(optional_no_strip)] show_past: Option<RwSignal<bool>>,
) -> impl IntoView {
    view! {
        <div class="language-switches">
            <div class="el-switch">
                <span class=("is_active", move || !use_english.get())>"中文"</span>
                <Switch checked=use_english />
                <span class=("is_active", move || use_english.get())>"English"</span>
            </div>
            {show_past.map(|show_past| view! {
                <label class="el-switch past-switch">
                    <Switch checked=show_past />
                    <span class="past-label">{move || if use_english.get() { "Show past conferences" } else { "显示往期会议" }}</span>
                </label>
            })}
        </div>
    }
}

#[component]
fn CategoryFilters(
    use_english: RwSignal<bool>,
    categories: RwSignal<Vec<Category>>,
    selected: RwSignal<HashSet<String>>,
) -> impl IntoView {
    let is_mobile = RwSignal::new(is_narrow_viewport());
    let listener = window_event_listener(ev::resize, move |_| is_mobile.set(is_narrow_viewport()));
    on_cleanup(move || listener.remove());
    view! {
            <CheckboxGroup value=selected>
                <div class="category-filter-grid">
                    <For
                        each=move || {
                            categories
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
                                    if selected.get().contains(&selected_sub) {
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
                        if selected.get().is_empty() {
                            view! {}.into_any()
                        } else {
                            view! {
                                <button
                                    type="button"
                                    class="clear-filter"
                                    on:click=move |_| selected.set(HashSet::new())
                                >
                                    {move || if use_english.get() { "Clear ×" } else { "清除 ×" }}
                                </button>
                            }
                                .into_any()
                        }
                    }}
                </div>
            </CheckboxGroup>


    }
}

fn is_narrow_viewport() -> bool {
    window()
        .and_then(|browser| browser.inner_width().ok())
        .and_then(|width| width.as_f64())
        .is_some_and(|width| width <= 768.0)
}

#[component]
fn TimezonePicker(
    use_english: RwSignal<bool>,
    selected_timezone: RwSignal<String>,
    browser_timezone: String,
    open_dropdown: RwSignal<Option<String>>,
) -> impl IntoView {
    view! {
                    <div class="toolbar-timezone">
                        <span>"("</span>
                        <div class="toolbar-timezone-picker">
                            <button
                                type="button"
                                class="toolbar-timezone-trigger"
                                aria-label=move || if use_english.get() { "Select display timezone" } else { "选择显示时区" }
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
                                <span>{move || selected_timezone.get()}</span>
                                <span class="toolbar-timezone-arrow" aria-hidden="true">"⌄"</span>
                            </button>
                            <Show when=move || open_dropdown.get().as_deref() == Some("timezone")>
                                <div
                                    class="toolbar-timezone-backdrop"
                                    on:click=move |_| open_dropdown.set(None)
                                ></div>
                                <div class="toolbar-timezone-menu" role="listbox">
                                    {display_timezone_options(&browser_timezone)
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
                        <span>" time)"</span>
                    </div>

    }
}

#[component]
fn ConferenceSearch(search: RwSignal<String>) -> impl IntoView {
    view! {
        <div class="toolbar-search">
            <Input value=search placeholder="search conference" size=InputSize::Small>
                <InputPrefix slot><Icon icon=icondata::FiSearch style="color: lightgray;" /></InputPrefix>
            </Input>
        </div>
    }
}

#[component]
fn RankFilters(
    use_english: RwSignal<bool>,
    rank_list: RwSignal<HashSet<String>>,
    core_rank_list: RwSignal<HashSet<String>>,
    thcpl_rank_list: RwSignal<HashSet<String>>,
    open_dropdown: RwSignal<Option<String>>,
) -> impl IntoView {
    let show_filters = RwSignal::new(false);
    view! {
        <div class="toolbar-rank-control">
            <Button class="toolbar-filter-toggle" size=ButtonSize::Small appearance=ButtonAppearance::Subtle
                on_click=move |_| show_filters.update(|value| *value = !*value)
                attr:aria-expanded=move || show_filters.get().to_string()>
                <Icon icon=icondata::FiFilter style="margin-right: 4px;" />
                {move || if use_english.get() { "Filters" } else { "筛选" }}
                <Icon icon=icondata::BsChevronDown style="margin-left: 4px;" />
            </Button>
            <div class="toolbar-rank-filters" class:is-open=move || show_filters.get() role="group" aria-label="Conference rankings">
                <MultiSelectDropdown dropdown_id="ccf".to_string() title="CCF".to_string() options=ccf_filter_options() selected_values=rank_list use_english panel_width="180px".to_string() open_dropdown />
                <MultiSelectDropdown dropdown_id="core".to_string() title="CORE".to_string() options=core_filter_options() selected_values=core_rank_list use_english panel_width="188px".to_string() open_dropdown />
                <MultiSelectDropdown dropdown_id="thcpl".to_string() title="THCPL".to_string() options=thcpl_filter_options() selected_values=thcpl_rank_list use_english panel_width="196px".to_string() open_dropdown />
            </div>
        </div>
    }
}

#[component]
pub fn LiveClock(selected_timezone: RwSignal<String>) -> impl IntoView {
    let clock = RwSignal::new(String::new());
    let tick = move || {
        clock.set(format_base_time_display(&format_datetime_local(
            Utc::now(),
            &selected_timezone.get_untracked(),
        )))
    };
    use_interval(1_000, tick);
    Effect::new(move |_| {
        let _ = selected_timezone.get();
        tick();
    });
    view! { <div class="toolbar-base-time"><strong class="toolbar-base-time-value">{move || clock.get()}</strong></div> }
}

pub(crate) fn parse_filter_values(
    value: Option<String>,
    allowed: &HashSet<String>,
) -> HashSet<String> {
    value
        .unwrap_or_default()
        .split(',')
        .filter(|value| allowed.contains(*value))
        .map(str::to_string)
        .collect()
}

fn stored_filter_values(key: &str) -> HashSet<String> {
    window()
        .and_then(|browser| browser.local_storage().ok().flatten())
        .and_then(|storage| storage.get_item(key).ok().flatten())
        .and_then(|value| serde_json::from_str(&value).ok())
        .unwrap_or_default()
}

fn rank_values(
    options: &[crate::components::checkbox_button::FilterDropdownOption],
) -> HashSet<String> {
    options
        .iter()
        .map(|option| option.value.to_string())
        .collect()
}

/// URL filters take precedence over the preferences shared by all three views.
pub struct ConferenceFilterState {
    pub category_list: RwSignal<Vec<Category>>,
    pub selected: RwSignal<HashSet<String>>,
    pub rank_list: RwSignal<HashSet<String>>,
    pub core_rank_list: RwSignal<HashSet<String>>,
    pub thcpl_rank_list: RwSignal<HashSet<String>>,
    pub search: RwSignal<String>,
    pub browser_timezone: String,
    pub selected_timezone: RwSignal<String>,
}

impl ConferenceFilterState {
    pub fn new() -> Self {
        let query = window()
            .and_then(|browser| browser.location().search().ok())
            .and_then(|search| UrlSearchParams::new_with_str(&search).ok());
        let url_has_filters = query.as_ref().is_some_and(|query| {
            ["categories", "ccf", "core", "thcpl", "filters", "q", "tz"]
                .iter()
                .any(|key| query.has(key))
        });
        let categories = get_categories();
        let all_categories: HashSet<String> =
            categories.iter().map(|item| item.sub.clone()).collect();
        let category_list = RwSignal::new(categories);
        let mut initial_categories = if url_has_filters {
            parse_filter_values(
                query.as_ref().and_then(|query| query.get("categories")),
                &all_categories,
            )
        } else {
            stored_filter_values("types")
        };
        initial_categories.retain(|category| all_categories.contains(category));
        if initial_categories == all_categories {
            initial_categories.clear();
        }
        let selected = RwSignal::new(initial_categories);
        let initial_rank = |url_key: &str, storage_key: &str, allowed: HashSet<String>| {
            if url_has_filters {
                parse_filter_values(
                    query.as_ref().and_then(|query| query.get(url_key)),
                    &allowed,
                )
            } else {
                let mut values = stored_filter_values(storage_key);
                values.retain(|value| allowed.contains(value));
                values
            }
        };
        let mut ccf = initial_rank("ccf", "ranks", rank_values(&ccf_filter_options()));
        let mut core = initial_rank("core", "core_ranks", rank_values(&core_filter_options()));
        let mut thcpl = initial_rank("thcpl", "thcpl_ranks", rank_values(&thcpl_filter_options()));
        normalize_rank_filter_selection(&mut ccf);
        normalize_rank_filter_selection(&mut core);
        normalize_rank_filter_selection(&mut thcpl);
        let rank_list = RwSignal::new(ccf);
        let core_rank_list = RwSignal::new(core);
        let thcpl_rank_list = RwSignal::new(thcpl);
        let search = RwSignal::new(if url_has_filters {
            query
                .as_ref()
                .and_then(|query| query.get("q"))
                .unwrap_or_default()
        } else {
            window()
                .and_then(|browser| browser.local_storage().ok().flatten())
                .and_then(|storage| storage.get_item("conference_search").ok().flatten())
                .unwrap_or_default()
        });
        let browser_timezone = get_timezone_name().unwrap_or_else(|| "UTC".to_string());
        let stored_timezone = window()
            .and_then(|browser| browser.local_storage().ok().flatten())
            .and_then(|storage| storage.get_item("display_timezone").ok().flatten());
        let initial_timezone = if url_has_filters {
            query.as_ref().and_then(|query| query.get("tz"))
        } else {
            stored_timezone
        }
        .filter(|value| is_supported_display_timezone(value, &browser_timezone))
        .unwrap_or_else(|| browser_timezone.clone());
        let selected_timezone = RwSignal::new(initial_timezone);
        Self {
            category_list,
            selected,
            rank_list,
            core_rank_list,
            thcpl_rank_list,
            search,
            browser_timezone,
            selected_timezone,
        }
    }
}

pub fn persist_filters(
    selected: RwSignal<HashSet<String>>,
    rank_list: RwSignal<HashSet<String>>,
    core_rank_list: RwSignal<HashSet<String>>,
    thcpl_rank_list: RwSignal<HashSet<String>>,
    search: RwSignal<String>,
    timezone: RwSignal<String>,
) {
    Effect::new(move |_| {
        if let Some(storage) = window().and_then(|browser| browser.local_storage().ok().flatten()) {
            for (key, value) in [
                ("types", selected.get()),
                ("ranks", rank_list.get()),
                ("core_ranks", core_rank_list.get()),
                ("thcpl_ranks", thcpl_rank_list.get()),
            ] {
                let _ = storage.set_item(key, &serde_json::to_string(&value).unwrap_or_default());
            }
            let _ = storage.set_item("conference_search", &search.get());
            let _ = storage.set_item("display_timezone", &timezone.get());
        }
    });
}

pub fn use_language_preference() -> RwSignal<bool> {
    let storage = web_sys::window().and_then(|window| window.local_storage().ok().flatten());
    let stored_language = storage
        .as_ref()
        .and_then(|storage| storage.get_item("language_preference").ok().flatten())
        .and_then(|value| match value.as_str() {
            "en" => Some(true),
            "zh" => Some(false),
            _ => None,
        })
        .or_else(|| {
            storage
                .as_ref()
                .and_then(|storage| storage.get_item("use_english").ok().flatten())
                .filter(|value| value == "true")
                .map(|_| true)
        });
    let browser_language = web_sys::window()
        .map(|window| window.navigator().language())
        .flatten()
        .unwrap_or_default();
    let use_english = RwSignal::new(
        stored_language.unwrap_or_else(|| !browser_language.to_ascii_lowercase().starts_with("zh")),
    );
    Effect::new(move |_| {
        if let Some(root) = web_sys::window()
            .and_then(|window| window.document())
            .and_then(|document| document.document_element())
        {
            let _ = root.set_attribute("lang", if use_english.get() { "en" } else { "zh-CN" });
        }
    });
    Effect::new(move |previous: Option<bool>| {
        let english = use_english.get();
        if previous.is_some() {
            if let Some(storage) =
                web_sys::window().and_then(|window| window.local_storage().ok().flatten())
            {
                let _ = storage.set_item("language_preference", if english { "en" } else { "zh" });
            }
        }
        english
    });
    use_english
}

pub fn conference_theme() -> RwSignal<Theme> {
    // theme
    let theme = RwSignal::new(Theme::light());
    theme.update(|theme| {
        theme
            .color
            .set_color_compound_brand_background("#409eff".to_string());
        theme
            .color
            .set_color_compound_brand_background_hover("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible("#dcdfe6".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible_pressed("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible_hover("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_2("#ebeef5".to_string());
    });
    theme
}
