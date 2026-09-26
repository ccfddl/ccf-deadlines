use gloo_net::http::Request;
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use wasm_bindgen_futures::spawn_local;

use crate::components::gitbutton::GitButton;

#[derive(Debug, Deserialize, Serialize, Clone)]
struct CommitData {
    commit: CommitInfo,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct CommitInfo {
    message: String,
}

#[component]
pub fn Header() -> impl IntoView {
    let (show_latest_conf, set_show_latest_conf) = signal(false);
    let (show_str, set_show_str) = signal(String::new());

    // Effect to fetch GitHub commits data on mount
    Effect::new(move |_| {
        let handle = set_timeout_with_handle(
            move || {
                spawn_local(async move {
                    if let Ok((show_conf, conf_str)) = fetch_latest_commit().await {
                        set_show_latest_conf.set(show_conf);
                        set_show_str.set(conf_str);
                    }
                });
            },
            Duration::from_millis(1500),
        )
        .ok();
        on_cleanup(move || {
            if let Some(handle) = handle {
                handle.clear();
            }
        });
    });

    view! {
        <section>
            <div class="header-main">
                <a href="/" class="title">
                    <span class="title-normal">"CCFDDL"</span>
                    <span class="title-normal">"\u{00a0}Open\u{00a0}"</span>
                    <span class="title-accent">"Deadlines"</span>
                </a>
                <div class="header-github">
                    <GitButton />
                </div>
                {move || {
                    show_latest_conf
                        .get()
                        .then(|| {
                            view! {
                                <span class="header-latest">
                                    "Latest: " {show_str.get()} " !!!"
                                </span>
                            }
                        })
                }}
            </div>
            <div class="el-row subtitle">
                "Worldwide Conference Deadline Countdowns. To add/edit a conference,\u{00a0}"
                <a
                    style="color: #666666"
                    href="https://github.com/ccfddl/ccf-deadlines/pulls"
                    target="_blank"
                >
                    "send a pull request"
                </a> "."
            </div>
            <div class="el-row subtitle">
                "*Disclaimer: The data provided by ccfddl is agenticly collected and for reference purposes only."
            </div>
        </section>
    }
}

async fn fetch_latest_commit() -> Result<(bool, String), Box<dyn std::error::Error>> {
    let url = "https://api.github.com/repos/ccfddl/ccf-deadlines/commits?page=1&per_page=10";

    let commits = Request::get(url)
        .send()
        .await?
        .json::<Vec<CommitData>>()
        .await?;

    for commit in commits {
        let message = commit.commit.message;
        let words: Vec<&str> = message.split_whitespace().collect();

        if !words.is_empty() {
            let first_word: String = words[0].to_lowercase();
            if first_word == "update" || first_word == "add" {
                let mut result_str: String = message[..].to_string();
                if let Some(idx) = message.find('(') {
                    result_str = message[..idx].to_string();
                }
                return Ok((true, result_str));
            }
        }
    }

    Ok((false, String::new()))
}
