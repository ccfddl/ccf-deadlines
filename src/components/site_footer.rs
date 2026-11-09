use leptos::prelude::*;

#[component]
pub fn SiteFooterLinks(use_english: RwSignal<bool>) -> impl IntoView {
    view! {
        <nav class="site-footer-links" aria-label=move || if use_english.get() { "Site information" } else { "网站说明" }>
            <a href="/privacy.html" data-privacy-modal="">{move || if use_english.get() { "Privacy Policy" } else { "隐私政策" }}</a>
        </nav>
    }
}
