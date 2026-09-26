use leptos::prelude::*;
use std::time::Duration;

#[derive(Clone, Copy, PartialEq)]
pub enum UrgencyLevel {
    Normal,
    Attention,
    Warning,
    Urgent,
}

fn get_urgency(remaining_secs: u64) -> UrgencyLevel {
    if remaining_secs < 3 * 86400 {
        UrgencyLevel::Urgent
    } else if remaining_secs < 7 * 86400 {
        UrgencyLevel::Warning
    } else if remaining_secs < 30 * 86400 {
        UrgencyLevel::Attention
    } else {
        UrgencyLevel::Normal
    }
}

pub fn urgency_class_for(remaining_secs: u64) -> &'static str {
    match get_urgency(remaining_secs) {
        UrgencyLevel::Normal => "countdown-normal",
        UrgencyLevel::Attention => "countdown-attention",
        UrgencyLevel::Warning => "countdown-warning",
        UrgencyLevel::Urgent => "countdown-urgent",
    }
}

pub fn use_interval<T, F>(interval_millis: T, f: F)
where
    F: Fn() + Clone + 'static,
    T: Into<Signal<u64>> + 'static,
{
    let interval_millis = interval_millis.into();
    Effect::new(move |prev_handle: Option<IntervalHandle>| {
        if let Some(prev_handle) = prev_handle {
            prev_handle.clear();
        }
        set_interval_with_handle(f.clone(), Duration::from_millis(interval_millis.get()))
            .expect("could not create interval")
    });
}

#[component]
pub fn CountDown(
    remain: u64,
    use_english: RwSignal<bool>,
    #[prop(default = false)] detailed: bool,
    #[prop(default = false)] legacy: bool,
    #[prop(default = true)] running: bool,
) -> impl IntoView {
    let remaining_time = RwSignal::new(remain / 1000);

    use_interval(1000, move || {
        if running {
            remaining_time.update(|r| {
                if *r > 0 {
                    *r -= 1;
                }
            });
        }
    });

    let urgency_class = move || urgency_class_for(remaining_time.get());

    view! {
        <span class=urgency_class>
            {if legacy {
                view! {
                    <span class="countdown-legacy-value">
                        {move || format_legacy_countdown(remaining_time.get(), use_english.get())}
                    </span>
                }
                    .into_any()
            } else if detailed {
                view! {
                    <span class="countdown-detailed-value">
                        {move || format_detailed_countdown(remaining_time.get(), use_english.get())}
                    </span>
                }.into_any()
            } else {
                view! {
                    <span class="countdown-value">
                        {move || format_compact_countdown(remaining_time.get(), use_english.get())}
                    </span>
                }.into_any()
            }}
        </span>
    }
}

/// Splits a number of seconds into (days, hours, minutes, seconds).
fn split_duration(total_secs: u64) -> (u64, u64, u64, u64) {
    (
        total_secs / 86400,
        total_secs % 86400 / 3600,
        total_secs % 3600 / 60,
        total_secs % 60,
    )
}

/// Short countdown shown on conference cards, e.g. "in 3d 19h" / "还剩 3天19小时".
pub fn format_compact_countdown(total_secs: u64, english: bool) -> String {
    let (days, hours, minutes, seconds) = split_duration(total_secs);
    if english {
        if days > 0 {
            format!("in {}d {}h", days, hours)
        } else if hours > 0 {
            format!("in {:02}h {:02}m", hours, minutes)
        } else if minutes > 0 {
            format!("in {:02}m {:02}s", minutes, seconds)
        } else {
            format!("in {}s", seconds)
        }
    } else if days > 0 {
        format!("还剩 {}天{}小时", days, hours)
    } else if hours > 0 {
        format!("还剩 {}小时{:02}分", hours, minutes)
    } else if minutes > 0 {
        format!("还剩 {}分{:02}秒", minutes, seconds)
    } else {
        format!("还剩 {}秒", seconds)
    }
}

/// Full countdown shown in the conference detail dialog.
pub fn format_detailed_countdown(total_secs: u64, english: bool) -> String {
    let (days, hours, minutes, seconds) = split_duration(total_secs);
    if english {
        format!("{}d {:02}h {:02}m {:02}s", days, hours, minutes, seconds)
    } else {
        format!(
            "{}天 {:02}时 {:02}分 {:02}秒",
            days, hours, minutes, seconds
        )
    }
}

/// Countdown used by the legacy list view (UI 1.0).
pub fn format_legacy_countdown(total_secs: u64, english: bool) -> String {
    let (days, hours, minutes, seconds) = split_duration(total_secs);
    if english {
        let day_label = if days == 1 { "day" } else { "days" };
        format!(
            "{:02} {} {:02} h {:02} m {:02} s",
            days, day_label, hours, minutes, seconds,
        )
    } else {
        format!(
            "{:02}天 {:02}时 {:02}分 {:02}秒",
            days, hours, minutes, seconds
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DAY: u64 = 86400;

    #[test]
    fn english_countdowns_keep_their_format() {
        assert_eq!(
            format_compact_countdown(3 * DAY + 19 * 3600, true),
            "in 3d 19h"
        );
        assert_eq!(
            format_compact_countdown(5 * 3600 + 7 * 60, true),
            "in 05h 07m"
        );
        assert_eq!(format_compact_countdown(12 * 60 + 5, true), "in 12m 05s");
        assert_eq!(format_compact_countdown(42, true), "in 42s");
        assert_eq!(
            format_detailed_countdown(2 * DAY + 3723, true),
            "2d 01h 02m 03s"
        );
        assert_eq!(
            format_legacy_countdown(DAY + 3723, true),
            "01 day 01 h 02 m 03 s"
        );
        assert_eq!(
            format_legacy_countdown(2 * DAY, true),
            "02 days 00 h 00 m 00 s"
        );
    }

    #[test]
    fn chinese_countdowns_use_chinese_units() {
        assert_eq!(
            format_compact_countdown(3 * DAY + 19 * 3600, false),
            "还剩 3天19小时"
        );
        assert_eq!(
            format_compact_countdown(5 * 3600 + 7 * 60, false),
            "还剩 5小时07分"
        );
        assert_eq!(
            format_compact_countdown(12 * 60 + 5, false),
            "还剩 12分05秒"
        );
        assert_eq!(format_compact_countdown(42, false), "还剩 42秒");
        assert_eq!(
            format_detailed_countdown(2 * DAY + 3723, false),
            "2天 01时 02分 03秒"
        );
        assert_eq!(
            format_legacy_countdown(DAY + 3723, false),
            "01天 01时 02分 03秒"
        );
    }
}
