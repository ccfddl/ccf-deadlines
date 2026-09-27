use crate::components::favorites::{FavoritesContext, api_url, start_github_login};
use chrono::{DateTime, Utc};
use gloo_net::http::{Request, Response};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use thaw::*;
use wasm_bindgen_futures::spawn_local;

const MESSAGE_MAX_CHARACTERS: usize = 500;

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
struct WallAuthor {
    login: String,
    avatar_url: String,
    profile_url: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
struct WallMessage {
    id: i64,
    body: String,
    created_at: i64,
    author: WallAuthor,
    can_delete: bool,
}

#[derive(Debug, Deserialize)]
struct WallMessagesResponse {
    messages: Vec<WallMessage>,
}

#[derive(Debug, Deserialize)]
struct WallMessageResponse {
    message: WallMessage,
}

#[derive(Debug, Deserialize)]
struct ApiError {
    error: String,
}

#[derive(Debug, Serialize)]
struct CreateWallMessage<'a> {
    body: &'a str,
}

#[component]
pub fn MessageWallModal(show: RwSignal<bool>, use_english: RwSignal<bool>) -> impl IntoView {
    let favorites = expect_context::<FavoritesContext>();
    let messages = RwSignal::new(Vec::<WallMessage>::new());
    let draft = RwSignal::new(String::new());
    let loading = RwSignal::new(false);
    let submitting = RwSignal::new(false);
    let deleting = RwSignal::new(HashSet::<i64>::new());
    let error = RwSignal::new(None::<String>);

    Effect::new(move |_| {
        if show.get() {
            load_messages(messages, loading, error);
        }
    });

    let submit = move |_| {
        if favorites.user.get_untracked().is_none() {
            start_github_login();
            return;
        }
        let body = draft.get_untracked().trim().to_string();
        let character_count = body.chars().count();
        if body.is_empty() || character_count > MESSAGE_MAX_CHARACTERS {
            return;
        }

        submitting.set(true);
        error.set(None);
        spawn_local(async move {
            match create_message(&body).await {
                Ok(message) => {
                    messages.update(|items| {
                        items.insert(0, message);
                        items.truncate(50);
                    });
                    draft.set(String::new());
                }
                Err(message) => error.set(Some(message)),
            }
            submitting.set(false);
        });
    };

    view! {
        <Dialog open=show>
            <DialogSurface class="conference-detail-dialog wall-dialog">
                <DialogBody>
                    <DialogTitle class="conference-detail-title wall-title">
                        <Icon icon=icondata::BsChatDots />
                        <span>{move || if use_english.get() { "Message Wall" } else { "漂流墙" }}</span>
                    </DialogTitle>
                    <button
                        type="button"
                        class="conference-detail-close"
                        aria-label=move || if use_english.get() { "Close" } else { "关闭" }
                        on:click=move |_| show.set(false)
                    >"×"</button>
                    <DialogContent>
                        <div class="wall-shell">
                            <p class="wall-intro">
                                {move || if use_english.get() {
                                    "Leave a short note for fellow researchers around the world."
                                } else {
                                    "留下一句话，和世界各地的同行打个招呼。"
                                }}
                            </p>

                            {move || {
                                if let Some(user) = favorites.user.get() {
                                    view! {
                                        <div class="wall-composer">
                                            <div class="wall-composer-user">
                                                <img src=user.avatar_url alt="" aria-hidden="true" />
                                                <span>{format!("@{}", user.login)}</span>
                                            </div>
                                            <textarea
                                                class="wall-textarea"
                                                rows="3"
                                                maxlength=MESSAGE_MAX_CHARACTERS
                                                prop:value=move || draft.get()
                                                disabled=move || submitting.get()
                                                placeholder=move || if use_english.get() {
                                                    "Share a thought, question, or encouragement..."
                                                } else {
                                                    "分享想法、问题，或者一句鼓励……"
                                                }
                                                on:input=move |event| draft.set(event_target_value(&event))
                                            ></textarea>
                                            <div class="wall-composer-footer">
                                                <span class="wall-character-count">
                                                    {move || format!("{}/{}", draft.get().chars().count(), MESSAGE_MAX_CHARACTERS)}
                                                </span>
                                                <Button
                                                    size=ButtonSize::Small
                                                    disabled=Signal::derive(move || {
                                                        let text = draft.get();
                                                        submitting.get()
                                                            || text.trim().is_empty()
                                                            || text.trim().chars().count() > MESSAGE_MAX_CHARACTERS
                                                    })
                                                    on_click=submit
                                                >
                                                    <Icon icon=icondata::FiSend style="margin-right: 4px;" />
                                                    {move || if submitting.get() {
                                                        if use_english.get() { "Posting..." } else { "发送中……" }
                                                    } else if use_english.get() {
                                                        "Send"
                                                    } else {
                                                        "投递"
                                                    }}
                                                </Button>
                                            </div>
                                        </div>
                                    }
                                        .into_any()
                                } else {
                                    view! {
                                        <button
                                            type="button"
                                            class="wall-login-button"
                                            on:click=move |_| start_github_login()
                                        >
                                            <Icon icon=icondata::BsGithub />
                                            <span>{move || if use_english.get() {
                                                "Sign in with GitHub to leave a message"
                                            } else {
                                                "使用 GitHub 登录后投递留言"
                                            }}</span>
                                        </button>
                                    }
                                        .into_any()
                                }
                            }}

                            <Show when=move || error.get().is_some()>
                                <div class="wall-error" role="alert">
                                    {move || error.get().unwrap_or_default()}
                                </div>
                            </Show>

                            <div class="wall-feed" aria-live="polite">
                                <Show
                                    when=move || !loading.get()
                                    fallback=move || view! {
                                        <div class="wall-status">
                                            {move || if use_english.get() { "Loading messages..." } else { "正在捞取留言……" }}
                                        </div>
                                    }
                                >
                                    {move || {
                                        let items = messages.get();
                                        if items.is_empty() {
                                            view! {
                                                <Show when=move || error.get().is_none()>
                                                    <div class="wall-status">
                                                        {if use_english.get() {
                                                            "No messages yet. Send the first one."
                                                        } else {
                                                            "还没有留言，来投递第一条吧。"
                                                        }}
                                                    </div>
                                                </Show>
                                            }
                                                .into_any()
                                        } else {
                                            items
                                                .into_iter()
                                                .map(|message| {
                                                    let message_id = message.id;
                                                    let can_delete = message.can_delete;
                                                    let body = message.body;
                                                    let time = format_message_time(message.created_at);
                                                    let login = message.author.login;
                                                    let avatar_alt = format!("@{login}");
                                                    let avatar_url = message.author.avatar_url;
                                                    let profile_url = message.author.profile_url;
                                                    view! {
                                                        <article class="wall-message">
                                                            <a
                                                                class="wall-message-avatar"
                                                                href=profile_url
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            >
                                                                <img src=avatar_url alt=avatar_alt />
                                                            </a>
                                                            <div class="wall-message-main">
                                                                <div class="wall-message-meta">
                                                                    <strong>{format!("@{login}")}</strong>
                                                                    <time>{time}</time>
                                                                    {can_delete.then(|| {
                                                                        view! {
                                                                            <button
                                                                                type="button"
                                                                                class="wall-delete-button"
                                                                                disabled=move || deleting.with(|ids| ids.contains(&message_id))
                                                                                aria-label=move || if use_english.get() { "Delete message" } else { "删除留言" }
                                                                                title=move || if use_english.get() { "Delete message" } else { "删除留言" }
                                                                                on:click=move |_| {
                                                                                    let prompt = if use_english.get_untracked() {
                                                                                        "Delete this message?"
                                                                                    } else {
                                                                                        "删除这条留言？"
                                                                                    };
                                                                                    let confirmed = web_sys::window()
                                                                                        .and_then(|window| window.confirm_with_message(prompt).ok())
                                                                                        .unwrap_or(false);
                                                                                    if !confirmed {
                                                                                        return;
                                                                                    }
                                                                                    deleting.update(|ids| {
                                                                                        ids.insert(message_id);
                                                                                    });
                                                                                    spawn_local(async move {
                                                                                        match delete_message(message_id).await {
                                                                                            Ok(()) => messages.update(|items| {
                                                                                                items.retain(|item| item.id != message_id);
                                                                                            }),
                                                                                            Err(message) => error.set(Some(message)),
                                                                                        }
                                                                                        deleting.update(|ids| {
                                                                                            ids.remove(&message_id);
                                                                                        });
                                                                                    });
                                                                                }
                                                                            >
                                                                                <Icon icon=icondata::FiTrash2 />
                                                                            </button>
                                                                        }
                                                                    })}
                                                                </div>
                                                                <p>{body}</p>
                                                            </div>
                                                        </article>
                                                    }
                                                })
                                                .collect_view()
                                                .into_any()
                                        }
                                    }}
                                </Show>
                            </div>
                        </div>
                    </DialogContent>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    }
}

