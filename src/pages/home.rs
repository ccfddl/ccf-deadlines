use crate::components::header::Header;
use crate::components::showtable::ShowTable;
use leptos::prelude::*;

use thaw::*;

/// Default Home Page
#[component]
pub fn Home() -> impl IntoView {
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
    Effect::new(move |_| {
        if let Some(root) = web_sys::window()
            .and_then(|window| window.document())
            .and_then(|document| document.document_element())
        {
            let _ = root.set_attribute("lang", if use_english.get() { "en" } else { "zh-CN" });
        }
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
                <Header />
                <ShowTable use_english />
            </div>
        </ConfigProvider>
    }
}
