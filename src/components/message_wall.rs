use crate::components::favorites::{FavoritesContext, api_url, start_github_login};
use chrono::{DateTime, Utc};
use gloo_net::http::{Request, Response};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
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
    like_count: usize,
    liked_by_me: bool,
    parent_id: Option<i64>,
    reply_count: usize,
}

#[derive(Debug, Deserialize)]
struct WallMessagesResponse {
    messages: Vec<WallMessage>,
    next_cursor: Option<usize>,
}

#[derive(Debug, Deserialize)]
struct WallMessageResponse {
    message: WallMessage,
}

#[derive(Debug, Deserialize)]
struct WallLikeResponse {
    count: usize,
    liked: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum WallSort {
    Latest,
    Likes,
    Mine,
}

impl WallSort {
    fn query_value(self) -> &'static str {
        match self {
            Self::Latest => "latest",
            Self::Likes => "likes",
            Self::Mine => "mine",
        }
    }
}

#[derive(Debug, Deserialize)]
struct ApiError {
    error: String,
}

#[derive(Debug, Serialize)]
struct CreateWallMessage<'a> {
    body: &'a str,
    parent_id: Option<i64>,
}

#[component]
pub fn MessageWallModal(show: RwSignal<bool>, use_english: RwSignal<bool>) -> impl IntoView {
    let favorites = expect_context::<FavoritesContext>();
    let messages = RwSignal::new(Vec::<WallMessage>::new());
    let next_cursor = RwSignal::new(None::<usize>);
    let sort = RwSignal::new(WallSort::Latest);
    let draft = RwSignal::new(String::new());
    let composer_open = RwSignal::new(false);
    let loading = RwSignal::new(false);
    let loading_more = RwSignal::new(false);
    let submitting = RwSignal::new(false);
    let deleting = RwSignal::new(HashSet::<i64>::new());
    let liking = RwSignal::new(HashSet::<i64>::new());
    let replies = RwSignal::new(HashMap::<i64, Vec<WallMessage>>::new());
    let reply_cursors = RwSignal::new(HashMap::<i64, usize>::new());
    let expanded_replies = RwSignal::new(HashSet::<i64>::new());
    let loading_replies = RwSignal::new(HashSet::<i64>::new());
    let replying_to = RwSignal::new(None::<(i64, String)>);
    let reply_draft = RwSignal::new(String::new());
    let submitting_reply = RwSignal::new(false);
    let error = RwSignal::new(None::<String>);

    Effect::new(move |_| {
        if show.get() {
            load_messages(messages, next_cursor, loading, error, sort.get(), sort);
        } else {
            composer_open.set(false);
        }
    });

    Effect::new(move |_| {
        if favorites.user.get().is_none() && sort.get() == WallSort::Mine {
            sort.set(WallSort::Latest);
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
            match create_message(&body, None).await {
                Ok(message) => {
                    draft.set(String::new());
                    composer_open.set(false);
                    if sort.get_untracked() == WallSort::Likes {
                        load_messages(messages, next_cursor, loading, error, WallSort::Likes, sort);
                    } else {
                        messages.update(|items| {
                            items.insert(0, message);
                        });
                    }
                }
                Err(message) => error.set(Some(message)),
            }
            submitting.set(false);
        });
    };

    let load_more = move |_| {
        let Some(cursor) = next_cursor.get_untracked() else {
            return;
        };
        loading_more.set(true);
        error.set(None);
        let selected_sort = sort.get_untracked();
        spawn_local(async move {
            match fetch_messages(selected_sort, Some(cursor)).await {
                Ok(payload) => {
                    if sort.get_untracked() == selected_sort {
                        messages.update(|items| {
                            let existing = items.iter().map(|item| item.id).collect::<HashSet<_>>();
                            items.extend(
                                payload
                                    .messages
                                    .into_iter()
                                    .filter(|item| !existing.contains(&item.id)),
                            );
                        });
                        next_cursor.set(payload.next_cursor);
                    }
                }
                Err(message) => {
                    if sort.get_untracked() == selected_sort {
                        error.set(Some(message));
                    }
                }
            }
            loading_more.set(false);
        });
    };

    let toggle_replies = move |parent_id: i64| {
        if expanded_replies.with_untracked(|ids| ids.contains(&parent_id)) {
            expanded_replies.update(|ids| {
                ids.remove(&parent_id);
            });
            return;
        }
        expanded_replies.update(|ids| {
            ids.insert(parent_id);
        });
        if !replies.with_untracked(|items| items.contains_key(&parent_id)) {
            load_reply_page(
                parent_id,
                None,
                replies,
                reply_cursors,
                loading_replies,
                error,
            );
        }
    };

    let submit_reply = move |parent_id: i64| {
        let body = reply_draft.get_untracked().trim().to_string();
        if body.is_empty() || body.chars().count() > MESSAGE_MAX_CHARACTERS {
            return;
        }
        submitting_reply.set(true);
        error.set(None);
        spawn_local(async move {
            match create_message(&body, Some(parent_id)).await {
                Ok(_) => {
                    reply_draft.set(String::new());
                    replying_to.set(None);
                    expanded_replies.update(|ids| {
                        ids.insert(parent_id);
                    });
                    messages.update(|items| {
                        if let Some(parent) = items.iter_mut().find(|item| item.id == parent_id) {
                            parent.reply_count += 1;
                        }
                    });
                    load_reply_page(
                        parent_id,
                        None,
                        replies,
                        reply_cursors,
                        loading_replies,
                        error,
                    );
                }
                Err(message) => error.set(Some(message)),
            }
            submitting_reply.set(false);
        });
    };

    view! {
        <Dialog open=show>
            <DialogSurface class="conference-detail-dialog wall-dialog">
                <DialogBody>
                    <DialogTitle class="conference-detail-title wall-title">
                        <Icon icon=icondata::BsChatDots />
                        <span>{move || if use_english.get() { "Message Wall" } else { "吹水墙" }}</span>
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
                                    "赶ddl累了？来吹水解压～"
                                }}
                            </p>

                            <div class="wall-toolbar">
                                <div class="wall-sort-tabs" role="tablist">
                                    <button
                                        type="button"
                                        role="tab"
                                        class="wall-sort-tab"
                                        class:wall-sort-tab--active=move || sort.get() == WallSort::Latest
                                        aria-selected=move || sort.get() == WallSort::Latest
                                        on:click=move |_| sort.set(WallSort::Latest)
                                    >
                                        {move || if use_english.get() { "Latest" } else { "最新" }}
                                    </button>
                                    <button
                                        type="button"
                                        role="tab"
                                        class="wall-sort-tab"
                                        class:wall-sort-tab--active=move || sort.get() == WallSort::Likes
                                        aria-selected=move || sort.get() == WallSort::Likes
                                        on:click=move |_| sort.set(WallSort::Likes)
                                    >
                                        {move || if use_english.get() {
                                            "Most liked (30d)"
                                        } else {
                                            "近30天最多点赞"
                                        }}
                                    </button>
                                    <Show when=move || favorites.user.get().is_some()>
                                        <button
                                            type="button"
                                            role="tab"
                                            class="wall-sort-tab"
                                            class:wall-sort-tab--active=move || sort.get() == WallSort::Mine
                                            aria-selected=move || sort.get() == WallSort::Mine
                                            on:click=move |_| sort.set(WallSort::Mine)
                                        >
                                            {move || if use_english.get() { "Mine" } else { "我的留言" }}
                                        </button>
                                    </Show>
                                </div>
                                <Show when=move || favorites.user.get().is_some()>
                                    <button
                                        type="button"
                                        class="wall-compose-toggle"
                                        class:wall-compose-toggle--active=move || composer_open.get()
                                        aria-expanded=move || composer_open.get()
                                        on:click=move |_| composer_open.update(|open| *open = !*open)
                                    >
                                        {move || if composer_open.get() {
                                            if use_english.get() { "Hide" } else { "收起" }
                                        } else if use_english.get() {
                                            "Write"
                                        } else {
                                            "写留言"
                                        }}
                                    </button>
                                </Show>
                            </div>

                            <Show when=move || composer_open.get() && favorites.user.get().is_some()>
                                {move || {
                                    favorites.user.get().map(|user| {
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
                                                    {move || if use_english.get() {
                                                        format!("{}/{} · 10/day", draft.get().chars().count(), MESSAGE_MAX_CHARACTERS)
                                                    } else {
                                                        format!("{}/{} · 每日 10 条", draft.get().chars().count(), MESSAGE_MAX_CHARACTERS)
                                                    }}
                                                </span>
                                                <button
                                                    type="button"
                                                    class="wall-composer-cancel"
                                                    disabled=move || submitting.get()
                                                    on:click=move |_| composer_open.set(false)
                                                >
                                                    {move || if use_english.get() { "Cancel" } else { "取消" }}
                                                </button>
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
                                    })
                                }}
                            </Show>

                            <Show when=move || favorites.user.get().is_none()>
                                <button
                                    type="button"
                                    class="wall-login-button"
                                    on:click=move |_| start_github_login()
                                >
                                    <Icon icon=icondata::BsGithub />
                                    <span>{move || if use_english.get() {
                                        "Sign in to post and browse all messages"
                                    } else {
                                        "使用 GitHub 登录后留言并浏览全部"
                                    }}</span>
                                </button>
                            </Show>

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
                                            view! {
                                                <>
                                                    {items
                                                        .into_iter()
                                                        .map(|message| {
                                                            let message_id = message.id;
                                                            let can_delete = message.can_delete;
                                                            let like_count = message.like_count;
                                                            let liked_by_me = message.liked_by_me;
                                                            let body = message.body;
                                                            let time = format_message_time(message.created_at);
                                                            let login = message.author.login;
                                                            let reply_login = login.clone();
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
                                                                        <div class="wall-message-actions">
                                                                            <button
                                                                                type="button"
                                                                                class="wall-reply-button"
                                                                                on:click=move |_| {
                                                                                    if favorites.user.get_untracked().is_none() {
                                                                                        start_github_login();
                                                                                        return;
                                                                                    }
                                                                                    reply_draft.set(String::new());
                                                                                    replying_to.set(Some((message_id, reply_login.clone())));
                                                                                }
                                                                            >
                                                                                {move || if use_english.get() { "Reply" } else { "回复" }}
                                                                            </button>
                                                                            <Show when=move || {
                                                                                messages.with(|items| items.iter().find(|item| item.id == message_id).is_some_and(|item| item.reply_count > 0))
                                                                            }>
                                                                                <button
                                                                                    type="button"
                                                                                    class="wall-reply-button"
                                                                                    on:click=move |_| toggle_replies(message_id)
                                                                                >
                                                                                    {move || {
                                                                                        let count = messages.with(|items| {
                                                                                            items.iter().find(|item| item.id == message_id).map(|item| item.reply_count).unwrap_or_default()
                                                                                        });
                                                                                        if use_english.get() {
                                                                                            format!("{count} replies")
                                                                                        } else {
                                                                                            format!("{count} 条回复")
                                                                                        }
                                                                                    }}
                                                                                </button>
                                                                            </Show>
                                                                            <button
                                                                                type="button"
                                                                                class=if liked_by_me {
                                                                                    "wall-like-button wall-like-button--active"
                                                                                } else {
                                                                                    "wall-like-button"
                                                                                }
                                                                                disabled=move || {
                                                                                    liking.with(|ids| ids.contains(&message_id))
                                                                                }
                                                                                aria-label=move || {
                                                                                    if liked_by_me {
                                                                                        if use_english.get() { "Unlike message" } else { "取消点赞" }
                                                                                    } else if use_english.get() {
                                                                                        "Like message"
                                                                                    } else {
                                                                                        "点赞"
                                                                                    }
                                                                                }
                                                                                title=move || {
                                                                                    if liked_by_me {
                                                                                        if use_english.get() { "Unlike" } else { "取消点赞" }
                                                                                    } else if use_english.get() {
                                                                                        "Like"
                                                                                    } else {
                                                                                        "点赞"
                                                                                    }
                                                                                }
                                                                                on:click=move |_| {
                                                                                    if favorites.user.get_untracked().is_none() {
                                                                                        start_github_login();
                                                                                        return;
                                                                                    }
                                                                                    liking.update(|ids| {
                                                                                        ids.insert(message_id);
                                                                                    });
                                                                                    spawn_local(async move {
                                                                                        let updated = match mutate_message_like(message_id, !liked_by_me).await {
                                                                                            Ok(result) => {
                                                                                                messages.update(|items| {
                                                                                                    if let Some(item) = items.iter_mut().find(|item| item.id == message_id) {
                                                                                                        item.like_count = result.count;
                                                                                                        item.liked_by_me = result.liked;
                                                                                                    }
                                                                                                });
                                                                                                true
                                                                                            }
                                                                                            Err(message) => {
                                                                                                error.set(Some(message));
                                                                                                false
                                                                                            }
                                                                                        };
                                                                                        liking.update(|ids| {
                                                                                            ids.remove(&message_id);
                                                                                        });
                                                                                        if updated && sort.get_untracked() == WallSort::Likes {
                                                                                            load_messages(
                                                                                                messages,
                                                                                                next_cursor,
                                                                                                loading,
                                                                                                error,
                                                                                                WallSort::Likes,
                                                                                                sort,
                                                                                            );
                                                                                        }
                                                                                    });
                                                                                }
                                                                            >
                                                                                {if liked_by_me {
                                                                                    view! { <Icon icon=icondata::BsHeartFill /> }.into_any()
                                                                                } else {
                                                                                    view! { <Icon icon=icondata::BsHeart /> }.into_any()
                                                                                }}
                                                                                <span>{like_count}</span>
                                                                            </button>
                                                                        </div>
                                                                        <Show when=move || {
                                                                            replying_to.with(|target| target.as_ref().is_some_and(|(id, _)| *id == message_id))
                                                                        }>
                                                                            <div class="wall-reply-composer">
                                                                                <div class="wall-replying-to">
                                                                                    {move || {
                                                                                        let login = replying_to.with(|target| {
                                                                                            target.as_ref().map(|(_, login)| login.clone()).unwrap_or_default()
                                                                                        });
                                                                                        if use_english.get() {
                                                                                            format!("Replying to @{login}")
                                                                                        } else {
                                                                                            format!("回复 @{login}")
                                                                                        }
                                                                                    }}
                                                                                </div>
                                                                                <textarea
                                                                                    rows="2"
                                                                                    maxlength=MESSAGE_MAX_CHARACTERS
                                                                                    prop:value=move || reply_draft.get()
                                                                                    disabled=move || submitting_reply.get()
                                                                                    placeholder=move || if use_english.get() { "Write a reply..." } else { "写下回复……" }
                                                                                    on:input=move |event| reply_draft.set(event_target_value(&event))
                                                                                ></textarea>
                                                                                <div class="wall-reply-composer-actions">
                                                                                    <span>{move || format!("{}/{}", reply_draft.get().chars().count(), MESSAGE_MAX_CHARACTERS)}</span>
                                                                                    <button
                                                                                        type="button"
                                                                                        disabled=move || submitting_reply.get()
                                                                                        on:click=move |_| {
                                                                                            replying_to.set(None);
                                                                                            reply_draft.set(String::new());
                                                                                        }
                                                                                    >
                                                                                        {move || if use_english.get() { "Cancel" } else { "取消" }}
                                                                                    </button>
                                                                                    <button
                                                                                        type="button"
                                                                                        disabled=move || {
                                                                                            let text = reply_draft.get();
                                                                                            submitting_reply.get()
                                                                                                || text.trim().is_empty()
                                                                                                || text.trim().chars().count() > MESSAGE_MAX_CHARACTERS
                                                                                        }
                                                                                        on:click=move |_| submit_reply(message_id)
                                                                                    >
                                                                                        {move || if submitting_reply.get() {
                                                                                            if use_english.get() { "Replying..." } else { "回复中……" }
                                                                                        } else if use_english.get() {
                                                                                            "Reply"
                                                                                        } else {
                                                                                            "回复"
                                                                                        }}
                                                                                    </button>
                                                                                </div>
                                                                            </div>
                                                                        </Show>
                                                                        <Show when=move || expanded_replies.with(|ids| ids.contains(&message_id))>
                                                                            <div class="wall-replies">
                                                                                <Show when=move || loading_replies.with(|ids| ids.contains(&message_id))>
                                                                                    <div class="wall-replies-status">
                                                                                        {move || if use_english.get() { "Loading replies..." } else { "正在加载回复……" }}
                                                                                    </div>
                                                                                </Show>
                                                                                {move || {
                                                                                    replies
                                                                                        .with(|items| items.get(&message_id).cloned().unwrap_or_default())
                                                                                        .into_iter()
                                                                                        .map(|reply| {
                                                                                            let reply_id = reply.id;
                                                                                            let reply_body = reply.body;
                                                                                            let reply_time = format_message_time(reply.created_at);
                                                                                            let reply_login = reply.author.login;
                                                                                            let reply_avatar = reply.author.avatar_url;
                                                                                            let reply_profile = reply.author.profile_url;
                                                                                            let reply_can_delete = reply.can_delete;
                                                                                            let reply_liked = reply.liked_by_me;
                                                                                            let reply_like_count = reply.like_count;
                                                                                            view! {
                                                                                                <article class="wall-reply">
                                                                                                    <a href=reply_profile target="_blank" rel="noopener noreferrer">
                                                                                                        <img src=reply_avatar alt=format!("@{reply_login}") />
                                                                                                    </a>
                                                                                                    <div class="wall-reply-main">
                                                                                                        <div class="wall-message-meta">
                                                                                                            <strong>{format!("@{reply_login}")}</strong>
                                                                                                            <time>{reply_time}</time>
                                                                                                            {reply_can_delete.then(|| view! {
                                                                                                                <button
                                                                                                                    type="button"
                                                                                                                    class="wall-delete-button"
                                                                                                                    disabled=move || deleting.with(|ids| ids.contains(&reply_id))
                                                                                                                    aria-label=move || if use_english.get() { "Delete reply" } else { "删除回复" }
                                                                                                                    title=move || if use_english.get() { "Delete reply" } else { "删除回复" }
                                                                                                                    on:click=move |_| {
                                                                                                                        deleting.update(|ids| { ids.insert(reply_id); });
                                                                                                                        spawn_local(async move {
                                                                                                                            match delete_message(reply_id).await {
                                                                                                                                Ok(()) => {
                                                                                                                                    replies.update(|items| {
                                                                                                                                        if let Some(thread) = items.get_mut(&message_id) {
                                                                                                                                            thread.retain(|item| item.id != reply_id);
                                                                                                                                        }
                                                                                                                                    });
                                                                                                                                    messages.update(|items| {
                                                                                                                                        if let Some(parent) = items.iter_mut().find(|item| item.id == message_id) {
                                                                                                                                            parent.reply_count = parent.reply_count.saturating_sub(1);
                                                                                                                                        }
                                                                                                                                    });
                                                                                                                                }
                                                                                                                                Err(message) => error.set(Some(message)),
                                                                                                                            }
                                                                                                                            deleting.update(|ids| { ids.remove(&reply_id); });
                                                                                                                        });
                                                                                                                    }
                                                                                                                >
                                                                                                                    <Icon icon=icondata::FiTrash2 />
                                                                                                                </button>
                                                                                                            })}
                                                                                                        </div>
                                                                                                        <p>{reply_body}</p>
                                                                                                        <div class="wall-message-actions">
                                                                                                            <button
                                                                                                                type="button"
                                                                                                                class=if reply_liked { "wall-like-button wall-like-button--active" } else { "wall-like-button" }
                                                                                                                disabled=move || liking.with(|ids| ids.contains(&reply_id))
                                                                                                                aria-label=move || if reply_liked {
                                                                                                                    if use_english.get() { "Unlike reply" } else { "取消点赞" }
                                                                                                                } else if use_english.get() { "Like reply" } else { "点赞" }
                                                                                                                on:click=move |_| {
                                                                                                                    if favorites.user.get_untracked().is_none() {
                                                                                                                        start_github_login();
                                                                                                                        return;
                                                                                                                    }
                                                                                                                    liking.update(|ids| { ids.insert(reply_id); });
                                                                                                                    spawn_local(async move {
                                                                                                                        match mutate_message_like(reply_id, !reply_liked).await {
                                                                                                                            Ok(result) => replies.update(|items| {
                                                                                                                                if let Some(thread) = items.get_mut(&message_id) {
                                                                                                                                    if let Some(item) = thread.iter_mut().find(|item| item.id == reply_id) {
                                                                                                                                        item.like_count = result.count;
                                                                                                                                        item.liked_by_me = result.liked;
                                                                                                                                    }
                                                                                                                                }
                                                                                                                            }),
                                                                                                                            Err(message) => error.set(Some(message)),
                                                                                                                        }
                                                                                                                        liking.update(|ids| { ids.remove(&reply_id); });
                                                                                                                    });
                                                                                                                }
                                                                                                            >
                                                                                                                {if reply_liked {
                                                                                                                    view! { <Icon icon=icondata::BsHeartFill /> }.into_any()
                                                                                                                } else {
                                                                                                                    view! { <Icon icon=icondata::BsHeart /> }.into_any()
                                                                                                                }}
                                                                                                                <span>{reply_like_count}</span>
                                                                                                            </button>
                                                                                                        </div>
                                                                                                    </div>
                                                                                                </article>
                                                                                            }
                                                                                        })
                                                                                        .collect_view()
                                                                                }}
                                                                                <Show when=move || {
                                                                                    favorites.user.get().is_some()
                                                                                        && reply_cursors.with(|cursors| cursors.contains_key(&message_id))
                                                                                }>
                                                                                    <button
                                                                                        type="button"
                                                                                        class="wall-replies-more"
                                                                                        disabled=move || loading_replies.with(|ids| ids.contains(&message_id))
                                                                                        on:click=move |_| {
                                                                                            if let Some(offset) = reply_cursors.with_untracked(|cursors| cursors.get(&message_id).copied()) {
                                                                                                load_reply_page(
                                                                                                    message_id,
                                                                                                    Some(offset),
                                                                                                    replies,
                                                                                                    reply_cursors,
                                                                                                    loading_replies,
                                                                                                    error,
                                                                                                );
                                                                                            }
                                                                                        }
                                                                                    >
                                                                                        {move || if use_english.get() { "Load more replies" } else { "加载更多回复" }}
                                                                                    </button>
                                                                                </Show>
                                                                            </div>
                                                                        </Show>
                                                                    </div>
                                                                </article>
                                                            }
                                                        })
                                                        .collect_view()}
                                                    <Show when=move || {
                                                        favorites.user.get().is_some() && next_cursor.get().is_some()
                                                    }>
                                                        <button
                                                            type="button"
                                                            class="wall-load-more"
                                                            disabled=move || loading_more.get()
                                                            on:click=load_more
                                                        >
                                                            {move || if loading_more.get() {
                                                                if use_english.get() { "Loading..." } else { "加载中……" }
                                                            } else if use_english.get() {
                                                                "Load more"
                                                            } else {
                                                                "加载更多"
                                                            }}
                                                        </button>
                                                    </Show>
                                                </>
                                            }
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
    next_cursor: RwSignal<Option<usize>>,
    loading: RwSignal<bool>,
    error: RwSignal<Option<String>>,
    selected_sort: WallSort,
    active_sort: RwSignal<WallSort>,
) {
    loading.set(true);
    error.set(None);
    spawn_local(async move {
        match fetch_messages(selected_sort, None).await {
            Ok(payload) => {
                if active_sort.get_untracked() == selected_sort {
                    messages.set(payload.messages);
                    next_cursor.set(payload.next_cursor);
                }
            }
            Err(message) => {
                if active_sort.get_untracked() == selected_sort {
                    error.set(Some(message));
                }
            }
        }
        if active_sort.get_untracked() == selected_sort {
            loading.set(false);
        }
    });
}

