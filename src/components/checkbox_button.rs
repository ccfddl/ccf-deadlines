use leptos::prelude::*;
use std::collections::HashSet;

const NON_RANK_VALUE: &str = "N";

#[derive(Clone, PartialEq, Eq)]
pub struct FilterDropdownOption {
    pub value: &'static str,
    pub label: &'static str,
    pub summary_label: &'static str,
}

pub fn normalize_rank_filter_selection(selected_values: &mut HashSet<String>) {
    if selected_values.contains(NON_RANK_VALUE) && selected_values.len() > 1 {
        selected_values.remove(NON_RANK_VALUE);
    }
}

pub fn ccf_filter_options() -> Vec<FilterDropdownOption> {
    vec![
        FilterDropdownOption {
            value: "A",
            label: "CCF A",
            summary_label: "A",
        },
        FilterDropdownOption {
            value: "B",
            label: "CCF B",
            summary_label: "B",
        },
        FilterDropdownOption {
            value: "C",
            label: "CCF C",
            summary_label: "C",
        },
        FilterDropdownOption {
            value: "N",
            label: "Non-CCF",
            summary_label: "Non",
        },
    ]
}

pub fn core_filter_options() -> Vec<FilterDropdownOption> {
    vec![
        FilterDropdownOption {
            value: "A*",
            label: "CORE A*",
            summary_label: "A*",
        },
        FilterDropdownOption {
            value: "A",
            label: "CORE A",
            summary_label: "A",
        },
        FilterDropdownOption {
            value: "B",
            label: "CORE B",
            summary_label: "B",
        },
        FilterDropdownOption {
            value: "C",
            label: "CORE C",
            summary_label: "C",
        },
        FilterDropdownOption {
            value: "N",
            label: "Non-CORE",
            summary_label: "Non",
        },
    ]
}

pub fn thcpl_filter_options() -> Vec<FilterDropdownOption> {
    vec![
        FilterDropdownOption {
            value: "A",
            label: "THCPL A",
            summary_label: "A",
        },
        FilterDropdownOption {
            value: "B",
            label: "THCPL B",
            summary_label: "B",
        },
        FilterDropdownOption {
            value: "N",
            label: "Non-THCPL",
            summary_label: "Non",
        },
    ]
}

