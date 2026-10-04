use crate::components::conf::TimePoint;
use chrono::{Duration, prelude::*};
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};

#[component]
pub fn TimeLine(
    time_points: Vec<TimePoint>,
    reference_time: DateTime<Utc>,
    #[prop(default = false)] custom_reference: bool,
) -> impl IntoView {
    let has_custom_reference = custom_reference;
    let hovered = RwSignal::new(None::<usize>);
    let focused = RwSignal::new(None::<usize>);
    let selected = RwSignal::new(None::<usize>);
    let active = Memo::new(move |_| hovered.get().or(focused.get()).or(selected.get()));
    let dismiss = move || {
        hovered.set(None);
        focused.set(None);
        selected.set(None);
    };
    let outside_listener = window_event_listener(ev::click, move |_| dismiss());
    on_cleanup(move || outside_listener.remove());
    let (sel_time, set_sel_time) = signal(String::new());
    let (start_date, set_start_date) = signal(0.0);
    let (end_date, set_end_date) = signal(0.0);
    let (incre_dates, set_incre_dates) = signal(Vec::<TimePoint>::new());
    let (all_incre, set_all_incre) = signal(Vec::<TimePoint>::new());
    let (date_tips, set_date_tips) = signal(Vec::<TimePoint>::new());
    let (is_single, set_is_single) = signal(false);
    let (expire_index, set_expire_index) = signal(-1);
    let (sel_dot_style, set_sel_dot_style) = signal(String::new());
    let (sel_dot_class, set_sel_dot_class) = signal(String::new());
    let (can_line_style, set_can_line_style) = signal(String::new());
    let preview_point = Memo::new(move |_| {
        active.get().and_then(|index| incre_dates.with(|points| points.get(index).cloned()))
    });

    Effect::new(move |_| {
        initialize_timeline(
            &time_points,
            set_sel_time,
            set_start_date,
            set_end_date,
            set_incre_dates,
            set_all_incre,
            set_date_tips,
            set_is_single,
            set_expire_index,
            set_can_line_style,
            set_sel_dot_style,
            set_sel_dot_class,
            all_incre,
            reference_time,
        );
    });

    let format_time_label =
        move |value: &DateTime<FixedOffset>, is_day: bool, index: usize| -> String {
            if !is_day {
                return format!("{}", value.format("%Y/%m/%d %H:%M:%S"));
            }

            let tips = date_tips.get();
            if tips.len() > 1 && index < tips.len() - 1 {
                let cur_percent = calculate_position_percent(
                    &tips[index].timepoint,
                    start_date.get(),
                    end_date.get(),
                );
                let next_percent = calculate_position_percent(
                    &tips[index + 1].timepoint,
                    start_date.get(),
                    end_date.get(),
                );
                if next_percent - cur_percent < 8.0 {
                    return String::new();
                }
            }
            format!("{}", value.format("%m/%d"))
        };

    let format_backup_type = |backup_type: i32| -> &'static str {
        match backup_type {
            0 => "Abstract Submission:",
            1 => "Paper Submission:",
            2 => "Rebuttal Submission:",
            3 => "Final Decisions:",
            4 => "Conference Opening:",
            _ => "",
        }
    };

    let format_backup_class = |backup_type: i32| -> &'static str {
        match backup_type {
            0 => "square square_all",
            1 => "dot dot_all",
            2 => "dot dot_all dot_rebuttal",
            3 => "dot dot_all dot_decision",
            4 => "dot dot_all",
            _ => "",
        }
    };

    let calculate_backup_position = move |time: &DateTime<FixedOffset>, index: usize| -> String {
        let left_percent = calculate_position_percent(time, start_date.get(), end_date.get());

        let clamped_percent = left_percent.max(0.5).min(99.5);
        let base_style = format!("left:{}%;", clamped_percent);

        if index as i32 <= expire_index.get() {
            format!("{}border: 2px solid #ccc;", base_style)
        } else {
            base_style
        }
    };

    let calculate_reference_position = move |time: &DateTime<FixedOffset>| -> String {
        let left_percent = calculate_position_percent(time, start_date.get(), end_date.get());

        let clamped_percent = left_percent.max(0.0).min(100.0);
        format!("left:{}%;", clamped_percent)
    };

    view! {
        <div
            class="time_con"
            class:is-interacting=move || active.get().is_some()
            on:click=move |_| dismiss()
            on:keydown=move |event| {
                if event.key() == "Escape" && active.get_untracked().is_some() {
                    event.stop_propagation();
                    event.prevent_default();
                    dismiss();
                }
            }
        >
            <style>
                r#"
                /* 时间轴容器 */
                .time_con {

                }

                /* 时间轴主容器 */
                .line_time {
                    position: relative;
                    -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                    user-select: none;
                }

                /* 时间轴外层容器 */
                .line_time .all_line {
                    width: 90%;
                    margin: 0 5%;
                    padding-top: 0;
                    padding-bottom: 15px;
                }

                .line_time .timeline-preview-slot {
                    display: flex;
                    align-items: flex-end;
                    min-height: 44px;
                    padding-bottom: 12px;
                    box-sizing: border-box;
                }

                .line_time .timeline-preview {
                    max-width: 100%;
                    min-width: 0;
                    color: #409eff;
                    font-size: 12px;
                    line-height: 1.4;
                    font-style: normal;
                    white-space: normal;
                    overflow-wrap: anywhere;
                }

                .line_time .timeline-event {
                    padding: 0;
                    cursor: pointer;
                }

                .line_time .timeline-event::before {
                    content: "";
                    position: absolute;
                    inset: -8px;
                }

                .line_time .timeline-event:focus-visible,
                .line_time .timeline-event[aria-pressed="true"] {
                    outline: 2px solid #409eff;
                    outline-offset: 3px;
                }

                .time_con.is-interacting .sel_dot {
                    visibility: hidden;
                }

                /* 时间轴主线 */
                .line_time .line {
                    width: 100%;
                    height: 3px;
                    background: #ccc;
                    position: relative;
                }

                /* 可进度线 */
                .line_time .can_line {
                    background: #1890ff77;
                    height: 3px;
                    width: 0%;
                    position: absolute;
                    left: 0;
                }

                .line_time .can_line span {
                    position: absolute;
                    right: 0;
                    margin-top: 20px;
                }

                /* 参考时间点 */
                .line_time .reference {
                    width: 1px;
                    height: 8px;
                    border: 0;
                    background: #bbb;
                    position: absolute;
                    top: -3px;
                    white-space: nowrap;
                }

                .line_time .reference em {
                    color: #bbb;
                    position: absolute;
                    transform: translateX(-50%);
                    margin-top: 5px;
                    font-size: 12px;
                }

                /* 圆形备份点 */
                .line_time .dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    border: 2px solid #4a9eff;
                    background: white;
                    position: absolute;
                    top: -3px;
                    white-space: nowrap;
                    margin-left: -4px;
                    box-sizing: border-box;
                }

                .line_time .dot_all:hover {
                    width: 10px;
                    height: 10px;
                    border: 2px solid #409eff;
                    top: -4px;
                }

                .line_time .dot_rebuttal {
                    border-color: #d59a2a;
                    background: #fff9eb;
                }

                .line_time .dot_decision {
                    border-color: #55a66a;
                    background: #f1faf3;
                }

                /* 方形备份点 */
                .line_time .square {
                    width: 8px;
                    height: 8px;
                    border-radius: 0;
                    border: 2px solid #4a9eff;
                    background: white;
                    position: absolute;
                    top: -3px;
                    white-space: nowrap;
                    margin-left: -4px;
                    box-sizing: border-box;
                }

                .line_time .square_all:hover {
                    width: 10px;
                    height: 10px;
                    border: 2px solid #409eff;
                    top: -4px;
                }

                /* 当前选中点 */
                .line_time .sel_dot {
                    pointer-events: none;
                    width: 10px;
                    height: 10px;
                    top: -4px;
                    border: 2px solid #FFA500;
                    box-shadow: 0 0 10px 4px rgba(255, 163, 2, 0.3);
                    z-index: 5;
                    position: absolute;
                }

                "#
            </style>

            <div class="line_time">
                <div class="all_line">
                    <div
                        class="timeline-preview-slot"
                        style=move || {
                            let percent = preview_point.get().map(|point| {
                                calculate_position_percent(&point.timepoint, start_date.get(), end_date.get())
                            }).unwrap_or(50.0);
                            if percent < 35.0 {
                                "justify-content:flex-start;text-align:left;"
                            } else if percent > 65.0 {
                                "justify-content:flex-end;text-align:right;"
                            } else {
                                "justify-content:center;text-align:center;"
                            }
                        }
                    >
                        {move || preview_point.get().map(|point| view! {
                            <div class="timeline-preview" style=if point.timepoint <= reference_time {
                                "color:#7a8795;"
                            } else {
                                ""
                            }>
                                {format_backup_type(point.r#type)} " "
                                {format_time_label(&point.timepoint, false, 0)}
                            </div>
                        })}
                    </div>
                    <div class="line">
                        <div class="can_line" style=move || can_line_style.get()></div>

                        {move || {
                            let is_single_val = is_single.get();
                            let date_tips_val = date_tips.get();
                            date_tips_val
                                .into_iter()
                                .enumerate()
                                .map(|(index, date_tip)| {
                                    let style = calculate_reference_position(&date_tip.timepoint);
                                    let should_show = !(index == 0 && is_single_val);

                                    view! {
                                        <div class="reference" style=style>
                                            {move || {
                                                if should_show {
                                                    let label = format_time_label(
                                                        &date_tip.timepoint,
                                                        true,
                                                        index,
                                                    );
                                                    if !label.is_empty() {
                                                        view! { <em>{label}</em> }.into_any()
                                                    } else {
                                                        view! {}.into_any()
                                                    }
                                                } else {
                                                    view! {}.into_any()
                                                }
                                            }}
                                        </div>
                                    }
                                })
                                .collect_view()
                        }}

                        {move || {
                            incre_dates
                                .get()
                                .into_iter()
                                .enumerate()
                                .map(|(index, backup_point)| {
                                    let class_name = format_backup_class(backup_point.r#type);
                                    let style = calculate_backup_position(
                                        &backup_point.timepoint,
                                        index,
                                    );
                                    let type_label = format_backup_type(backup_point.r#type);
                                    let time_label = format_time_label(
                                        &backup_point.timepoint,
                                        false,
                                        0,
                                    );

                                    view! {
                                        <button
                                            type="button"
                                            class=format!("timeline-event {class_name}")
                                            style=style
                                            aria-label=format!("{type_label} {time_label}")
                                            aria-pressed=move || (selected.get() == Some(index)).to_string()
                                            on:pointerenter=move |_| hovered.set(Some(index))
                                            on:pointerleave=move |_| hovered.set(None)
                                            on:focus=move |_| focused.set(Some(index))
                                            on:blur=move |_| {
                                                focused.set(None);
                                                if selected.get_untracked() == Some(index) {
                                                    selected.set(None);
                                                }
                                            }
                                            on:click=move |event| {
                                                event.stop_propagation();
                                                hovered.set(None);
                                                focused.set(None);
                                                selected.update(|value| {
                                                    *value = if *value == Some(index) { None } else { Some(index) };
                                                });
                                            }
                                        ></button>
                                    }
                                })
                                .collect_view()
                        }}

                        <div
                            class=move || format!("dot sel_dot {}", sel_dot_class.get())
                            style=move || sel_dot_style.get()
                            data-label=if has_custom_reference { "BASE" } else { "NOW" }
                            title=move || format!("{}: {}", if has_custom_reference { "Base" } else { "Now" }, sel_time.get())
                        >

                        </div>
                    </div>
                </div>
            </div>
        </div>
    }
}

fn calculate_position_percent(time: &DateTime<FixedOffset>, start: f64, end: f64) -> f64 {
    let timestamp = time.timestamp() as f64;
    (timestamp - start) / (end - start) * 100.0
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

fn timestamp_to_datetime(timestamp: f64, timezone: FixedOffset) -> DateTime<FixedOffset> {
    DateTime::from_timestamp(timestamp as i64, 0)
        .expect("Invalid timestamp")
        .with_timezone(&timezone)
}

fn initialize_timeline(
    time_points: &[TimePoint],
    set_sel_time: WriteSignal<String>,
    set_start_date: WriteSignal<f64>,
    set_end_date: WriteSignal<f64>,
    set_incre_dates: WriteSignal<Vec<TimePoint>>,
    set_all_incre: WriteSignal<Vec<TimePoint>>,
    set_date_tips: WriteSignal<Vec<TimePoint>>,
    set_is_single: WriteSignal<bool>,
    set_expire_index: WriteSignal<i32>,
    set_can_line_style: WriteSignal<String>,
    set_sel_dot_style: WriteSignal<String>,
    set_sel_dot_class: WriteSignal<String>,
    all_incre: ReadSignal<Vec<TimePoint>>,
    reference_time: DateTime<Utc>,
) {
    let (_, now_timezone) = get_browser_time_and_timezone();
    let now = reference_time.with_timezone(&now_timezone);
    let now_timestamp = now.timestamp() as f64;

    let deadlines = time_points.to_vec();
    let is_single_point = time_points.len() == 1;

    if is_single_point {
        set_is_single.set(true);
    } else {
        set_is_single.set(false);
    }

    let expire_idx = deadlines
        .iter()
        .enumerate()
        .rev()
        .find(|(_, point)| now_timestamp >= point.timepoint.timestamp() as f64)
        .map(|(i, _)| i as i32)
        .unwrap_or(-1);
    set_expire_index.set(expire_idx);

    let first_time = deadlines[0].timepoint.timestamp() as f64;
    let start_time = if now_timestamp < first_time {
        (now - Duration::days(7)).timestamp() as f64
    } else {
        (deadlines[0].timepoint - Duration::days(7)).timestamp() as f64
    };
    let end_time = (deadlines.last().unwrap().timepoint + Duration::days(7)).timestamp() as f64;

    set_start_date.set(start_time);
    set_end_date.set(end_time);

    let last_deadline_time = deadlines.last().unwrap().timepoint.timestamp() as f64;
    let progress_ratio = (last_deadline_time - now_timestamp) / (end_time - start_time);

    if progress_ratio > 0.0 {
        let width = progress_ratio * 100.0;
        let left = (now_timestamp - start_time) / (end_time - start_time) * 100.0;
        let max_width = 100.0 - left;
        set_can_line_style.set(format!(
            "width:{}%;left:{}%;max-width:{}%;",
            width, left, max_width
        ));
    } else {
        set_can_line_style.set("width:0%;".to_string());
    }

    set_incre_dates.set(deadlines.clone());
    set_date_tips.set(deadlines.clone());

    let mut all_incremental = deadlines.clone();
    all_incremental.push(TimePoint {
        timepoint: deadlines.last().unwrap().timepoint,
        r#type: 1,
        round: deadlines.last().map(|point| point.round).unwrap_or(1),
        comment: None,
    });
    all_incremental.push(TimePoint {
        timepoint: now,
        r#type: 1,
        round: 1,
        comment: None,
    });
    set_all_incre.set(all_incremental);

    update_selected_dot(
        now_timestamp,
        now_timezone,
        set_sel_dot_style,
        set_sel_dot_class,
        set_sel_time,
        start_time,
        end_time,
        last_deadline_time,
        now_timestamp,
        all_incre.get(),
    );
}

fn update_selected_dot(
    target_time: f64,
    time_zone: FixedOffset,
    set_sel_dot_style: WriteSignal<String>,
    set_sel_dot_class: WriteSignal<String>,
    set_sel_time: WriteSignal<String>,
    start_date: f64,
    end_date: f64,
    binlog_date: f64,
    full_date: f64,
    all_incre: Vec<TimePoint>,
) {
    let mut actual_time = target_time;
    let mut position_ratio = (target_time - start_date) / (end_date - start_date);

    if actual_time > binlog_date || actual_time < full_date {
        let nearest_point = all_incre
            .iter()
            .min_by(|a, b| {
                let a_diff = (a.timepoint.timestamp() as f64 - actual_time).abs();
                let b_diff = (b.timepoint.timestamp() as f64 - actual_time).abs();
                a_diff.partial_cmp(&b_diff).unwrap()
            })
            .unwrap();

        actual_time = nearest_point.timepoint.timestamp() as f64;
        position_ratio = (actual_time - start_date) / (end_date - start_date);
    }

    let datetime = timestamp_to_datetime(actual_time, time_zone);
    set_sel_time.set(format!("{}", datetime.format("%Y-%m-%d %H:%M:%S")));

    let left_percent = position_ratio * 100.0;
    let clamped_percent = left_percent.max(0.5).min(99.5);
    set_sel_dot_style.set(format!("left:{}%;", clamped_percent));

    let class_suffix = if clamped_percent < 10.0 {
        "sel_dot_left"
    } else if clamped_percent > 90.0 {
        "sel_dot_right"
    } else {
        ""
    };
    set_sel_dot_class.set(class_suffix.to_string());
}