async fn fetch_messages(
    sort: WallSort,
    offset: Option<usize>,
) -> Result<WallMessagesResponse, String> {
    let mut path = format!("/api/messages?sort={}", sort.query_value());
    if let Some(cursor) = offset {
        path.push_str(&format!("&offset={cursor}"));
    }
    let response = Request::get(&api_url(&path))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(api_error(response).await);
    }
    response
        .json::<WallMessagesResponse>()
        .await
        .map_err(|error| error.to_string())
}

fn load_reply_page(
    parent_id: i64,
    offset: Option<usize>,
    replies: RwSignal<HashMap<i64, Vec<WallMessage>>>,
    reply_cursors: RwSignal<HashMap<i64, usize>>,
    loading_replies: RwSignal<HashSet<i64>>,
    error: RwSignal<Option<String>>,
) {
    if loading_replies.with_untracked(|ids| ids.contains(&parent_id)) {
        return;
    }
    loading_replies.update(|ids| {
        ids.insert(parent_id);
    });
    error.set(None);
    spawn_local(async move {
        match fetch_replies(parent_id, offset).await {
            Ok(payload) => {
                if offset.is_some() {
                    replies.update(|items| {
                        let thread = items.entry(parent_id).or_default();
                        let existing = thread.iter().map(|item| item.id).collect::<HashSet<_>>();
                        thread.extend(
                            payload
                                .messages
                                .into_iter()
                                .filter(|item| !existing.contains(&item.id)),
                        );
                    });
                } else {
                    replies.update(|items| {
                        items.insert(parent_id, payload.messages);
                    });
                }
                reply_cursors.update(|cursors| {
                    if let Some(cursor) = payload.next_cursor {
                        cursors.insert(parent_id, cursor);
                    } else {
                        cursors.remove(&parent_id);
                    }
                });
            }
            Err(message) => error.set(Some(message)),
        }
        loading_replies.update(|ids| {
            ids.remove(&parent_id);
        });
    });
}

