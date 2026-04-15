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
) -> impl IntoView {
    let remaining_time = RwSignal::new(remain / 1000);
    let urgency = Memo::new(move |_| get_urgency(remaining_time.get()));

    use_interval(1000, move || {
        remaining_time.update(|r| {
            if *r > 0 {
                *r -= 1;
            }
        });
    });

    let display_time = move || {
        let mut secs = remaining_time.get();
        let days = secs / (24 * 3600);
        secs %= 24 * 3600;
        let hours = secs / 3600;
        secs %= 3600;
        let minutes = secs / 60;
        let seconds = secs % 60;

        (days, hours, minutes, seconds)
    };

    let urgency_class = move || {
        match urgency.get() {
            UrgencyLevel::Normal => "countdown-normal",
            UrgencyLevel::Attention => "countdown-attention",
            UrgencyLevel::Warning => "countdown-warning",
            UrgencyLevel::Urgent => "countdown-urgent",
        }
    };

    view! {
        <span class=urgency_class>
            <span class="countdown-value">
                {move || {
                    let (days, hours, minutes, seconds) = display_time();
                    if days > 0 {
                        format!("{:02}d {:02}h {:02}m {:02}s", days, hours, minutes, seconds)
                    } else if hours > 0 {
                        format!("{:02}h {:02}m {:02}s", hours, minutes, seconds)
                    } else {
                        format!("{:02}m {:02}s", minutes, seconds)
                    }
                }}
            </span>
        </span>
    }
}
