use leptos::prelude::*;
use serde::{Deserialize, Serialize};
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
pub fn Header(use_english: RwSignal<bool>) -> impl IntoView {
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
                Err(_) => {}
            }
        });
    });

    view! {
        <section>
            <div class="header-main">
                <a href="/" class="title">
                    <span class="title-normal">"CCFDDL"</span>
                    <span class="title-normal">"\u{00a0}Open "</span>
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
                                    {move || if use_english.get() { "Latest: " } else { "最新：" }} {show_str.get()} " !!!"
                                </span>
                            }
                        })
                }}
            </div>
            <div class="el-row subtitle">
                {move || if use_english.get() {
                    "Worldwide Conference Deadline Countdowns. To add/edit a conference,\u{00a0}"
                } else {
                    "全球学术会议截止日期倒计时。添加或修改会议信息，请\u{00a0}"
                }}
                <a
                    style="color: #666666"
                    href="https://github.com/ccfddl/ccf-deadlines/pulls"
                    target="_blank"
                >
                    {move || if use_english.get() { "send a pull request" } else { "提交 Pull Request" }}
                </a> "."
            </div>
            <div class="el-row subtitle">
                {move || if use_english.get() {
                    "*Disclaimer: The data provided by ccfddl is agenticly collected and for reference purposes only."
                } else {
                    "*免责声明：ccfddl 的数据由自动化方式收集，仅供参考。"
                }}
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
