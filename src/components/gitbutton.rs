use leptos::prelude::*;

#[component]
pub fn GitButton() -> impl IntoView {
    view! {
        <iframe
            src="https://ghbtns.com/github-btn.html?user=ccfddl&repo=ccf-deadlines&type=star&count=true&size=large"
            width="170"
            height="30"
            title="GitHub"
            class="github-iframe"
        />
    }
}
