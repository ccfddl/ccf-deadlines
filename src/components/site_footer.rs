use leptos::prelude::*;

#[component]
pub fn SiteFooterLinks(use_english: RwSignal<bool>) -> impl IntoView {
    view! {
        <nav class="site-footer-links" aria-label=move || if use_english.get() { "Site information" } else { "网站说明" }>
            <a href="/about.html">{move || if use_english.get() { "About & contact" } else { "关于与联系" }}</a>
            <a href="/guide.html">{move || if use_english.get() { "Guide" } else { "使用说明" }}</a>
            <a href="/privacy.html">{move || if use_english.get() { "Privacy" } else { "隐私政策" }}</a>
        </nav>
    }
}
