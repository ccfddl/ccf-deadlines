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
pub fn CountDown(remain: u64, #[prop(default = false)] detailed: bool) -> impl IntoView {
    let remaining_time = RwSignal::new(remain / 1000);

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

        (days, hours, minutes)
    };

    let urgency_class = move || urgency_class_for(remaining_time.get());

    view! {
        <span class=urgency_class>
            {if detailed {
                view! {
                    <span class="countdown-detailed-value">
                        {move || {
                            let (days, hours, minutes) = display_time();
                            format!("{}d {:02}h {:02}m {:02}s", days, hours, minutes, remaining_time.get() % 60)
                        }}
                    </span>
                }.into_any()
            } else {
                view! {
                    <span class="countdown-value">
                        {move || {
                            let (days, hours, minutes) = display_time();
                            if days > 0 {
                                format!("in {}d {}h", days, hours)
                            } else if hours > 0 {
                                format!("in {:02}h {:02}m", hours, minutes)
                            } else if minutes > 0 {
                                let seconds = remaining_time.get() % 60;
                                format!("in {:02}m {:02}s", minutes, seconds)
                            } else {
                                format!("in {}s", remaining_time.get() % 60)
                            }
                        }}
                    </span>
                }.into_any()
            }}
        </span>
    }
}
