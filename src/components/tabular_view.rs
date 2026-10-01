use crate::components::checkbox_button::{
    MultiSelectDropdown, ccf_filter_options, core_filter_options, normalize_rank_filter_selection,
    thcpl_filter_options,
};
use crate::components::conf::{
    Category, Conference, ConferenceYear, Timeline, fetch_all_conf, get_categories,
};
use chrono::{Datelike, Local, NaiveDate};
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};
use std::collections::HashSet;
use thaw::{Checkbox, CheckboxGroup, CheckboxSize, Switch};
use wasm_bindgen::JsValue;
use wasm_bindgen_futures::spawn_local;
use web_sys::{UrlSearchParams, window};

#[derive(Clone)]
struct DeadlineCell {
    date: String,
    year: i32,
    month: u32,
    place: String,
    link: String,
}

struct TabularRow {
    title: String,
    sort_date: String,
    cells: [Vec<DeadlineCell>; 4],
}

struct MonthGroup {
    month: u32,
    rows: Vec<TabularRow>,
}

#[derive(Default)]
struct RankFilters {
    ccf: HashSet<String>,
    core: HashSet<String>,
    thcpl: HashSet<String>,
}

impl RankFilters {
    fn matches(&self, conference: &Conference) -> bool {
        (self.ccf.is_empty() || self.ccf.contains(&conference.rank.ccf))
            && (self.core.is_empty()
                || self
                    .core
                    .contains(conference.rank.core.as_deref().unwrap_or("N")))
            && (self.thcpl.is_empty()
                || self
                    .thcpl
                    .contains(conference.rank.thcpl.as_deref().unwrap_or("N")))
    }
}

