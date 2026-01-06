use crate::components::checkbox_button::*;
use crate::components::conf::ConfItem;
use crate::components::conf::*;
use crate::components::countdown::CountDown;
use crate::components::timeline::*;
use crate::components::timezone::*;
use crate::components::calendar_popover::*;
use chrono::{DateTime, FixedOffset, Utc};
use leptos::prelude::*;
use serde_json;
use std::collections::HashMap;
use std::collections::HashSet;
use thaw::*;
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::spawn_local;
use web_sys::{console, js_sys, window};
use urlencoding::encode;

#[component]
pub fn ShowTable() -> impl IntoView {
    // mobile
    let is_mobile = RwSignal::new(false);

    // switch
    let cached_use_english = get_from_local_storage("use_english");
    let use_english = RwSignal::new(cached_use_english
        .as_deref()
        .and_then(|s| s.parse::<bool>().ok())
        .unwrap_or(false));

    // checkbox
    let sub_list = RwSignal::new(get_categories());
    let cached_check_list: HashSet<String> = get_from_local_storage("types")
    .and_then(|data| serde_json::from_str(&data).ok())
    .unwrap_or_else(|| HashSet::new());
    let check_list = RwSignal::new(cached_check_list);
    let is_all_checked_memo = Memo::new(move |_| {
        let total_count = sub_list.get().len();
        let checked_count = check_list.get().len();
        total_count > 0 && checked_count == total_count
    });

    let is_all_checked = RwSignal::new(false);

    Effect::new(move |_| {
        is_all_checked.set(is_all_checked_memo.get());
    });

    let handle_check_all = move |_| {
        if is_all_checked_memo.get_untracked() {
            check_list.set(HashSet::new());
        } else {
            let all_subs: HashSet<String> = sub_list
                .get_untracked()
                .iter()
                .map(|s| s.sub.clone())
                .collect();
            check_list.set(all_subs);
        }
    };

    // input
    let input_value = RwSignal::new(String::new());

    // checkboxbutton
    let cached_rank_list: HashSet<String> = get_from_local_storage("ranks")
    .and_then(|data| serde_json::from_str(&data).ok())
    .unwrap_or_else(|| HashSet::new());
    let rank_list = RwSignal::new(cached_rank_list);

    // liked
    let cached_like_list: HashSet<String> = get_from_local_storage("likes")
    .and_then(|data| serde_json::from_str(&data).ok())
    .unwrap_or_else(|| HashSet::new());
    let like_list = RwSignal::new(cached_like_list);


    // pagination
    let page = RwSignal::new(1);
    let page_size = RwSignal::new(10);
    let page_count = RwSignal::new(1);
    let is_filter_change = RwSignal::new(false);

    // table
    let all_conf_list = RwSignal::new(Vec::<ConfItem>::new());

    // timezone
    let time_zone = RwSignal::new(String::new());

    Effect::new(move |_| {
        let _ = check_list.get();
        let _ = input_value.get();
        let _ = rank_list.get();

        if is_filter_change.get_untracked() {
            page.set(1);
        } else {
            is_filter_change.set(true);
        }
    });

    Effect::new(move |_| {
        set_in_local_storage("use_english", &use_english.get().to_string());
        set_in_local_storage("types", &serde_json::to_string(&check_list.get()).unwrap());
        set_in_local_storage("ranks", &serde_json::to_string(&rank_list.get()).unwrap());
    });

    Effect::new(move |_| {
        set_in_local_storage("likes", &serde_json::to_string(&like_list.get()).unwrap());
    });

    Effect::new(move |_| {
        let _ = check_list.get();
        let _ = input_value.get();
        let _ = rank_list.get();
        let _ = page.get();

        let (current_time, current_timezone) = get_browser_time_and_timezone();
        let utc_map = load_utc_map();

        all_conf_list.update(|conferences| {
            for item in conferences.iter_mut() {
                if item.deadline != "TBD" {
                    let mut tz_str = item.timezone.clone();
                    if tz_str == "AoE" {
                        tz_str = "UTC-12".to_string();
                    } else if tz_str == "UTC" {
                        tz_str = "UTC+0".to_string();
                    }

                    if let Some(tz_offset) = utc_map.get(&tz_str) {
                        let ddl_str = if item.deadline.contains(' ') {
                            format!(
                                "{}T{}{}",
                                item.deadline.split(' ').nth(0).unwrap_or(""),
                                item.deadline.split(' ').nth(1).unwrap_or("00:00:00"),
                                tz_offset
                            )
                        } else {
                            format!("{}T23:59:59{}", item.deadline, tz_offset)
                        };

                        if let Ok(ddl_datetime) = DateTime::parse_from_rfc3339(&ddl_str) {
                            let diff = ddl_datetime.signed_duration_since(current_time);
                            if diff.num_milliseconds() <= 0 {
                                item.remain = 0;
                                item.status = "FIN".to_string();
                            } else {
                                item.remain = diff.num_milliseconds() as u64;
                                item.status = "RUN".to_string();
                            }
                        }
                    }
                }
            }
        });
    });

    Effect::new(move || {
        // mobile check
        is_mobile.set(is_mobile_device());

        // timezone
        time_zone.set(get_timezone_name().unwrap());

        spawn_local(async move {
            let utc_map = load_utc_map();
            let rank_options: HashMap<&str, &str> = [
                ("A", "CCF A"),
                ("B", "CCF B"),
                ("C", "CCF C"),
                ("N", "Non-CCF"),
            ]
            .iter()
            .cloned()
            .collect();

            let (current_time, current_timezone) = get_browser_time_and_timezone();

            // base_url
            let window = web_sys::window().unwrap();
            let location = window.location();
            let base_url = location.origin().unwrap();

            match fetch_all_conf(&base_url).await {
                Ok(conferences) => {
                    let mut conf_vec = Vec::new();

                    for conf in conferences {
                        let conf_items = conf.confs.iter().map(|year_conf| {
                            let mut flag = false;
                            let len = year_conf.timeline.len();
                            let mut cur_deadline = year_conf.timeline[len - 1].deadline.clone();
                            let mut cur_abstract_deadline = year_conf.timeline[len - 1].abstract_deadline.clone();
                            let mut cur_comment = year_conf.timeline[len - 1].comment.clone();
                            let mut ddl_vec = Vec::<TimePoint>::new();

                            for timeline_item in year_conf.timeline.iter() {
                                let tz_offset = utc_map.get(&year_conf.timezone).unwrap();

                                let ddl_str = if timeline_item.deadline.contains(' ') {
                                    format!(
                                        "{}T{}{}",
                                        timeline_item.deadline.split(' ').nth(0).unwrap(),
                                        timeline_item.deadline.split(' ').nth(1).unwrap(),
                                        tz_offset
                                    )
                                } else {
                                    format!("{}T23:59:59{}", timeline_item.deadline, tz_offset)
                                };

                                // abstract type:0 submission type:1
                                if let Some(abs_ddl) = timeline_item.abstract_deadline.clone() {
                                    let abs_ddl_str = if abs_ddl.contains(' ') {
                                        format!(
                                            "{}T{}{}",
                                            abs_ddl.split(' ').nth(0).unwrap(),
                                            abs_ddl.split(' ').nth(1).unwrap(),
                                            tz_offset
                                        )
                                    } else {
                                        format!("{}T23:59:59{}", abs_ddl, tz_offset)
                                    };

                                    if let Ok(abs_ddl_datetime) = DateTime::parse_from_rfc3339(&abs_ddl_str) {
                                        ddl_vec.push(TimePoint { timepoint: abs_ddl_datetime.with_timezone(&current_timezone).clone(), r#type: 0 });
                                    }
                                }

                                if let Ok(ddl_datetime) = DateTime::parse_from_rfc3339(&ddl_str) {
                                    ddl_vec.push(TimePoint { timepoint: ddl_datetime.with_timezone(&current_timezone).clone(), r#type: 1 });

                                    let diff = ddl_datetime.signed_duration_since(current_time);
                                    if !flag && diff.num_milliseconds() > 0 {
                                        cur_deadline = timeline_item.deadline.clone();
                                        cur_abstract_deadline =
                                            timeline_item.abstract_deadline.clone();
                                        cur_comment = timeline_item.comment.clone();
                                        flag = true;
                                    }
                                }
                            }

                            ConfItem {
                                title: conf.title.clone(),
                                description: conf.description.clone(),
                                sub: conf.sub.clone(),
                                rank: conf.rank.ccf.clone(),
                                corerank: conf.rank.core.clone(),
                                thcplrank: conf.rank.thcpl.clone(),
                                displayrank: rank_options
                                    .get(conf.rank.ccf.as_str())
                                    .unwrap()
                                    .to_string(),
                                dblp: conf.dblp.clone(),
                                year: year_conf.year,
                                id: year_conf.id.clone(),
                                link: year_conf.link.clone(),
                                abstract_deadline: cur_abstract_deadline,
                                deadline: cur_deadline,
                                comment: cur_comment,
                                timezone: year_conf.timezone.clone(),
                                date: year_conf.date.clone(),
                                place: year_conf.place.clone(),
                                status: "".to_string(), // Placeholder, should be determined based on current date
                                is_like: like_list.get_untracked().contains(&year_conf.id),
                                remain: 0,
                                local_ddl: None,
                                origin_ddl: None,
                                subname: "".to_string(),
                                subname_en: "".to_string(),
                                google_calendar_url: None,
                                icloud_calendar_url: None,
                                acc_str: None,
                                ddls: ddl_vec
                            }
                        });
                        conf_vec.extend(conf_items);
                    }

                    for item in conf_vec.iter_mut() {
                        // subname
                        if let Some(matched_category) = sub_list
                            .get_untracked()
                            .iter()
                            .find(|sub_item| sub_item.sub == item.sub)
                        {
                            item.subname = matched_category.name.clone();
                            item.subname_en = matched_category.name_en.clone();
                        }

                        if item.deadline == "TBD" {
                            item.remain = 0;
                            item.status = "TBD".to_string();
                            continue;
                        }

                        let mut tz_str = item.timezone.clone();
                        if tz_str == "AoE" {
                            tz_str = "UTC-12".to_string();
                        } else if tz_str == "UTC" {
                            tz_str = "UTC+0".to_string();
                        }

                        // 4. Calculate deadlines and remaining time
                        if let Some(tz_offset) = utc_map.get(&tz_str) {
                            let ddl_str = if item.deadline.contains(' ') {
                                format!(
                                    "{}T{}{}",
                                    item.deadline.split(' ').nth(0).unwrap_or(""),
                                    item.deadline.split(' ').nth(1).unwrap_or("00:00:00"),
                                    tz_offset
                                )
                            } else {
                                format!("{}T23:59:59{}", item.deadline, tz_offset)
                            };

                            if let Ok(ddl_datetime) = DateTime::parse_from_rfc3339(&ddl_str) {
                                // Convert to browser local time and format
                                let local_ddl_datetime =
                                    ddl_datetime.with_timezone(&current_timezone);
                                let formatted_date_time =
                                    local_ddl_datetime.format("%Y-%m-%d %H:%M:%S").to_string();
                                let offset_seconds = local_ddl_datetime.offset().local_minus_utc();
                                let offset_hours = offset_seconds / 3600;
                                let formatted_timezone = format!("UTC{:+}", offset_hours);

                                item.local_ddl =
                                    Some(format!("{} {}", formatted_date_time, formatted_timezone));
                                item.origin_ddl =
                                    Some(format!("{} {}", item.deadline, item.timezone));

                                // Handle abstract deadline
                                if let Some(abs_ddl) = &item.abstract_deadline {
                                    let abs_ddl_str = if abs_ddl.contains(' ') {
                                        format!(
                                            "{}T{}{}",
                                            abs_ddl.split(' ').nth(0).unwrap_or(""),
                                            abs_ddl.split(' ').nth(1).unwrap_or("00:00:00"),
                                            tz_offset
                                        )
                                    } else {
                                        format!("{}T23:59:59{}", abs_ddl, tz_offset)
                                    };
                                    if let Ok(abs_datetime) =
                                        DateTime::parse_from_rfc3339(&abs_ddl_str)
                                    {
                                        let formatted_abs_ddl = abs_datetime
                                            .with_timezone(&current_timezone)
                                            .format("%b %e, %Y")
                                            .to_string();
                                        if item.comment.is_none() {
                                            item.comment = Some(format!(
                                                "abstract deadline on {}.",
                                                formatted_abs_ddl
                                            ));
                                        }
                                    }
                                }

                                let diff = ddl_datetime.signed_duration_since(current_time);
                                if diff.num_milliseconds() <= 0 {
                                    item.remain = 0;
                                    item.status = "FIN".to_string();
                                } else {
                                    item.remain = diff.num_milliseconds() as u64;
                                    item.status = "RUN".to_string();
                                }

                                let iso_string = local_ddl_datetime.format("%Y%m%dT%H%M%S").to_string();

                                item.google_calendar_url = Some(format!(
                                    "https://www.google.com/calendar/render?action=TEMPLATE&text={}&dates={}/{}&details={:?}&location=Online&ctz={}&sf=true&output=xml",
                                    encode(&format!("{} {}", item.title, item.year)),
                                    iso_string,
                                    iso_string,
                                    encode(&format!("{} {}", item.comment.as_ref().map_or("".to_string(), |c| c.clone()), "provided by @ccfddl".to_string())),
                                    time_zone.get_untracked(),
                                ));

                                item.icloud_calendar_url = Some(format!(
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
                                    encode(&format!("{} {} Deadline", item.title, item.year)),
                                    encode(item.comment.as_ref().map_or("", |c| c.as_str())),
                                    encode(""),
                                ));
                            }
                        }
                    }
                    all_conf_list.set(conf_vec);
                }
                Err(e) => {
                    console::error_1(&format!("Error: {:?}", e).into());
                }
            }

            match fetch_all_acc(&base_url).await {
                Ok(all_acc) => {
                    for acc_item in all_acc {
                        for cur_acc in &acc_item.accept_rates {
                            all_conf_list.update(|conferences| {
                                for item in conferences.iter_mut() {
                                    for y in 1..=3 {
                                        if item.title == acc_item.title && item.year == cur_acc.year + y {
                                            item.acc_str = Some(cur_acc.str.clone());
                                        }
                                    }
                                }
                            });
                        }
                    }
                }
                Err(e) => {
                    console::error_1(&format!("Error: {:?}", e).into());
                }
            }
        });


    });

    let paginated_list = Memo::new(move |_| {
        let mut filtered_list = all_conf_list.get();

        // Filtering
        let checkbox_val = check_list.get();
        if !checkbox_val.is_empty() {
            filtered_list.retain(|item| checkbox_val.contains(&item.sub.to_uppercase()));
        }

        let rank_val = rank_list.get();
        if !rank_val.is_empty() {
            filtered_list.retain(|item| rank_val.contains(&item.rank));
        }

        let input_val = input_value.get();
        if !input_val.is_empty() {
            let input_lower = input_val.to_lowercase();
            filtered_list.retain(|item| item.id.to_lowercase().contains(&input_lower) || item.title.to_lowercase().contains(&input_lower));
        }

        // Sorting and Grouping
        let mut run_list: Vec<_> = filtered_list
            .iter()
            .filter(|item| item.status == "RUN".to_string())
            .cloned()
            .collect();
        let mut tbd_list: Vec<_> = filtered_list
            .iter()
            .filter(|item| item.status == "TBD".to_string())
            .cloned()
            .collect();
        let mut fin_list: Vec<_> = filtered_list
            .iter()
            .filter(|item| item.status == "FIN".to_string())
            .cloned()
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
            final_list[start..end].to_vec()
        } else {
            Vec::new()
        };

        paginated_list
    });

    let select_all_name = Memo::new(move |_| {
        if use_english.get() {
            "Select All".to_string()
        } else {
            "全选".to_string()
        }
    });


    view! {
        <section>
            <div class="el-switch">
                <span class=("is_active", move || !use_english.get())>"中文"</span>
                <Switch checked=use_english />
                <span class=("is_active", move || use_english.get())>"English"</span>
            </div>

            <div class="checkbox-item">
                <label>
                    <Checkbox
                        size=CheckboxSize::Large
                        checked=is_all_checked
                        on:change=handle_check_all
                        label=select_all_name
                    />
                </label>
            </div>

            <CheckboxGroup value=check_list>
                <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
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
                                <div class="checkbox-item">
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
                </div>
            </CheckboxGroup>

            <div class="timezone" style="padding-top: 15px; color: #666666; overflow: hidden;">
                <div style="float: left; font-size: 16px">
                    "Deadlines are shown in "{move || time_zone.get()}" time."
                </div>
                <div style="float: left; margin-left: 10px;">
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

                <div style="float: right">
                    <CheckboxButtonGroup rank_list=rank_list />
                </div>
            </div>

            <div class="zonedivider" />
            <div style="width: 100%">
                <Table>
                    <TableBody>
                        {move || {
                            if paginated_list.get().is_empty() {
                                view! {
                                    <TableRow>
                                        <TableCell>
                                            <div style="color: #909399; text-align: center;">
                                                "No data available."
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                }
                                    .into_any()
                            } else {
                                view! {
                                    <For
                                        each=move || paginated_list.get()
                                        key=|conf| {
                                            format!("{}{}", conf.title.clone(), conf.year.clone())
                                        }
                                        children=move |conf| {
                                            let is_finished = conf.status == "FIN";
                                            let is_tbd = conf.status == "TBD";
                                            let show_ddl_str = if is_tbd {
                                                "TBD".to_string()
                                            } else {
                                                format!(
                                                    "{} ({})",
                                                    conf.local_ddl.clone().unwrap(),
                                                    conf.origin_ddl.clone().unwrap(),
                                                )
                                            };
                                            view! {
                                                <TableRow>
                                                    <TableCell>
                                                        <TableCellLayout>
                                                            <div class=("conf-fin", is_finished)>
                                                                <div class="conf-title">
                                                                    <a
                                                                        href=format!(
                                                                            "https://dblp.org/db/conf/{}",
                                                                            conf.dblp,
                                                                        )
                                                                        style="text-decoration: none; border-bottom: 1px solid #ccc; color: inherit;"
                                                                        target="_blank"
                                                                    >
                                                                        {conf.title.clone()}
                                                                    </a>
                                                                    " "
                                                                    {conf.year.clone()}
                                                                    {move || {
                                                                        let conf_title = conf.title.clone();
                                                                        let conf_year = conf.year.clone();
                                                                        let current_like = conf.is_like;
                                                                        if !current_like {
                                                                            view! {
                                                                                <div
                                                                                    style="display: inline;"
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
                                                                                    <Icon icon=icondata::BsStar style="margin-left: 5px;" />
                                                                                </div>
                                                                            }
                                                                                .into_any()
                                                                        } else {
                                                                            view! {
                                                                                <div
                                                                                    style="display: inline;"
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
                                                                                        style="color: rgb(251, 202, 4); margin-left: 5px;"
                                                                                    />
                                                                                </div>
                                                                            }
                                                                                .into_any()
                                                                        }
                                                                    }}
                                                                </div>

                                                                <div style="font-size: 14px; color: #606266; margin-top: 3px;">
                                                                    {conf.date.clone()} " " {conf.place.clone()}
                                                                </div>

                                                                <div style="font-size: 14px; color: #606266; margin-top: 3px;">
                                                                    {conf.description.clone()}
                                                                </div>

                                                                <div class="tag-container">
                                                                    <Tag class="plain-tag">
                                                                        {move || {
                                                                            if conf.displayrank == "N" {
                                                                                "Non-CCF".to_string()
                                                                            } else {
                                                                                conf.displayrank.clone()
                                                                            }
                                                                        }}
                                                                    </Tag>
                                                                    " "
                                                                    {move || {
                                                                        conf.corerank
                                                                            .as_ref()
                                                                            .filter(|corerank| corerank.as_str() != "N")
                                                                            .map(|corerank| {
                                                                                view! {
                                                                                    <Tag class="plain-tag">
                                                                                        {format!("CORE {} ", corerank.clone())}
                                                                                    </Tag>
                                                                                    " "
                                                                                }
                                                                            })
                                                                    }}
                                                                    {move || {
                                                                        conf.thcplrank
                                                                            .as_ref()
                                                                            .filter(|thcplrank| thcplrank.as_str() != "N")
                                                                            .map(|thcplrank| {
                                                                                view! {
                                                                                    <Tag class="plain-tag">
                                                                                        {format!("THCPL {} ", thcplrank.clone())}
                                                                                    </Tag>
                                                                                    " "
                                                                                }
                                                                            })
                                                                    }}
                                                                    {move || {
                                                                        conf.comment
                                                                            .as_ref()
                                                                            .map(|comment| {
                                                                                view! {
                                                                                    <span style="color: #409eff">
                                                                                        <b>"NOTE: "</b>
                                                                                        {comment.clone()}
                                                                                    </span>
                                                                                }
                                                                            })
                                                                    }}
                                                                </div>

                                                                <div style="padding-top: 5px; font-size: 14px; color: #606266;">
                                                                    {move || {
                                                                        if let Some(ref acc) = conf.acc_str {
                                                                            format!("Acc. Rate: {} ", acc)
                                                                        } else {
                                                                            "".to_string()
                                                                        }
                                                                    }}
                                                                    <span style="color: rgb(36, 101, 191); background: rgba(236, 240, 241, 0.7); font-size: 13px; padding: 3px 5px;">
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

                                                                {move || {
                                                                    if is_tbd {
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
                                                                                        <CountDown remain=conf.remain.clone() />
                                                                                        // <Icon icon=icondata::VsCalendar style="margin-left: 5px"/>
                                                                                        <CalendarPopover
                                                                                            google_calendar_url=conf.google_calendar_url.clone()
                                                                                            icloud_calendar_url=conf.icloud_calendar_url.clone()
                                                                                            is_mobile
                                                                                        />
                                                                                    </span>
                                                                                </div>
                                                                            </div>
                                                                        }
                                                                            .into_any()
                                                                    }
                                                                }}
                                                                <div style="font-size: 14px; color: #606266; margin-top: 3px;">
                                                                    {move || {
                                                                        if is_tbd {
                                                                            view! {
                                                                                <span>
                                                                                    "Deadline: "
                                                                                    <a
                                                                                        href="https://github.com/ccfddl/ccf-deadlines/pulls"
                                                                                        style="text-decoration: none; border-bottom: 1px solid #ccc; color: inherit;"
                                                                                        target="_blank"
                                                                                    >
                                                                                        "pull request to update"
                                                                                    </a>
                                                                                </span>
                                                                            }
                                                                                .into_any()
                                                                        } else {
                                                                            view! {
                                                                                <span>{format!("Deadline: {}", show_ddl_str)}</span>
                                                                            }
                                                                                .into_any()
                                                                        }
                                                                    }}
                                                                </div>
                                                                <div style="font-size: 14px; color: #606266; margin-top: 3px;">
                                                                    "website: "
                                                                    <a
                                                                        href=conf.link.clone()
                                                                        style="text-decoration: none; border-bottom: 1px solid #ccc; color: inherit; word-wrap: break-word;"
                                                                        target="_blank"
                                                                    >
                                                                        {conf.link.clone()}
                                                                    </a>
                                                                </div>
                                                                {move || {
                                                                    if is_finished || is_tbd {
                                                                        view! {}.into_any()
                                                                    } else {
                                                                        view! { <TimeLine time_points=conf.ddls.clone() /> }
                                                                            .into_any()
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
        </section>
    }
}

fn load_utc_map() -> HashMap<String, String> {
    let mut utc_map: HashMap<String, String> = HashMap::new();

    for i in -12..=12 {
        if i >= 0 {
            let offset_str = format!("+{:02}:00", i);
            let key = format!("UTC+{}", i);
            utc_map.insert(key, offset_str);
        } else {
            let offset_str = format!("-{:02}:00", -i);
            let key = format!("UTC{}", i);
            utc_map.insert(key, offset_str);
        }
    }
    utc_map.insert("AoE".to_string(), "-12:00".to_string());
    utc_map.insert("UTC".to_string(), "+00:00".to_string());

    utc_map
}

#[cfg(target_arch = "wasm32")]
fn get_browser_time_and_timezone() -> (DateTime<FixedOffset>, FixedOffset) {
    let utc_now = Utc::now();
    let js_date = js_sys::Date::new_0();
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

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = navigator, getter, js_name = userAgent)]
    fn user_agent() -> String;
}

fn is_client_device() -> bool {
    web_sys::window().is_some()
}

fn is_mobile_device() -> bool {
    if !is_client_device() {
        return false;
    }

    let window = web_sys::window().expect("no global window exists");
    let navigator = window.navigator();
    let user_agent = navigator.user_agent().expect("user agent not available").to_lowercase();

    let mobile_keywords = [
        "phone", "pad", "pod", "iphone", "ipod", "ios", "ipad", "android",
        "mobile", "blackberry", "iemobile", "mqqbrowser", "juc", "fennec",
        "wosbrowser", "browserng", "webos", "symbian", "windows phone"
    ];

    mobile_keywords.iter().any(|&keyword| user_agent.contains(keyword))
}

fn get_from_local_storage(key: &str) -> Option<String> {
    let window = window().unwrap();
    let local_storage = window.local_storage().ok().flatten().unwrap();
    local_storage.get_item(key).unwrap()
}

fn set_in_local_storage(key: &str, value: &str) {
    let window = window().unwrap();
    let local_storage = window.local_storage().ok().flatten().unwrap();
    local_storage.set_item(key, value).unwrap();
}
