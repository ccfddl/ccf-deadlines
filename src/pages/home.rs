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

    let storage = web_sys::window().and_then(|window| window.local_storage().ok().flatten());
    let stored_language = storage
        .as_ref()
        .and_then(|storage| storage.get_item("language_preference").ok().flatten())
        .and_then(|value| match value.as_str() {
            "en" => Some(true),
            "zh" => Some(false),
            _ => None,
        })
        .or_else(|| {
            storage
                .as_ref()
                .and_then(|storage| storage.get_item("use_english").ok().flatten())
                .filter(|value| value == "true")
                .map(|_| true)
        });
    let browser_language = web_sys::window()
        .map(|window| window.navigator().language())
        .flatten()
        .unwrap_or_default();
    let use_english = RwSignal::new(
        stored_language.unwrap_or_else(|| !browser_language.to_ascii_lowercase().starts_with("zh")),
    );
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
    Effect::new(move |_| {
        if let Some(root) = web_sys::window()
            .and_then(|window| window.document())
            .and_then(|document| document.document_element())
        {
            let _ = root.set_attribute("lang", if use_english.get() { "en" } else { "zh-CN" });
        }
    });
    Effect::new(move |previous: Option<bool>| {
        let english = use_english.get();
        if previous.is_some() {
            if let Some(storage) =
                web_sys::window().and_then(|window| window.local_storage().ok().flatten())
            {
                let _ = storage.set_item("language_preference", if english { "en" } else { "zh" });
            }
        }
        english
    });
    // theme
    let theme = RwSignal::new(Theme::light());
    theme.update(|theme| {
        theme
            .color
            .set_color_compound_brand_background("#409eff".to_string());
        theme
            .color
            .set_color_compound_brand_background_hover("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible("#dcdfe6".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible_pressed("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_accessible_hover("#409eff".to_string());
        theme
            .color
            .set_color_neutral_stroke_2("#ebeef5".to_string());
    });

    view! {
        <ConfigProvider theme>
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
