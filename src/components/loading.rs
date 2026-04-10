use leptos::prelude::*;

#[component]
pub fn LoadingSkeleton() -> impl IntoView {
    view! {
        <div class="skeleton-container">
            <div class="skeleton-header">
                <div class="skeleton-title"></div>
                <div class="skeleton-subtitle"></div>
            </div>

            <div class="skeleton-filters">
                <div class="skeleton-checkbox-group">
                    <div class="skeleton-checkbox"></div>
                    <div class="skeleton-checkbox"></div>
                    <div class="skeleton-checkbox"></div>
                    <div class="skeleton-checkbox"></div>
                </div>
            </div>

            <div class="skeleton-search">
                <div class="skeleton-search-input"></div>
            </div>

            <div class="skeleton-table">
                <For
                    each=move || 0..5
                    key=|i| *i
                    children=move |_| {
                        view! {
                            <div class="skeleton-row">
                                <div class="skeleton-cell main">
                                    <div class="skeleton-line title"></div>
                                    <div class="skeleton-line subtitle"></div>
                                    <div class="skeleton-line subtitle"></div>
                                    <div class="skeleton-tags">
                                        <div class="skeleton-tag"></div>
                                        <div class="skeleton-tag"></div>
                                    </div>
                                </div>
                                <div class="skeleton-cell right">
                                    <div class="skeleton-countdown"></div>
                                    <div class="skeleton-line small"></div>
                                    <div class="skeleton-line small"></div>
                                </div>
                            </div>
                        }
                    }
                />
            </div>
        </div>
    }
}
