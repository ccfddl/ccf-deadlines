use crate::components::conf::ConfItem;
use crate::components::countdown::CountDown;
use crate::components::favorites::{FavoritesContext, start_github_login};
use chrono::{DateTime, FixedOffset, Utc};
use leptos::prelude::*;
use std::collections::HashMap;
use std::time::Duration;
use thaw::*;

#[derive(Clone, Debug, PartialEq)]
struct FavoriteTimelineEvent {
    conference_id: String,
    conference_title: String,
    conference_year: i32,
    link: String,
    timepoint: DateTime<FixedOffset>,
    deadline_type: i32,
    round: usize,
    multi_round: bool,
    color: String,
}

#[derive(Clone, Debug, PartialEq)]
enum FavoriteTimelineRow {
    Now,
    Event(FavoriteTimelineEvent),
}

#[derive(Clone, Debug, PartialEq)]
struct FavoriteConferenceLegend {
    id: String,
    label: String,
    color: String,
}

#[derive(Clone, Debug, PartialEq)]
struct FavoriteTimelineData {
    rows: Vec<FavoriteTimelineRow>,
    legends: Vec<FavoriteConferenceLegend>,
    awaiting_dates: Vec<ConfItem>,
}

#[component]
pub fn FavoritesTimelineModal(
    show: RwSignal<bool>,
    use_english: RwSignal<bool>,
    conferences: RwSignal<Vec<ConfItem>>,
    reference_time: RwSignal<Option<DateTime<Utc>>>,
    display_timezone: RwSignal<String>,
) -> impl IntoView {
    let favorites = expect_context::<FavoritesContext>();
    let timeline = Memo::new(move |_| {
        build_favorite_timeline(
            conferences.get(),
            reference_time.get().unwrap_or_else(Utc::now),
        )
    });
    let now_marker_ref = NodeRef::<leptos::html::Div>::new();

    Effect::new(move |_| {
        if !show.get() {
            return;
        }
        let _ = timeline.get();
        set_timeout(
            move || {
                if let Some(marker) = now_marker_ref.get() {
                    marker.scroll_into_view_with_bool(true);
                }
            },
            Duration::from_millis(40),
        );
    });

    view! {
        <Dialog open=show>
            <DialogSurface class="conference-detail-dialog favorites-timeline-dialog">
                <DialogBody>
                    <DialogTitle class="conference-detail-title favorites-timeline-title">
                        <Icon icon=icondata::MdiTimelineClockOutline />
                        <span>{move || if use_english.get() {
                            "My Favorites Timeline"
                        } else {
                            "我的收藏时间线"
                        }}</span>
                    </DialogTitle>
                    <button
                        type="button"
                        class="conference-detail-close"
                        aria-label=move || if use_english.get() { "Close" } else { "关闭" }
                        on:click=move |_| show.set(false)
                    >"×"</button>
                    <DialogContent>
                        <div class="favorites-timeline-shell">
                            <p class="favorites-timeline-intro">
                                {move || if use_english.get() {
                                    "Every deadline from your starred conference editions, in one place."
                                } else {
                                    "收藏会议的所有重要节点将在一条时间线上展示"
                                }}
                            </p>

                            {move || {
                                if !favorites.loaded.get() {
                                    view! {
                                        <div class="favorites-timeline-status">
                                            {if use_english.get() {
                                                "Loading favorites..."
                                            } else {
                                                "正在加载收藏……"
                                            }}
                                        </div>
                                    }
                                        .into_any()
                                } else if favorites.user.get().is_none() {
                                    view! {
                                        <button
                                            type="button"
                                            class="favorites-timeline-login"
                                            on:click=move |_| start_github_login()
                                        >
                                            <Icon icon=icondata::BsGithub />
                                            <span>{move || if use_english.get() {
                                                "Sign in with GitHub to view your timeline"
                                            } else {
                                                "使用 GitHub 登录后查看收藏时间线"
                                            }}</span>
                                        </button>
                                    }
                                        .into_any()
                                } else {
                                    let data = timeline.get();
                                    if data.legends.is_empty() {
                                        view! {
                                            <div class="favorites-timeline-empty">
                                                <Icon icon=icondata::BsStar />
                                                <strong>{if use_english.get() {
                                                    "No favorites yet"
                                                } else {
                                                    "还没有收藏会议"
                                                }}</strong>
                                                <span>{if use_english.get() {
                                                    "Star a conference edition to add its dates here."
                                                } else {
                                                    "在会议卡片上点亮星标后，重要日期会出现在这里。"
                                                }}</span>
                                            </div>
                                        }
                                            .into_any()
                                    } else {
                                        let awaiting_dates = data.awaiting_dates.clone();
                                        let has_awaiting_dates = !awaiting_dates.is_empty();
                                        view! {
                                            <div class="favorites-timeline-legends" aria-label=move || {
                                                if use_english.get() {
                                                    "Conference colors"
                                                } else {
                                                    "会议颜色"
                                                }
                                            }>
                                                {data
                                                    .legends
                                                    .into_iter()
                                                    .map(|legend| {
                                                        view! {
                                                            <span
                                                                class="favorites-timeline-legend"
                                                                title=legend.id
                                                            >
                                                                <i style=format!("background:{}", legend.color)></i>
                                                                {legend.label}
                                                            </span>
                                                        }
                                                    })
                                                    .collect_view()}
                                            </div>
                                            <div class="favorites-timeline-scroll">
                                                <div class="favorites-timeline-rows">
                                                    {data
                                                        .rows
                                                        .into_iter()
                                                        .map(|row| match row {
                                                            FavoriteTimelineRow::Now => view! {
                                                                <div
                                                                    node_ref=now_marker_ref
                                                                    class="favorites-timeline-row favorites-timeline-now"
                                                                >
                                                                    <span class="favorites-timeline-date">
                                                                        {move || if use_english.get() { "NOW" } else { "现在" }}
                                                                    </span>
                                                                    <span class="favorites-timeline-rail">
                                                                        <i></i>
                                                                    </span>
                                                                    <span class="favorites-timeline-now-line"></span>
                                                                </div>
                                                            }
                                                                .into_any(),
                                                            FavoriteTimelineRow::Event(event) => {
                                                                let is_past = event.timepoint.timestamp_millis()
                                                                    <= reference_time
                                                                        .get_untracked()
                                                                        .unwrap_or_else(Utc::now)
                                                                        .timestamp_millis();
                                                                let remaining = event
                                                                    .timepoint
                                                                    .timestamp_millis()
                                                                    .saturating_sub(
                                                                        reference_time
                                                                            .get_untracked()
                                                                            .unwrap_or_else(Utc::now)
                                                                            .timestamp_millis(),
                                                                    )
                                                                    .max(0) as u64;
                                                                let running = reference_time.get_untracked().is_none();
                                                                let date = event.timepoint.format("%b %-d, %Y").to_string();
                                                                let clock = event.timepoint.format("%H:%M").to_string();
                                                                let deadline_label = deadline_label(
                                                                    event.deadline_type,
                                                                    event.round,
                                                                    event.multi_round,
                                                                );
                                                                view! {
                                                                    <div
                                                                        class="favorites-timeline-row favorites-timeline-event"
                                                                        class:favorites-timeline-event--past=is_past
                                                                        style=format!("--conference-color:{}", event.color)
                                                                    >
                                                                        <span class="favorites-timeline-date">
                                                                            <strong>{date}</strong>
                                                                            <small>{clock}</small>
                                                                        </span>
                                                                        <span class="favorites-timeline-rail">
                                                                            <i></i>
                                                                        </span>
                                                                        <article class="favorites-timeline-card">
                                                                            <div class="favorites-timeline-card-heading">
                                                                                <a
                                                                                    href=event.link
                                                                                    target="_blank"
                                                                                    rel="noopener noreferrer"
                                                                                >
                                                                                    {format!("{} {}", event.conference_title, event.conference_year)}
                                                                                </a>
                                                                                <span>{deadline_label}</span>
                                                                            </div>
                                                                            <div class="favorites-timeline-card-meta">
                                                                                <span>{move || display_timezone.get()}</span>
                                                                                {if is_past {
                                                                                    view! {
                                                                                        <span class="favorites-timeline-passed">
                                                                                            {move || if use_english.get() { "passed" } else { "已结束" }}
                                                                                        </span>
                                                                                    }
                                                                                        .into_any()
                                                                                } else {
                                                                                    view! {
                                                                                        <CountDown remain=remaining running=running />
                                                                                    }
                                                                                        .into_any()
                                                                                }}
                                                                            </div>
                                                                        </article>
                                                                    </div>
                                                                }
                                                                    .into_any()
                                                            }
                                                        })
                                                        .collect_view()}
                                                </div>

                                                <Show when=move || has_awaiting_dates>
                                                    <section class="favorites-timeline-tbd">
                                                        <h3>{move || if use_english.get() {
                                                            "Awaiting dates"
                                                        } else {
                                                            "日期待定"
                                                        }}</h3>
                                                        <div>
                                                            {awaiting_dates
                                                                .clone()
                                                                .into_iter()
                                                                .map(|conference| view! {
                                                                    <a
                                                                        href=conference.link
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                    >
                                                                        <Icon icon=icondata::BsStarFill />
                                                                        {format!("{} {}", conference.title, conference.year)}
                                                                        <small>"TBD"</small>
                                                                    </a>
                                                                })
                                                                .collect_view()}
                                                        </div>
                                                    </section>
                                                </Show>
                                            </div>
                                        }
                                            .into_any()
                                    }
                                }
                            }}
                        </div>
                    </DialogContent>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    }
}