fn parse_filter_values(value: Option<String>, allowed: &HashSet<String>) -> HashSet<String> {
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

fn filter_query(
    categories: &HashSet<String>,
    ccf: &HashSet<String>,
    core: &HashSet<String>,
    thcpl: &HashSet<String>,
) -> String {
    let mut query = "?view=table".to_string();
    for (name, values) in [
        ("categories", categories),
        ("ccf", ccf),
        ("core", core),
        ("thcpl", thcpl),
    ] {
        if !values.is_empty() {
            let mut values: Vec<_> = values.iter().map(String::as_str).collect();
            values.sort_unstable();
            query.push('&');
            query.push_str(name);
            query.push('=');
            query.push_str(&values.join(","));
        }
    }
    if query == "?view=table" {
        query.push_str("&filters=all");
    }
    query
}

#[component]
pub fn TabularView(use_english: RwSignal<bool>) -> impl IntoView {
    let query = window()
        .and_then(|browser| browser.location().search().ok())
        .and_then(|search| UrlSearchParams::new_with_str(&search).ok());
    let url_has_filters = query.as_ref().is_some_and(|query| {
        ["categories", "ccf", "core", "thcpl", "filters"]
            .iter()
            .any(|key| query.has(key))
    });
    let categories = get_categories();
    let all_categories: HashSet<String> = categories.iter().map(|item| item.sub.clone()).collect();
    let category_list = RwSignal::new(categories);
    let is_mobile = RwSignal::new(is_narrow_viewport());
    let resize_listener = window_event_listener(ev::resize, move |_| {
        is_mobile.set(is_narrow_viewport());
    });
    on_cleanup(move || resize_listener.remove());
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
    let open_dropdown = RwSignal::new(None::<String>);
    let conferences = RwSignal::new(None::<Vec<Conference>>);
    let loading = RwSignal::new(true);
    let failed = RwSignal::new(false);
    let reload = RwSignal::new(0u32);

    Effect::new(move |_| {
        let value = serde_json::to_string(&selected.get()).unwrap_or_else(|_| "[]".to_string());
        if let Some(storage) = window().and_then(|browser| browser.local_storage().ok().flatten()) {
            let _ = storage.set_item("types", &value);
        }
    });

    Effect::new(move |_| {
        let ranks = serde_json::to_string(&rank_list.get()).unwrap_or_else(|_| "[]".to_string());
        let core_ranks =
            serde_json::to_string(&core_rank_list.get()).unwrap_or_else(|_| "[]".to_string());
        let thcpl_ranks =
            serde_json::to_string(&thcpl_rank_list.get()).unwrap_or_else(|_| "[]".to_string());
        if let Some(storage) = window().and_then(|browser| browser.local_storage().ok().flatten()) {
            let _ = storage.set_item("ranks", &ranks);
            let _ = storage.set_item("core_ranks", &core_ranks);
            let _ = storage.set_item("thcpl_ranks", &thcpl_ranks);
        }
    });

    Effect::new(move |_| {
        let query = filter_query(
            &selected.get(),
            &rank_list.get(),
            &core_rank_list.get(),
            &thcpl_rank_list.get(),
        );
        if let Some(browser) = window() {
            let location = browser.location();
            if location.search().ok().as_deref() != Some(query.as_str()) {
                let path = location.pathname().unwrap_or_else(|_| "/".to_string());
                let hash = location.hash().unwrap_or_default();
                let url = format!("{path}{query}{hash}");
                if let Ok(history) = browser.history() {
                    let _ = history.replace_state_with_url(&JsValue::NULL, "", Some(&url));
                }
            }
        }
    });

    Effect::new(move |_| {
        let _ = reload.get();
        loading.set(true);
        failed.set(false);
        spawn_local(async move {
            let origin = window().and_then(|browser| browser.location().origin().ok());
            let result = match origin {
                Some(origin) => fetch_all_conf(&origin).await,
                None => Err(std::io::Error::other("browser origin unavailable").into()),
            };
            match result {
                Ok(data) => conferences.set(Some(data)),
                Err(error) => {
                    log::error!("Unable to load tabular conference data: {error}");
                    failed.set(true);
                }
            }
            loading.set(false);
        });
    });

    view! {
        <section class="tabular-view">
            <div class="language-switches">
                <div class="el-switch">
                    <span class=("is_active", move || !use_english.get())>"中文"</span>
                    <Switch checked=use_english />
                    <span class=("is_active", move || use_english.get())>"English"</span>
                </div>
            </div>
            <div class="tabular-filter-row">
                <div class="tabular-category-column">
                    <CheckboxGroup value=selected>
                        <div class="category-filter-grid" role="group" aria-label=move || if use_english.get() { "Conference categories" } else { "选择会议类别" }>
                    <For
                        each=move || {
                            category_list.get().into_iter().enumerate().collect::<Vec<(usize, Category)>>()
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
                                <div class=move || if selected.get().contains(&selected_sub) {
                                    "checkbox-item filter-selected"
                                } else {
                                    "checkbox-item"
                                }>
                                    <label><Checkbox size=CheckboxSize::Large label=label value=item.sub.clone() /></label>
                                </div>
                            }
                        }
                    />
                    <Show when=move || !selected.get().is_empty()>
                        <button type="button" class="clear-filter" on:click=move |_| selected.set(HashSet::new())>
                            {move || if use_english.get() { "Clear ×" } else { "清除 ×" }}
                        </button>
                    </Show>
                        </div>
                    </CheckboxGroup>
                </div>
                <div class="tabular-rank-filters" role="group" aria-label=move || if use_english.get() { "Conference rankings" } else { "会议评级筛选" }>
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
            </div>
            {move || {
                if loading.get() {
                    view! { <p class="tabular-status">{if use_english.get() { "Loading conference table..." } else { "正在加载会议表格…" }}</p> }.into_any()
                } else if failed.get() {
                    view! {
                        <div class="tabular-status" role="alert">
                            <span>{if use_english.get() { "Could not load conference data." } else { "会议数据加载失败。" }}</span>
                            <button type="button" on:click=move |_| reload.update(|value| *value += 1)>
                                {move || if use_english.get() { "Retry" } else { "重试" }}
                            </button>
                        </div>
                    }.into_any()
                } else if let Some(data) = conferences.get() {
                    let selected_categories = selected.get();
                    let ranks = RankFilters {
                        ccf: rank_list.get(),
                        core: core_rank_list.get(),
                        thcpl: thcpl_rank_list.get(),
                    };
                    let year = leading_year(&data, &selected_categories, &ranks, Local::now().year());
                    let groups = build_table(&data, &selected_categories, &ranks, year);
                    render_table(year, groups, use_english.get()).into_any()
                } else {
                    view! { <p class="tabular-status">"—"</p> }.into_any()
                }
            }}
            <div class="footer">
                <div class="footer-text">
                    <span class="footer-credit">
                        "Maintained by @ccfddl. If you find it useful, star or follow "
                        <a style="color: #666666" href="https://github.com/ccfddl" target="_blank" rel="noopener noreferrer">"@ccfddl"</a>
                        " on Github."
                    </span>
                </div>
            </div>
        </section>
    }
}

