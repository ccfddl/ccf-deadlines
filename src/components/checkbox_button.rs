use leptos::*;
use leptos::prelude::*;
use std::collections::HashSet;

#[component]
pub fn CheckboxButton(
    label: String,
    value: String,
    rank_list: RwSignal<HashSet<String>>,
    #[prop(optional)] is_first: bool,
    #[prop(optional)] is_last: bool,
) -> impl IntoView {
    let value_clone = value.clone();
    let is_checked = Memo::new(move |_| {
        rank_list.get().contains(&value_clone)
    });

    let handle_change = move |_ev| {
        let value_for_update = value.clone();
        rank_list.update(|set| {
            if set.contains(&value_for_update) {
                set.remove(&value_for_update);
            } else {
                set.insert(value_for_update);
            }
        });
    };

    view! {
        <label class=move || {
            let mut classes = vec!["checkbox-btn"];
            if is_checked.get() {
                classes.push("checked");
            }
            if is_first {
                classes.push("first");
            }
            if is_last {
                classes.push("last");
            }
            classes.join(" ")
        }>
            <input type="checkbox" checked=move || is_checked.get() on:change=handle_change />
            <span>{label}</span>
        </label>
        <style>
            {r#"
            .checkbox-btn {
              display: inline-flex;
              align-items: center;
              padding: 2px 8px;
              border: 1px solid #d9d9d9;
              background: #fff;
              cursor: pointer;
              user-select: none;
              margin: 0;
              font-size: 12px;
              font-weight: 500;
              transition: all 0.2s;
              position: relative;
              border-right: none;
              color: #666;
            }

            .checkbox-btn.first {
              border-top-left-radius: 6px;
              border-bottom-left-radius: 6px;
            }

            .checkbox-btn.last {
              border-top-right-radius: 6px;
              border-bottom-right-radius: 6px;
              border-right: 1px solid #d9d9d9;
            }

            .checkbox-btn input {
              display: none;
            }

            .checkbox-btn.checked {
              background: #1890ff;
              border-color: #1890ff;
              color: #fff;
              z-index: 2;
            }

            .checkbox-btn.checked:not(.last) {
              box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.3);
            }

            .checkbox-btn.checked.last {
              border-right: 1px solid #1890ff;
            }

            .checkbox-btn:hover {
              z-index: 1;
            }

            .checkbox-btn:hover:not(.checked) {
              color: #1890ff;
            }

            .checkbox-btn.disabled {
              color: rgba(0, 0, 0, 0.25);
              background: #f5f5f5;
              border-color: #d9d9d9;
              cursor: not-allowed;
            }
            "#}
        </style>
    }
}

#[component]
pub fn CheckboxButtonGroup(
    rank_list: RwSignal<HashSet<String>>,
) -> impl IntoView {

    view! {
        <div>
            <div class="checkbox-group" style="display: inline-flex;">
                <CheckboxButton
                    label="CCF A".to_string()
                    value="A".to_string()
                    rank_list=rank_list
                    is_first=true
                />
                <CheckboxButton
                    label="CCF B".to_string()
                    value="B".to_string()
                    rank_list=rank_list
                />
                <CheckboxButton
                    label="CCF C".to_string()
                    value="C".to_string()
                    rank_list=rank_list
                />
                <CheckboxButton
                    label="Non-CCF".to_string()
                    value="N".to_string()
                    rank_list=rank_list
                    is_last=true
                />
            </div>
        </div>
    }
}
