use ccfddl::App;
use leptos::prelude::*;

fn main() {
    // set up logging
    _ = console_log::init_with_level(log::Level::Debug);
    console_error_panic_hook::set_once();

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
