use leptos::{ev, html, leptos_dom::helpers::window_event_listener, portal::Portal, prelude::*};
use wasm_bindgen::JsCast;
use web_sys::window;

/// A single-choice field using the same menu styles as the homepage timezone picker.
#[component]
pub fn SelectDropdown(
    id: &'static str,
    label: Signal<&'static str>,
    selected: RwSignal<String>,
    options: Signal<Vec<(String, String)>>,
    open_dropdown: RwSignal<Option<&'static str>>,
) -> impl IntoView {
    let options = Memo::new(move |_| options.get());
    let trigger = NodeRef::<html::Button>::new();
    let menu = NodeRef::<html::Div>::new();
    let active = RwSignal::new(0usize);
    let menu_style = RwSignal::new(String::new());
    let is_open = Memo::new(move |_| open_dropdown.get() == Some(id));
    let label_id = StoredValue::new(format!("{id}-label"));
    let menu_id = StoredValue::new(format!("{id}-menu"));
    let selected_label = Memo::new(move |_| {
        let value = selected.get();
        options
            .get()
            .into_iter()
            .find(|(option, _)| *option == value)
            .map(|(_, label)| label)
            .unwrap_or(value)
    });

    let open_menu = move || {
        let Some(button) = trigger.get() else { return };
        let rect = button.get_bounding_client_rect();
        let viewport_height = window()
            .and_then(|browser| browser.inner_height().ok())
            .and_then(|height| height.as_f64())
            .unwrap_or(600.0);
        let items = options.get_untracked();
        let desired_height = (items.len() as f64 * 30.0 + 10.0).min(220.0);
        let below = (viewport_height - rect.bottom() - 8.0).max(0.0);
        let above = (rect.top() - 8.0).max(0.0);
        let open_above = below < desired_height && above > below;
        let height = desired_height.min(if open_above { above } else { below });
        let top = if open_above {
            rect.top() - height - 5.0
        } else {
            rect.bottom() + 5.0
        };
        menu_style.set(format!(
            "top:{top}px;left:{}px;width:{}px;max-height:{height}px;",
            rect.left(),
            rect.width()
        ));
        active.set(
            items
                .iter()
                .position(|(value, _)| *value == selected.get_untracked())
                .unwrap_or(0),
        );
        open_dropdown.set(Some(id));
    };

    let outside = window_event_listener(ev::click, move |event| {
        if !is_open.get_untracked() {
            return;
        }
        let inside = event
            .target()
            .and_then(|target| target.dyn_into::<web_sys::Node>().ok())
            .is_some_and(|target| {
                trigger
                    .get_untracked()
                    .is_some_and(|button| button.contains(Some(&target)))
                    || menu
                        .get_untracked()
                        .is_some_and(|list| list.contains(Some(&target)))
            });
        if !inside {
            open_dropdown.set(None);
        }
    });
    let resize = window_event_listener(ev::resize, move |_| open_dropdown.set(None));
    let scroll = window_event_listener(ev::scroll, move |_| open_dropdown.set(None));
    on_cleanup(move || {
        outside.remove();
        resize.remove();
        scroll.remove();
    });

    Effect::new(move |_| {
        if !is_open.get() {
            return;
        }
        let index = active.get();
        if let Some(list) = menu.get() {
            if let Ok(Some(option)) = list.query_selector(&format!("[data-index='{index}']")) {
                if let Ok(option) = option.dyn_into::<web_sys::HtmlElement>() {
                    list.set_scroll_top(option.offset_top() - list.client_height() / 2);
                }
            }
        }
    });

    let search = StoredValue::new(String::new());
    let last_key = StoredValue::new(0i64);
    let on_keydown = move |event: ev::KeyboardEvent| {
        let key = event.key();
        if key == "Tab" {
            open_dropdown.set(None);
            return;
        }
        if key == "Escape" && is_open.get_untracked() {
            event.prevent_default();
            event.stop_propagation();
            open_dropdown.set(None);
            return;
        }
        let items = options.get_untracked();
        if items.is_empty() {
            return;
        }
        if matches!(key.as_str(), "ArrowDown" | "ArrowUp" | "Home" | "End") {
            event.prevent_default();
            if !is_open.get_untracked() {
                open_menu();
            }
            let index = active.get_untracked();
            active.set(match key.as_str() {
                "Home" => 0,
                "End" => items.len() - 1,
                "ArrowUp" => index.saturating_sub(1),
                _ => (index + 1).min(items.len() - 1),
            });
        } else if matches!(key.as_str(), "Enter" | " ") && is_open.get_untracked() {
            event.prevent_default();
            if let Some((value, _)) = items.get(active.get_untracked()) {
                selected.set(value.clone());
            }
            open_dropdown.set(None);
        } else if key.chars().count() == 1
            && !event.ctrl_key()
            && !event.alt_key()
            && !event.meta_key()
        {
            event.prevent_default();
            if !is_open.get_untracked() {
                open_menu();
            }
            let now = chrono::Utc::now().timestamp_millis();
            if now - last_key.get_value() > 1000 {
                search.set_value(String::new());
            }
            last_key.set_value(now);
            search.update_value(|text| text.push_str(&key.to_lowercase()));
            let prefix = search.get_value();
            if let Some(index) = items
                .iter()
                .position(|(_, text)| text.to_lowercase().starts_with(&prefix))
            {
                active.set(index);
            }
        }
    };

    view! {
        <div class="email-reminder-field">
            <span id=label_id.get_value()>{move || label.get()}</span>
            <button
                type="button" id=id node_ref=trigger
                class="toolbar-timezone-trigger email-reminder-dropdown-trigger"
                role="combobox" aria-haspopup="listbox"
                aria-labelledby=label_id.get_value() aria-controls=menu_id.get_value()
                aria-expanded=move || is_open.get()
                aria-activedescendant=move || is_open.get().then(|| format!("{id}-option-{}", active.get()))
                title=move || selected_label.get()
                on:click=move |_| {
                    if is_open.get_untracked() { open_dropdown.set(None); } else { open_menu(); }
                }
                on:blur=move |_| open_dropdown.set(None)
                on:keydown=on_keydown
            >
                <span class="toolbar-timezone-label">{move || selected_label.get()}</span>
                <span class="toolbar-timezone-arrow" aria-hidden="true">"⌄"</span>
            </button>
            <Show when=move || is_open.get()>
                <Portal>
                    <div
                        id=menu_id.get_value() node_ref=menu
                        class="toolbar-timezone-menu email-reminder-dropdown-menu"
                        role="listbox" aria-labelledby=label_id.get_value()
                        style=move || menu_style.get()
                    >
                        {move || options.get().into_iter().enumerate().map(|(index, (value, text))| {
                            let selection = value.clone();
                            view! {
                                <div
                                    id=format!("{id}-option-{index}")
                                    class="toolbar-timezone-option" role="option"
                                    aria-selected=move || selected.get() == selection
                                    data-index=index data-active=move || active.get() == index
                                    title=text.clone()
                                    on:mousedown=move |event| event.prevent_default()
                                    on:click=move |_| { selected.set(value.clone()); open_dropdown.set(None); }
                                >{text.clone()}</div>
                            }
                        }).collect_view()}
                    </div>
                </Portal>
            </Show>
        </div>
    }
}
