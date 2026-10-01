use gloo_net::http::Request;
use leptos::prelude::*;
use serde::Deserialize;
use std::time::Duration;
use thaw::Icon;
use wasm_bindgen_futures::spawn_local;

#[derive(Deserialize)]
struct RepositoryStats {
    stargazers_count: u64,
}

const STAR_COUNT_KEY: &str = "github_star_count";
const STAR_COUNT_UPDATED_KEY: &str = "github_star_count_updated_at";
const STAR_COUNT_CACHE_TTL_MS: f64 = 6.0 * 60.0 * 60.0 * 1000.0;

#[component]
pub fn GitButton() -> impl IntoView {
    let (cached_count, cache_is_fresh) = read_cached_star_count();
    let star_count = RwSignal::new(cached_count);

    Effect::new(move |_| {
        if cache_is_fresh {
            return;
        }

        let handle = set_timeout_with_handle(
            move || {
                spawn_local(async move {
                    if let Ok(count) = fetch_star_count().await {
                        star_count.set(Some(count));
                        cache_star_count(count);
                    }
                });
            },
            Duration::from_millis(2000),
        )
        .ok();

        on_cleanup(move || {
            if let Some(handle) = handle {
                handle.clear();
            }
        });
    });

    view! {
        <a
            class="github-star-link"
            href="https://github.com/ccfddl/ccf-deadlines"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Star ccfddl/ccf-deadlines on GitHub"
        >
            <Icon icon=icondata::BsGithub />
            <span class="github-star-label">"Star"</span>
            {move || {
                star_count.get().map(|count| {
                    view! {
                        <span class="github-star-count">{format_count(count)}</span>
                    }
                })
            }}
        </a>
    }
}

async fn fetch_star_count() -> Result<u64, Box<dyn std::error::Error>> {
    let repository = Request::get("https://api.github.com/repos/ccfddl/ccf-deadlines")
        .send()
        .await?
        .json::<RepositoryStats>()
        .await?;
    Ok(repository.stargazers_count)
}

fn read_cached_star_count() -> (Option<u64>, bool) {
    let Some(storage) = web_sys::window()
        .and_then(|window| window.local_storage().ok())
        .flatten()
    else {
        return (None, false);
    };
    let count = storage
        .get_item(STAR_COUNT_KEY)
        .ok()
        .flatten()
        .and_then(|value| value.parse::<u64>().ok());
    let updated_at = storage
        .get_item(STAR_COUNT_UPDATED_KEY)
        .ok()
        .flatten()
        .and_then(|value| value.parse::<f64>().ok());
    let is_fresh = updated_at
        .map(|timestamp| web_sys::js_sys::Date::now() - timestamp < STAR_COUNT_CACHE_TTL_MS)
        .unwrap_or(false);
    (count, is_fresh)
}

fn cache_star_count(count: u64) {
    let Some(storage) = web_sys::window()
        .and_then(|window| window.local_storage().ok())
        .flatten()
    else {
        return;
    };
    let _ = storage.set_item(STAR_COUNT_KEY, &count.to_string());
    let _ = storage.set_item(
        STAR_COUNT_UPDATED_KEY,
        &web_sys::js_sys::Date::now().to_string(),
    );
}

fn format_count(count: u64) -> String {
    let digits = count.to_string();
    let mut formatted = String::with_capacity(digits.len() + digits.len() / 3);
    let first_group = digits.len() % 3;

    for (index, character) in digits.chars().enumerate() {
        if index > 0 && index >= first_group && (index - first_group) % 3 == 0 {
            formatted.push(',');
        }
        formatted.push(character);
    }
    formatted
}