fn build_favorite_timeline(
    conferences: Vec<ConfItem>,
    reference_time: DateTime<Utc>,
) -> FavoriteTimelineData {
    let mut favorites = conferences
        .into_iter()
        .filter(|conference| conference.is_like)
        .collect::<Vec<_>>();
    favorites.sort_by(|left, right| {
        left.title
            .cmp(&right.title)
            .then_with(|| left.year.cmp(&right.year))
    });

    let mut colors = HashMap::new();
    let legends = favorites
        .iter()
        .enumerate()
        .map(|(index, conference)| {
            let color = conference_color(index);
            colors.insert(conference.id.clone(), color.clone());
            FavoriteConferenceLegend {
                id: conference.id.clone(),
                label: format!("{} {}", conference.title, conference.year),
                color,
            }
        })
        .collect::<Vec<_>>();

    let mut awaiting_dates = Vec::new();
    let mut events = Vec::new();
    for conference in favorites {
        if conference.ddls.is_empty() {
            awaiting_dates.push(conference);
            continue;
        }
        let multi_round = conference
            .ddls
            .iter()
            .map(|point| point.round)
            .max()
            .unwrap_or_default()
            > 1;
        let color = colors[&conference.id].clone();
        for point in conference.ddls {
            events.push(FavoriteTimelineEvent {
                conference_id: conference.id.clone(),
                conference_title: conference.title.clone(),
                conference_year: conference.year,
                link: conference.link.clone(),
                timepoint: point.timepoint,
                deadline_type: point.r#type,
                round: point.round,
                multi_round,
                color: color.clone(),
            });
        }
    }
    events.sort_by_key(|event| event.timepoint);
    awaiting_dates.sort_by(|left, right| {
        left.title
            .cmp(&right.title)
            .then_with(|| left.year.cmp(&right.year))
    });

    FavoriteTimelineData {
        rows: insert_now_row(events, reference_time),
        legends,
        awaiting_dates,
    }
}

