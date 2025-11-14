use leptos::prelude::*;
use crate::components::header::Header;
use crate::components::showtable::ShowTable;

use thaw::*;


/// Default Home Page
#[component]
pub fn Home() -> impl IntoView {
    // theme
    let theme = RwSignal::new(Theme::light());
    theme.update(|theme| {
        theme.color.set_color_compound_brand_background("#409eff".to_string());
        theme.color.set_color_compound_brand_background_hover("#409eff".to_string());
        theme.color.set_color_neutral_stroke_accessible("#dcdfe6".to_string());
        theme.color.set_color_neutral_stroke_accessible_pressed("#409eff".to_string());
        theme.color.set_color_neutral_stroke_accessible_hover("#409eff".to_string());
        theme.color.set_color_neutral_stroke_2("#ebeef5".to_string());
    });

    view! {
        <ConfigProvider theme>
            <div class="home">
                <Header />
                <ShowTable />
            </div>
        </ConfigProvider>
    }
}
