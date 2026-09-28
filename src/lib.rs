use leptos::prelude::*;

// Modules
mod components;
mod pages;

// Top-Level pages
use crate::pages::home::Home;

#[component]
pub fn App() -> impl IntoView {
    view! { <Home /> }
}
