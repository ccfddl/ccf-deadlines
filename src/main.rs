use ccfddl::{App, DirectoryControls};
use leptos::prelude::*;
use wasm_bindgen::JsCast;

fn main() {
    #[cfg(debug_assertions)]
    {
        _ = console_log::init_with_level(log::Level::Debug);
    }
    console_error_panic_hook::set_once();

    if let Some(root) = web_sys::window()
        .and_then(|window| window.document())
        .and_then(|document| document.get_element_by_id("directory-controls-root"))
    {
        // Replace only the controls; keep the generated conference content intact.
        root.set_inner_html("");
        leptos::mount::mount_to(root.unchecked_into(), || view! { <DirectoryControls /> }).forget();
        return;
    }

    mount_to_body(|| {
        view! { <App /> }
    });

    if let Some(initial_loading) = web_sys::window()
        .and_then(|window| window.document())
        .and_then(|document| document.get_element_by_id("initial-loading"))
    {
        initial_loading.remove();
    }
}