fn insert_now_row(
    events: Vec<FavoriteTimelineEvent>,
    reference_time: DateTime<Utc>,
) -> Vec<FavoriteTimelineRow> {
    let mut rows = Vec::with_capacity(events.len() + 1);
    let mut inserted = false;
    for event in events {
        if !inserted && event.timepoint.timestamp_millis() >= reference_time.timestamp_millis() {
            rows.push(FavoriteTimelineRow::Now);
            inserted = true;
        }
        rows.push(FavoriteTimelineRow::Event(event));
    }
    if !inserted {
        rows.push(FavoriteTimelineRow::Now);
    }
    rows
}

fn deadline_label(deadline_type: i32, round: usize, multi_round: bool) -> String {
    let label = match deadline_type {
        0 => "Abstract Submission",
        1 => "Paper Submission",
        2 => "Rebuttal Submission",
        3 => "Final Decisions",
        _ => "Deadline",
    };
    if multi_round {
        format!("Round {round} {label}")
    } else {
        label.to_string()
    }
}

fn conference_color(index: usize) -> String {
    let hue = (index * 137 + 207) % 360;
    format!("hsl({hue}deg 48% 47%)")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::components::conf::TimePoint;

    fn favorite(id: &str, title: &str, timestamps: &[i64]) -> ConfItem {
        ConfItem {
            title: title.to_string(),
            description: String::new(),
            sub: "AI".to_string(),
            rank: "A".to_string(),
            corerank: None,
            thcplrank: None,
            displayrank: "CCF A".to_string(),
            dblp: String::new(),
            year: 2027,
            id: id.to_string(),
            link: format!("https://example.com/{id}"),
            abstract_deadline: None,
            deadline: String::new(),
            deadline_type: 1,
            comment: None,
            timezone: "UTC".to_string(),
            date: String::new(),
            place: String::new(),
            status: "RUN".to_string(),
            is_like: true,
            remain: 0,
            subname: String::new(),
            subname_en: String::new(),
            acc_str: None,
            ddls: timestamps
                .iter()
                .map(|timestamp| TimePoint {
                    timepoint: DateTime::from_timestamp(*timestamp, 0)
                        .expect("test timestamp is valid")
                        .fixed_offset(),
                    r#type: 1,
                    round: 1,
                })
                .collect(),
            estimated_deadlines: Vec::new(),
        }
    }

    #[test]
    fn merges_favorites_around_now_with_distinct_conference_colors() {
        let reference = DateTime::from_timestamp(200, 0).expect("test timestamp is valid");
        let data = build_favorite_timeline(
            vec![
                favorite("beta27", "Beta", &[300]),
                favorite("alpha27", "Alpha", &[100]),
            ],
            reference,
        );

        assert_eq!(data.legends.len(), 2);
        assert_ne!(data.legends[0].color, data.legends[1].color);
        assert!(matches!(data.rows[0], FavoriteTimelineRow::Event(_)));
        assert!(matches!(data.rows[1], FavoriteTimelineRow::Now));
        assert!(matches!(data.rows[2], FavoriteTimelineRow::Event(_)));
    }

    #[test]
    fn keeps_favorites_without_published_dates_in_tbd_section() {
        let reference = DateTime::from_timestamp(200, 0).expect("test timestamp is valid");
        let data = build_favorite_timeline(vec![favorite("tbd27", "TBD", &[])], reference);

        assert_eq!(data.awaiting_dates.len(), 1);
        assert!(matches!(data.rows.as_slice(), [FavoriteTimelineRow::Now]));
    }
}