fn is_narrow_viewport() -> bool {
    window()
        .and_then(|browser| browser.inner_width().ok())
        .and_then(|width| width.as_f64())
        .is_some_and(|width| width <= 768.0)
}

fn leading_year(
    conferences: &[Conference],
    selected: &HashSet<String>,
    ranks: &RankFilters,
    current_year: i32,
) -> i32 {
    conferences
        .iter()
        .filter(|conference| {
            (selected.is_empty() || selected.contains(&conference.sub)) && ranks.matches(conference)
        })
        .flat_map(|conference| &conference.confs)
        .flat_map(|edition| &edition.timeline)
        .filter(|point| is_full_submission_deadline(point))
        .filter_map(|point| {
            NaiveDate::parse_from_str(point.deadline.get(..10)?, "%Y-%m-%d")
                .ok()
                .map(|date| date.year())
        })
        .max()
        .unwrap_or(current_year)
        .max(current_year)
}

fn is_full_submission_deadline(point: &Timeline) -> bool {
    let Some(comment) = point.comment.as_deref() else {
        return true;
    };
    let comment = comment.trim().to_ascii_lowercase();
    !(matches!(
        comment.as_str(),
        "abstract"
            | "abstract deadline"
            | "abstract submission"
            | "abstract submission deadline"
            | "abstract registerations"
            | "abstract registration deadline"
            | "deadline to register abstracts"
            | "paper registration"
            | "paper title and author registration"
            | "research track abstract submission (mandatory)"
            | "regular paper abstract submissions"
            | "title and abstract due (conference track)"
            | "winter cycle title and abstract"
            | "spring cycle title and abstract"
            | "regular papers, arr commitment"
    ) || comment.starts_with("commitment deadline for papers")
        || comment.contains("commitment after arr meta-reviews")
        || comment.starts_with("stage 1: initial 6-page extended abstract submission")
        || comment.starts_with("original abstract registration:"))
}

fn round_deadline(edition: &ConferenceYear, round: usize) -> Option<DeadlineCell> {
    let point = edition.timeline.get(round)?;
    if !is_full_submission_deadline(point) {
        return None;
    }
    let date = NaiveDate::parse_from_str(point.deadline.get(..10)?, "%Y-%m-%d").ok()?;
    Some(DeadlineCell {
        date: date.format("%Y-%m-%d").to_string(),
        year: date.year(),
        month: date.month(),
        place: edition.place.clone(),
        link: edition.link.clone(),
    })
}

