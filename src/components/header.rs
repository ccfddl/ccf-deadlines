use gloo_net::http::Request;
use leptos::prelude::*;
use leptos::{ev, leptos_dom::helpers::window_event_listener};
use serde::{Deserialize, Serialize};
use std::time::Duration;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::spawn_local;
use web_sys::window;

use crate::components::favorites::{FavoritesContext, start_github_login};
use crate::components::gitbutton::GitButton;
use thaw::Icon;

#[derive(Debug, Deserialize, Serialize, Clone)]
struct CommitData {
    commit: CommitInfo,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct CommitInfo {
    message: String,
}

#[component]
pub fn Header(
    use_english: RwSignal<bool>,
    show_favorites_timeline: RwSignal<bool>,
) -> impl IntoView {
    let favorites = expect_context::<FavoritesContext>();
    let (show_latest_conf, set_show_latest_conf) = signal(false);
    let (show_str, set_show_str) = signal(String::new());
    let outside_listener = window_event_listener(ev::click, move |event| {
        let Some(details) = window()
            .and_then(|browser| browser.document())
            .and_then(|document| document.get_element_by_id("github-account-menu"))
        else {
            return;
        };
        let clicked_inside = event
            .target()
            .and_then(|target| target.dyn_into::<web_sys::Element>().ok())
            .and_then(|target| target.closest("#github-account-menu").ok().flatten())
            .is_some();
        if !clicked_inside {
            let _ = details.remove_attribute("open");
        }
    });
    on_cleanup(move || outside_listener.remove());

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
                <div class="header-auth">
                    {move || {
                        if !favorites.loaded.get() {
                            view! {
                                <button type="button" class="github-login-button github-login-button--checking" disabled aria-busy="true">
                                    <Icon icon=icondata::BsGithub />
                                    <span>{move || if use_english.get() { "Signing in with GitHub..." } else { "GitHub登陆中" }}</span>
                                </button>
                            }
                                .into_any()
                        } else if let Some(user) = favorites.user.get() {
                            view! {
                                <details id="github-account-menu" class="github-account-menu">
                                    <summary class="github-account-trigger">
                                        <img src=user.avatar_url alt="" aria-hidden="true" />
                                        <span class="github-account-name">{user.login}</span>
                                        <span class="github-account-chevron" aria-hidden="true"></span>
                                    </summary>
                                    <div class="github-account-options">
                                        <button
                                            type="button"
                                            on:click=move |_| {
                                                close_account_menu();
                                                show_favorites_timeline.set(true);
                                            }
                                        >
                                            {move || if use_english.get() { "My Favorites" } else { "我的收藏" }}
                                        </button>
                                        <button
                                            type="button"
                                            on:click=move |_| {
                                                close_account_menu();
                                                favorites.logout();
                                            }
                                        >
                                            {move || if use_english.get() { "Sign out" } else { "退出" }}
                                        </button>
                                    </div>
                                </details>
                            }
                                .into_any()
                        } else if favorites.error.get().is_some() {
                            view! {
                                <button
                                    type="button"
                                    class="github-auth-retry"
                                    on:click=move |_| favorites.load()
                                >
                                    {move || if use_english.get() {
                                        "Sign-in check failed · Retry"
                                    } else {
                                        "登录状态检查失败 · 重试"
                                    }}
                                </button>
                            }
                                .into_any()
                        } else {
                            view! {
                                <button
                                    type="button"
                                    class="github-login-button"
                                    on:click=move |_| start_github_login()
                                >
                                    <Icon icon=icondata::BsGithub />
                                    <span>
                                        {move || if use_english.get() {
                                            "Sign in with GitHub"
                                        } else {
                                            "使用 GitHub 登录"
                                        }}
                                    </span>
                                </button>
                            }
                                .into_any()
                        }
                    }}
                </div>
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

fn close_account_menu() {
    if let Some(details) = window()
        .and_then(|browser| browser.document())
        .and_then(|document| document.get_element_by_id("github-account-menu"))
    {
        let _ = details.remove_attribute("open");
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
