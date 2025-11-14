use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use wasm_bindgen_futures::spawn_local;
use web_sys::{console, js_sys, window};

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
        spawn_local(async move {
            match fetch_latest_commit().await {
                Ok((show_conf, conf_str)) => {
                    set_show_latest_conf.set(show_conf);
                    set_show_str.set(conf_str);
                }
                Err(_) => {

                }
            }
        });
    });

    view! {
        <section>
            <div style="display: inline-block; align-items: center; font-size: 16px;">
                <a href="/" class="title">
                    "CCFDDL"
                    <sup>"®"</sup>
                    "\u{00a0}Open Deadlines"
                </a>
                <div style="padding-left: 5px; display: inline-block;">
                    <GitButton />
                </div>
                {move || {
                    show_latest_conf
                        .get()
                        .then(|| {
                            view! {
                                <span style="display: inline-block; color:#fd3c95;font-weight: bold; font-size: 16px;">
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
                "Preview tabular portal:\u{00a0}"
                <a style="color: #666666" href="https://ccfddl.cn/" target="_blank">
                    "https://ccfddl.cn/"
                </a> ", or scan to try\u{00a0}"
                <a
                    style="color: #666666"
                    href="https://github.com/ccfddl/ccf-deadlines/blob/main/.readme_assets/applet_qrcode.jpg"
                    target="_blank"
                >
                    "wechat applet"
                </a> "."
            </div>
            <div class="el-row subtitle">
                "*Disclaimer: The data provided by ccfddl is manually collected and for reference purposes only."
            </div>
        </section>
    }
}

async fn fetch_latest_commit() -> Result<(bool, String), Box<dyn std::error::Error>> {
    let url = "https://api.github.com/repos/ccfddl/ccf-deadlines/commits?page=1&per_page=10";

    let response = reqwest::get(url).await?;
    let commits: Vec<CommitData> = response.json().await?;

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
