use gloo_net::http::Request;
use leptos::prelude::*;
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use wasm_bindgen_futures::spawn_local;
use web_sys::window;

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct GithubUser {
    pub login: String,
    pub avatar_url: String,
    pub profile_url: String,
}

#[derive(Clone, Debug, Deserialize)]
struct FavoritesBootstrap {
    user: Option<GithubUser>,
    counts: HashMap<String, u64>,
    starred: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
struct StarMutation {
    count: u64,
    starred: bool,
}

#[derive(Clone, Copy)]
pub struct FavoritesContext {
    pub user: RwSignal<Option<GithubUser>>,
    pub loaded: RwSignal<bool>,
    pub counts: RwSignal<HashMap<String, u64>>,
    pub starred: RwSignal<HashSet<String>>,
    pending: RwSignal<HashSet<String>>,
    pub error: RwSignal<Option<String>>,
}

impl FavoritesContext {
    pub fn new() -> Self {
        Self {
            user: RwSignal::new(None),
            loaded: RwSignal::new(false),
            counts: RwSignal::new(HashMap::new()),
            starred: RwSignal::new(HashSet::new()),
            pending: RwSignal::new(HashSet::new()),
            error: RwSignal::new(None),
        }
    }

    pub fn load(self) {
        spawn_local(async move {
            match fetch_bootstrap().await {
                Ok(snapshot) => {
                    self.user.set(snapshot.user);
                    self.counts.set(snapshot.counts);
                    self.starred.set(snapshot.starred.into_iter().collect());
                    self.error.set(None);
                }
                Err(error) => self.error.set(Some(error)),
            }
            self.loaded.set(true);
        });
    }

    pub fn count(self, conference_key: &str) -> u64 {
        self.counts
            .with(|counts| counts.get(conference_key).copied().unwrap_or_default())
    }

    pub fn is_pending(self, conference_key: &str) -> bool {
        self.pending
            .with(|pending| pending.contains(conference_key))
    }

    pub fn toggle(self, conference_key: String) {
        if self.user.get_untracked().is_none() {
            start_github_login();
            return;
        }
        if self.is_pending(&conference_key) {
            return;
        }

        let was_starred = self
            .starred
            .with_untracked(|starred| starred.contains(&conference_key));
        let previous_count = self.count(conference_key.as_str());
        let should_star = !was_starred;

        self.pending.update(|pending| {
            pending.insert(conference_key.clone());
        });
        self.starred.update(|starred| {
            if should_star {
                starred.insert(conference_key.clone());
            } else {
                starred.remove(&conference_key);
            }
        });
        self.counts.update(|counts| {
            counts.insert(
                conference_key.clone(),
                if should_star {
                    previous_count.saturating_add(1)
                } else {
                    previous_count.saturating_sub(1)
                },
            );
        });

        spawn_local(async move {
            match mutate_star(&conference_key, should_star).await {
                Ok(result) => {
                    self.starred.update(|starred| {
                        if result.starred {
                            starred.insert(conference_key.clone());
                        } else {
                            starred.remove(&conference_key);
                        }
                    });
                    self.counts
                        .update(|counts| _ = counts.insert(conference_key.clone(), result.count));
                    self.error.set(None);
                }
                Err(error) => {
                    self.starred.update(|starred| {
                        if was_starred {
                            starred.insert(conference_key.clone());
                        } else {
                            starred.remove(&conference_key);
                        }
                    });
                    self.counts
                        .update(|counts| _ = counts.insert(conference_key.clone(), previous_count));
                    self.error.set(Some(error));
                }
            }
            self.pending.update(|pending| {
                pending.remove(&conference_key);
            });
        });
    }

    pub fn logout(self) {
        spawn_local(async move {
            let response = Request::post(&api_url("/api/auth/logout")).send().await;
            if response.is_ok_and(|response| response.ok()) {
                self.user.set(None);
                self.starred.set(HashSet::new());
                self.error.set(None);
            } else {
                self.error
                    .set(Some("Unable to sign out. Please try again.".to_string()));
            }
        });
    }
}

pub fn start_github_login() {
    let return_to = window()
        .and_then(|browser| {
            let location = browser.location();
            let path = location.pathname().ok()?;
            let search = location.search().unwrap_or_default();
            let hash = location.hash().unwrap_or_default();
            Some(format!("{path}{search}{hash}"))
        })
        .unwrap_or_else(|| "/".to_string());
    let login_url = format!(
        "{}?return_to={}",
        api_url("/api/auth/github"),
        urlencoding::encode(&return_to),
    );
    if let Some(browser) = window() {
        let _ = browser.location().set_href(&login_url);
    }
}

async fn fetch_bootstrap() -> Result<FavoritesBootstrap, String> {
    let response = Request::get(&api_url("/api/bootstrap"))
        .send()
        .await
        .map_err(|error| error.to_string())?;
    if !response.ok() {
        return Err(format!("Favorites API returned HTTP {}", response.status()));
    }
    response.json().await.map_err(|error| error.to_string())
}

async fn mutate_star(conference_key: &str, should_star: bool) -> Result<StarMutation, String> {
    let url = api_url(&format!(
        "/api/stars/{}",
        urlencoding::encode(conference_key),
    ));
    let response = if should_star {
        Request::put(&url).send().await
    } else {
        Request::delete(&url).send().await
    }
    .map_err(|error| error.to_string())?;

    if response.status() == 401 {
        start_github_login();
        return Err("GitHub sign-in is required.".to_string());
    }
    if !response.ok() {
        return Err(format!("Favorites API returned HTTP {}", response.status()));
    }
    response.json().await.map_err(|error| error.to_string())
}

fn api_url(path: &str) -> String {
    let base = option_env!("CCFDDL_API_BASE")
        .unwrap_or_default()
        .trim_end_matches('/');
    format!("{base}{path}")
}