fn build_table(
    conferences: &[Conference],
    selected: &HashSet<String>,
    ranks: &RankFilters,
    year: i32,
) -> Vec<MonthGroup> {
    let mut monthly_rows: [Vec<TabularRow>; 12] = std::array::from_fn(|_| Vec::new());
    for conference in conferences {
        if (!selected.is_empty() && !selected.contains(&conference.sub))
            || !ranks.matches(conference)
        {
            continue;
        }
        let Some(latest_edition) = conference
            .confs
            .iter()
            .filter(|edition| {
                (0..edition.timeline.len()).any(|round| round_deadline(edition, round).is_some())
            })
            .max_by_key(|edition| edition.year)
        else {
            continue;
        };
        for round in 0..latest_edition.timeline.len() {
            if round_deadline(latest_edition, round).is_none() {
                continue;
            }
            let deadlines: Vec<_> = conference
                .confs
                .iter()
                .filter_map(|edition| {
                    round_deadline(edition, round).map(|date| (edition.year, date))
                })
                .filter(|(_, date)| (year - 3..=year).contains(&date.year))
                .collect();
            let Some((_, anchor)) = deadlines
                .iter()
                .max_by_key(|(edition_year, _)| edition_year)
            else {
                continue;
            };
            let month = anchor.month as usize;
            let sort_date = anchor.date[5..].to_string();
            let mut cells: [Vec<DeadlineCell>; 4] = std::array::from_fn(|_| Vec::new());
            for (_, deadline) in deadlines {
                cells[(year - deadline.year) as usize].push(deadline);
            }
            for cell in &mut cells {
                cell.sort_by(|a, b| a.date.cmp(&b.date));
            }
            monthly_rows[month - 1].push(TabularRow {
                title: conference.title.clone(),
                sort_date,
                cells,
            });
        }
    }
    monthly_rows
        .into_iter()
        .enumerate()
        .filter_map(|(index, mut rows)| {
            rows.sort_by(|a, b| a.sort_date.cmp(&b.sort_date).then(a.title.cmp(&b.title)));
            (!rows.is_empty()).then_some(MonthGroup {
                month: index as u32 + 1,
                rows,
            })
        })
        .collect()
}

fn render_deadlines(deadlines: Vec<DeadlineCell>, english: bool) -> AnyView {
    if deadlines.is_empty() {
        return view! { <span class="tabular-empty">"—"</span> }.into_any();
    }
    deadlines
        .into_iter()
        .map(|deadline| {
            let place = if deadline.place.trim().is_empty() {
                if english { "Location TBA" } else { "地点待公布" }.to_string()
            } else {
                deadline.place
            };
            if deadline.link.starts_with("https://") || deadline.link.starts_with("http://") {
                let tooltip = place.clone();
                view! {
                    <a class="tabular-date" href=deadline.link target="_blank" rel="noopener noreferrer" title=tooltip>
                        <span>{deadline.date}</span><small>{place}</small>
                    </a>
                }.into_any()
            } else {
                view! { <span class="tabular-date tabular-date-plain"><span>{deadline.date}</span><small>{place}</small></span> }.into_any()
            }
        })
        .collect_view()
        .into_any()
}