fn load_messages(
    messages: RwSignal<Vec<WallMessage>>,
    loading: RwSignal<bool>,
    error: RwSignal<Option<String>>,
) {
    loading.set(true);
    error.set(None);
    spawn_local(async move {
        match fetch_messages().await {
            Ok(items) => messages.set(items),
            Err(message) => error.set(Some(message)),
        }
        loading.set(false);
    });
}

async fn fetch_messages() -> Result<Vec<WallMessage>, String> {
    let response = Request::get(&api_url("/api/messages"))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(api_error(response).await);
    }
    response
        .json::<WallMessagesResponse>()
        .await
        .map(|payload| payload.messages)
        .map_err(|error| error.to_string())
}

async fn create_message(body: &str) -> Result<WallMessage, String> {
    let request = Request::post(&api_url("/api/messages"))
        .json(&CreateWallMessage { body })
        .map_err(|error| error.to_string())?;
    let response = request.send().await.map_err(|error| error.to_string())?;
    if response.status() == 401 {
        start_github_login();
        return Err("GitHub sign-in is required.".to_string());
    }
    if !response.ok() {
        return Err(api_error(response).await);
    }
    response
        .json::<WallMessageResponse>()
        .await
        .map(|payload| payload.message)
        .map_err(|error| error.to_string())
}

async fn delete_message(message_id: i64) -> Result<(), String> {
    let response = Request::delete(&api_url(&format!("/api/messages/{message_id}")))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if response.status() == 401 {
        start_github_login();
        return Err("GitHub sign-in is required.".to_string());
    }
    if !response.ok() {
        return Err(api_error(response).await);
    }
    Ok(())
}

async fn api_error(response: Response) -> String {
    let status = response.status();
    response
        .json::<ApiError>()
        .await
        .map(|payload| payload.error)
        .unwrap_or_else(|_| format!("Message wall API returned HTTP {status}"))
}

fn format_message_time(timestamp: i64) -> String {
    DateTime::<Utc>::from_timestamp(timestamp, 0)
        .map(|date| date.format("%b %-d, %Y · %H:%M UTC").to_string())
        .unwrap_or_default()
}