async fn fetch_replies(
    parent_id: i64,
    offset: Option<usize>,
) -> Result<WallMessagesResponse, String> {
    let mut path = format!("/api/messages/{parent_id}/replies");
    if let Some(cursor) = offset {
        path.push_str(&format!("?offset={cursor}"));
    }
    let response = Request::get(&api_url(&path))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(api_error(response).await);
    }
    response
        .json::<WallMessagesResponse>()
        .await
        .map_err(|error| error.to_string())
}

async fn mutate_message_like(
    message_id: i64,
    should_like: bool,
) -> Result<WallLikeResponse, String> {
    let path = api_url(&format!("/api/messages/{message_id}/like"));
    let request = if should_like {
        Request::put(&path)
    } else {
        Request::delete(&path)
    };
    let response = request.send().await.map_err(|error| error.to_string())?;
    if response.status() == 401 {
        start_github_login();
        return Err("GitHub sign-in is required.".to_string());
    }
    if !response.ok() {
        return Err(api_error(response).await);
    }
    response
        .json::<WallLikeResponse>()
        .await
        .map_err(|error| error.to_string())
}

async fn create_message(body: &str, parent_id: Option<i64>) -> Result<WallMessage, String> {
    let request = Request::post(&api_url("/api/messages"))
        .json(&CreateWallMessage { body, parent_id })
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