fn render_table(year: i32, groups: Vec<MonthGroup>, english: bool) -> AnyView {
    if groups.is_empty() {
        return view! { <p class="tabular-status">{if english { "No known submission deadlines match these categories." } else { "没有符合条件的已知投稿截止日期。" }}</p> }.into_any();
    }
    let months_zh = [
        "一月",
        "二月",
        "三月",
        "四月",
        "五月",
        "六月",
        "七月",
        "八月",
        "九月",
        "十月",
        "十一月",
        "十二月",
    ];
    let months_en = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    let rows = groups
        .into_iter()
        .flat_map(|group| {
            let count = group.rows.len();
            let label = if english { months_en[(group.month - 1) as usize] } else { months_zh[(group.month - 1) as usize] };
            let shade = if group.month % 2 == 0 { "tabular-even" } else { "tabular-odd" };
            group.rows.into_iter().enumerate().map(move |(index, row)| {
                let class = if index == 0 { format!("{shade} tabular-month-start") } else { shade.to_string() };
                view! {
                    <tr class=class>
                        {(index == 0).then(|| view! { <th scope="rowgroup" rowspan=count class="tabular-month">{label}</th> })}
                        <td class="tabular-venue">{row.title}</td>
                        {row.cells.into_iter().map(|deadlines| view! { <td>{render_deadlines(deadlines, english)}</td> }).collect_view()}
                    </tr>
                }
            })
        })
        .collect_view();
    view! {
        <div class="tabular-table-wrap">
            <table class="tabular-table">
                <thead><tr>
                    <th scope="col">{if english { "Month" } else { "月份" }}</th>
                    <th scope="col">{if english { "Venue" } else { "会议" }}</th>
                    <th scope="col">{year}</th>
                    <th scope="col">{year - 1}</th>
                    <th scope="col">{year - 2}</th>
                    <th scope="col">{year - 3}</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    }
    .into_any()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn shareable_filter_query_is_sorted_and_uses_only_allowed_values() {
        let categories = HashSet::from(["AI".to_string(), "DB".to_string()]);
        let ccf = HashSet::from(["B".to_string(), "A".to_string()]);
        let core = HashSet::from(["A*".to_string()]);
        assert_eq!(
            filter_query(&categories, &ccf, &core, &HashSet::new()),
            "?view=table&categories=AI,DB&ccf=A,B&core=A*"
        );
        assert_eq!(
            filter_query(
                &HashSet::new(),
                &HashSet::new(),
                &HashSet::new(),
                &HashSet::new()
            ),
            "?view=table&filters=all"
        );
        assert_eq!(
            parse_filter_values(Some("AI,INVALID,DB".to_string()), &categories),
            categories
        );
    }

    #[test]
    fn table_excludes_abstract_and_commitment_dates_but_keeps_full_paper_dates() {
        let conferences: Vec<Conference> = serde_json::from_value(json!([{
            "title": "Example",
            "description": "Example Conference",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "dblp": "example",
            "confs": [{
                "year": 2027,
                "id": "example27",
                "link": "https://example.com/",
                "timeline": [
                    {"deadline": "2026-10-01 23:59:59", "comment": "Abstract deadline"},
                    {"deadline": "2026-10-08 23:59:59", "abstract_deadline": "2026-10-01 23:59:59", "comment": "Mandatory abstract deadline on October 1."},
                    {"deadline": "2026-11-01 23:59:59", "comment": "Commitment deadline for papers reviewed by ARR"}
                ],
                "timezone": "AoE",
                "date": "June 2027",
                "place": "Paris"
            }]
        }])).unwrap();
        let groups = build_table(&conferences, &HashSet::new(), &RankFilters::default(), 2026);
        let dates: Vec<_> = groups
            .iter()
            .flat_map(|group| &group.rows)
            .flat_map(|row| &row.cells)
            .flat_map(|cell| cell.iter().map(|deadline| deadline.date.as_str()))
            .collect();
        assert_eq!(dates, ["2026-10-08"]);
    }

    #[test]
    fn latest_edition_rounds_align_with_prior_edition_rounds() {
        let conferences: Vec<Conference> = serde_json::from_value(json!([{
            "title": "VLDB",
            "description": "Very Large Data Bases",
            "sub": "DB",
            "rank": {"ccf": "A", "core": "A*", "thcpl": "A"},
            "dblp": "vldb",
            "confs": [
                {"year": 2025, "id": "vldb25", "link": "https://vldb.org/2025/", "timeline": [
                    {"deadline": "2024-04-01 17:00:00"},
                    {"deadline": "2025-01-01 17:00:00"}
                ], "timezone": "PT", "date": "August 2025", "place": "London"},
                {"year": 2026, "id": "vldb26", "link": "https://vldb.org/2026/", "timeline": [
                    {"deadline": "2025-04-01 17:00:00"},
                    {"deadline": "2026-01-01 17:00:00"}
                ], "timezone": "PT", "date": "August 2026", "place": "Boston"},
                {"year": 2027, "id": "vldb27", "link": "https://vldb.org/2027/", "timeline": [
                    {"deadline": "2026-04-01 17:00:00"},
                    {"deadline": "2027-01-01 17:00:00"}
                ], "timezone": "PT", "date": "August 2027", "place": "Athens"}
            ]
        }, {
            "title": "AIConf",
            "description": "AI Conference",
            "sub": "AI",
            "rank": {"ccf": "B"},
            "dblp": "aiconf",
            "confs": [{"year": 2026, "id": "aiconf26", "link": "https://example.com/", "timeline": [
                {"deadline": "2026-02-03 17:00:00"}
            ], "timezone": "PT", "date": "August 2026", "place": "Paris"}]
        }]))
        .unwrap();

        let all_ranks = RankFilters::default();
        assert_eq!(
            leading_year(&conferences, &HashSet::new(), &all_ranks, 2026),
            2027
        );
        let ai_only = HashSet::from(["AI".to_string()]);
        assert_eq!(leading_year(&conferences, &ai_only, &all_ranks, 2026), 2026);
        let ai_february = build_table(&conferences, &ai_only, &all_ranks, 2027)
            .into_iter()
            .find(|group| group.month == 2)
            .unwrap();
        assert!(ai_february.rows[0].cells[0].is_empty());
        assert_eq!(ai_february.rows[0].cells[1][0].date, "2026-02-03");
        let b_only = RankFilters {
            ccf: HashSet::from(["B".to_string()]),
            ..Default::default()
        };
        assert_eq!(
            leading_year(&conferences, &HashSet::new(), &b_only, 2026),
            2026
        );
        assert_eq!(
            build_table(&conferences, &HashSet::new(), &b_only, 2027)
                .iter()
                .map(|group| group.rows.len())
                .sum::<usize>(),
            1
        );
        let matching_ranks = RankFilters {
            ccf: HashSet::from(["A".to_string()]),
            core: HashSet::from(["A*".to_string()]),
            thcpl: HashSet::from(["A".to_string()]),
        };
        assert_eq!(
            leading_year(&conferences, &HashSet::new(), &matching_ranks, 2026),
            2027
        );
        assert_eq!(
            build_table(&conferences, &HashSet::new(), &matching_ranks, 2027)
                .iter()
                .map(|group| group.rows.len())
                .sum::<usize>(),
            2
        );
        let non_core = RankFilters {
            core: HashSet::from(["N".to_string()]),
            ..Default::default()
        };
        assert_eq!(
            leading_year(&conferences, &HashSet::new(), &non_core, 2026),
            2026
        );
        let future_groups = build_table(&conferences, &HashSet::new(), &all_ranks, 2027);
        let future_january = future_groups.iter().find(|group| group.month == 1).unwrap();
        assert_eq!(future_january.rows[0].cells[0][0].date, "2027-01-01");
        assert_eq!(future_january.rows[0].cells[1].len(), 1);
        assert_eq!(future_january.rows[0].cells[1][0].date, "2026-01-01");
        assert_eq!(future_january.rows[0].cells[2][0].date, "2025-01-01");
        let future_april = future_groups.iter().find(|group| group.month == 4).unwrap();
        assert!(future_april.rows[0].cells[0].is_empty());
        assert_eq!(future_april.rows[0].cells[1][0].date, "2026-04-01");
        assert_eq!(future_april.rows[0].cells[2][0].date, "2025-04-01");
        assert_eq!(future_april.rows[0].cells[3][0].date, "2024-04-01");
        assert_eq!(
            future_groups
                .iter()
                .map(|group| group.rows.len())
                .sum::<usize>(),
            3
        );

        let groups = build_table(&conferences, &HashSet::new(), &all_ranks, 2026);
        let january = groups.iter().find(|group| group.month == 1).unwrap();
        assert_eq!(january.rows[0].cells[0].len(), 1);
        assert_eq!(january.rows[0].cells[0][0].date, "2026-01-01");
        assert_eq!(january.rows[0].cells[1].len(), 1);
        assert_eq!(january.rows[0].cells[1][0].date, "2025-01-01");
        let april = groups.iter().find(|group| group.month == 4).unwrap();
        assert_eq!(april.rows[0].cells[0][0].date, "2026-04-01");
        assert_eq!(april.rows[0].cells[0][0].place, "Athens");
        assert_eq!(april.rows[0].cells[1][0].date, "2025-04-01");
        assert_eq!(april.rows[0].cells[1][0].place, "Boston");
    }
}