#[component]
pub fn MultiSelectDropdown(
    dropdown_id: String,
    title: String,
    options: Vec<FilterDropdownOption>,
    selected_values: RwSignal<HashSet<String>>,
    use_english: RwSignal<bool>,
    panel_width: String,
    open_dropdown: RwSignal<Option<String>>,
) -> impl IntoView {
    let dropdown_id_for_open = dropdown_id.clone();
    let is_open =
        Memo::new(move |_| open_dropdown.get().as_deref() == Some(dropdown_id_for_open.as_str()));
    let options_for_summary = options.clone();
    let title_for_summary = title.clone();
    let title_for_panel = title.clone();
    let options_for_render = StoredValue::new(options.clone());
    let summary = Memo::new(move |_| {
        let selected = selected_values.get();
        let selected_labels: Vec<&str> = options_for_summary
            .iter()
            .filter(|option| selected.contains(option.value))
            .map(|option| option.summary_label)
            .collect();

        match selected_labels.len() {
            0 => title_for_summary.clone(),
            1 => format!("{title_for_summary} {}", selected_labels[0]),
            2 => format!(
                "{title_for_summary} {},{}",
                selected_labels[0], selected_labels[1]
            ),
            _ => format!(
                "{title_for_summary} {},{}+{}",
                selected_labels[0],
                selected_labels[1],
                selected_labels.len() - 2
            ),
        }
    });

    let has_selection = Memo::new(move |_| !selected_values.get().is_empty());
    let clear_label = Memo::new(move |_| {
        if use_english.get() {
            "Clear".to_string()
        } else {
            "清空".to_string()
        }
    });
    let dropdown_id_for_toggle = dropdown_id.clone();

    view! {
        <div class="filter-dropdown" style=format!("--filter-panel-width: {panel_width};")>
            <button
                type="button"
                class=move || {
                if has_selection.get() {
                        if is_open.get() {
                            "filter-dropdown-trigger active open"
                        } else {
                            "filter-dropdown-trigger active"
                        }
                } else {
                        if is_open.get() {
                            "filter-dropdown-trigger open"
                        } else {
                            "filter-dropdown-trigger"
                        }
                    }
                }
                on:click=move |_| {
                    if is_open.get_untracked() {
                        open_dropdown.set(None);
                    } else {
                        open_dropdown.set(Some(dropdown_id_for_toggle.clone()));
                    }
                }
            >
                <span class="filter-dropdown-trigger-text">{move || summary.get()}</span>
                <span class="filter-dropdown-trigger-icon">"▾"</span>
            </button>

            <Show when=move || is_open.get()>
                <div class="filter-dropdown-panel">
                    <div class="filter-dropdown-panel-header">
                        <span>{title_for_panel.clone()}</span>
                        <button
                            type="button"
                            class="filter-dropdown-clear"
                            on:click=move |_| {
                                selected_values.set(HashSet::new());
                            }
                            disabled=move || !has_selection.get()
                        >
                            {move || clear_label.get()}
                        </button>
                    </div>

                    <div class="filter-dropdown-options">
                        {move || {
                            options_for_render
                                .get_value()
                                .into_iter()
                                .map(|option| {
                                    let value = option.value.to_string();
                                    let label = option.label.to_string();
                                    let value_for_checked = value.clone();
                                    let value_for_update = value.clone();

                                    view! {
                                        <label class="filter-dropdown-option">
                                            <input
                                                type="checkbox"
                                                prop:checked=move || {
                                                    selected_values.get().contains(&value_for_checked)
                                                }
                                                on:change=move |_| {
                                                    selected_values.update(|set| {
                                                        if set.contains(&value_for_update) {
                                                            set.remove(&value_for_update);
                                                        } else {
                                                            if value_for_update == NON_RANK_VALUE {
                                                                set.clear();
                                                            } else {
                                                                set.remove(NON_RANK_VALUE);
                                                            }
                                                            set.insert(value_for_update.clone());
                                                        }
                                                    });
                                                }
                                            />
                                            <span>{label}</span>
                                        </label>
                                    }
                                })
                                .collect_view()
                        }}
                    </div>
                </div>
            </Show>
        </div>

        <style>
            {r#"
            .filter-dropdown {
              position: relative;
            }

            .filter-dropdown-trigger {
              display: inline-flex;
              align-items: center;
              justify-content: space-between;
              gap: 6px;
              min-width: 88px;
              max-width: 132px;
              padding: 5px 8px;
              border: 1px solid #d9d9d9;
              border-radius: 6px;
              background: #fff;
              color: #666;
              cursor: pointer;
              user-select: none;
              text-align: left;
              font-size: 11px;
              font-weight: 500;
              transition: border-color 0.2s, color 0.2s, box-shadow 0.2s;
            }

            .filter-dropdown-trigger:hover,
            .filter-dropdown-trigger.open {
              border-color: #1890ff;
              color: #1890ff;
            }

            .filter-dropdown-trigger.active {
              border-color: #1890ff;
              color: #1890ff;
              background: #f2f8ff;
            }

            .filter-dropdown-trigger-text {
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .filter-dropdown-trigger-icon {
              color: inherit;
              font-size: 10px;
              transition: transform 0.2s;
            }

            .filter-dropdown-trigger.open .filter-dropdown-trigger-icon {
              transform: rotate(180deg);
            }

            .filter-dropdown-panel {
              position: absolute;
              right: 0;
              top: calc(100% + 6px);
              width: var(--filter-panel-width, 220px);
              padding: 8px;
              border: 1px solid #e5e7eb;
              border-radius: 8px;
              background: #fff;
              box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
              z-index: 20;
            }

            .filter-dropdown-panel-header {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 6px;
              margin-bottom: 6px;
              font-size: 11px;
              font-weight: 600;
              color: #475569;
            }

            .filter-dropdown-clear {
              border: none;
              background: transparent;
              color: #1890ff;
              cursor: pointer;
              font-size: 11px;
              padding: 0;
            }

            .filter-dropdown-clear:disabled {
              color: #94a3b8;
              cursor: default;
            }

            .filter-dropdown-options {
              display: flex;
              flex-direction: column;
              gap: 4px;
            }

            .filter-dropdown-option {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 5px 6px;
              border-radius: 6px;
              color: #334155;
              font-size: 12px;
              cursor: pointer;
            }

            .filter-dropdown-option:hover {
              background: #f8fafc;
            }

            .filter-dropdown-option input {
              margin: 0;
            }
            "#}
        </style>
    }
}
