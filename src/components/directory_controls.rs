//! A controls island: conference links remain static and crawlable.
use crate::components::conference_controls::*;
use leptos::prelude::*;
use thaw::ConfigProvider;
use wasm_bindgen::prelude::*;

#[wasm_bindgen(inline_js = r#"
export function updateDirectoryFilters(json, english) {
    const state = JSON.parse(json);
    const needle = state.q.trim().toLocaleLowerCase();
    let matches = 0;
    for (const section of document.querySelectorAll('.directory-section')) {
        let count = 0;
        for (const row of section.querySelectorAll('li[data-category]')) {
            const visible = (!state.categories.length || state.categories.includes(row.dataset.category))
                && ['ccf', 'core', 'thcpl'].every(key => !state[key].length || state[key].includes(row.dataset[key]))
                && (!needle || row.dataset.search.toLocaleLowerCase().includes(needle));
            row.hidden = !visible;
            if (visible) { matches++; count++; }
        }
        section.hidden = count === 0;
    }
    const empty = document.getElementById('directory-empty');
    if (empty) {
        empty.hidden = matches !== 0;
        empty.textContent = english ? 'No matching conferences.' : '没有匹配的会议。';
    }
    document.querySelectorAll('[data-en][data-zh]').forEach(node => {
        node.textContent = english ? node.dataset.en : node.dataset.zh;
    });
    const query = new URLSearchParams();
    for (const key of ['categories', 'ccf', 'core', 'thcpl']) {
        if (state[key].length) query.set(key, state[key].sort().join(','));
    }
    if (!query.size) query.set('filters', 'all');
    if (state.q) query.set('q', state.q);
    query.set('tz', state.tz);
    history.replaceState(null, '', location.pathname + '?' + query + location.hash);
}
"#)]
extern "C" {
    #[wasm_bindgen(js_name = updateDirectoryFilters)]
    fn update_directory_filters(json: &str, english: bool);
}

#[component]
pub fn DirectoryControls() -> impl IntoView {
    let use_english = use_language_preference();
    let ConferenceFilterState {
        category_list,
        selected,
        rank_list,
        core_rank_list,
        thcpl_rank_list,
        search,
        browser_timezone,
        selected_timezone,
    } = ConferenceFilterState::new();
    let open_dropdown = RwSignal::new(None::<String>);
    persist_filters(
        selected,
        rank_list,
        core_rank_list,
        thcpl_rank_list,
        search,
        selected_timezone,
    );
    Effect::new(move |_| {
        let state = serde_json::json!({
            "categories": selected.get(), "ccf": rank_list.get(),
            "core": core_rank_list.get(), "thcpl": thcpl_rank_list.get(),
            "q": search.get(), "tz": selected_timezone.get(),
        });
        update_directory_filters(&state.to_string(), use_english.get());
    });
    view! {
        <ConfigProvider theme=conference_theme() class="conference-controls-provider">
            <ConferenceControls use_english categories=category_list selected search
                rank_list core_rank_list thcpl_rank_list selected_timezone browser_timezone open_dropdown>
                <ToolbarClock slot><LiveClock selected_timezone /></ToolbarClock>
            </ConferenceControls>
            <ConferenceDivider />
        </ConfigProvider>
    }
}
