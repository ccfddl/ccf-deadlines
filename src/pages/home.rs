use crate::components::conference_controls::{conference_theme, use_language_preference};
use crate::components::favorites::FavoritesContext;
use crate::components::header::Header;
use crate::components::showtable::ShowTable;
use crate::components::tabular_view::TabularView;
use leptos::prelude::*;

use thaw::*;

/// Default Home Page
#[component]
pub fn Home() -> impl IntoView {
    let favorites = FavoritesContext::new();
    provide_context(favorites);
    favorites.load();

    let use_english = use_language_preference();
    let table_view = web_sys::window()
        .and_then(|window| window.location().search().ok())
        .is_some_and(|query| {
            query
                .trim_start_matches('?')
                .split('&')
                .any(|part| part == "view=table")
        });
    let show_favorites_timeline = RwSignal::new(false);
    let show_batch_subscription = RwSignal::new(false);
    let show_email_reminders = RwSignal::new(
        web_sys::window()
            .and_then(|browser| browser.location().search().ok())
            .is_some_and(|query| query.contains("email_reminders=1")),
    );

    view! {
        <ConfigProvider theme=conference_theme()>
            <div class="home">
                <Header use_english show_favorites_timeline show_batch_subscription show_email_reminders table_view />
                {if table_view {
                    view! { <TabularView use_english /> }.into_any()
                } else {
                    view! { <ShowTable use_english show_favorites_timeline show_batch_subscription show_email_reminders /> }.into_any()
                }}
            </div>
        </ConfigProvider>
    }
}
