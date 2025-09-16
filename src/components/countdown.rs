use leptos::prelude::*;
use std::time::Duration;

/// Countdown timer component.
#[component]
pub fn CountDown(
    /// The remaining time in seconds.
    remain: u64,
) -> impl IntoView {
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
        let seconds = secs % 60;

        let day_string = if days > 1 { "days" } else { "day" };

        format!(
            "{:02} {} {:02} h {:02} m {:02} s",
            days, day_string, hours, minutes, seconds
        )
    };

    view! { {display_time} }
}

/// A hook to create a reactive interval.
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

        set_interval_with_handle(
            f.clone(),
            Duration::from_millis(interval_millis.get()),
        )
        .expect("could not create interval")
    });
}
