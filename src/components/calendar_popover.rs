use leptos::prelude::*;
use thaw::*;
use chrono::{DateTime, Utc};

#[component]
pub fn CalendarPopover(
    google_calendar_url: Option<String>,
    icloud_calendar_url: Option<String>,
) -> impl IntoView {
    let show_popover = RwSignal::new(false);

    view! {
        <div
            class="calendar-popover-container"
            on:mouseenter=move |_| show_popover.set(true)
            on:mouseleave=move |_| show_popover.set(false)
        >
            <Icon icon=icondata::VsCalendar style="margin-left: 5px; cursor: pointer" />

            {move || {
                let google_calendar_url_clone = google_calendar_url.clone();
                let icloud_calendar_url_clone = icloud_calendar_url.clone();

                if show_popover.get() {
                    view! {
                        <div class="calendar-popover">
                            <div>
                                <div style="margin-bottom: 8px; font-weight: 500; color: #666; font-size: 12px;">
                                    "Add to Calendar:"
                                </div>

                                // Google Calendar
                                <div style="margin-bottom: 8px; display: flex; align-items: center;">
                                    <img
                                        src="//ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_31_2x.png#"
                                        alt="Google Calendar"
                                        style="width: 16px; height: 16px; vertical-align: middle; margin-right: 8px;"
                                    />
                                    <a
                                        href=google_calendar_url_clone
                                        target="_blank"
                                        style="text-decoration: none; border-bottom: 1px solid #ccc; color: inherit;"
                                    >
                                        "Google Calendar"
                                    </a>
                                </div>

                                // iCloud Calendar
                                <div style="display: flex; align-items: center;">
                                    <img
                                        src="https://help.apple.com/assets/61526E8E1494760B754BD308/61526E8F1494760B754BD30F/zh_CN/2162f7d3de310d2b3503c0bbebdc3d56.png"
                                        alt="iCloud Calendar"
                                        style="width: 16px; height: 16px; vertical-align: middle; margin-right: 8px;"
                                    />
                                    <a
                                        href=icloud_calendar_url_clone
                                        style="text-decoration: none; border-bottom: 1px solid #ccc; color: inherit;"
                                    >
                                        "iCloud Calendar"
                                    </a>
                                </div>
                            </div>

                            // 箭头（桌面端右侧，移动端左侧）
                            <div class="calendar-popover-arrow"></div>
                        </div>

                        // CSS 样式
                        <style>
                            ".calendar-popover-container {
                                position: relative;
                                display: inline-block;
                            }

                            .calendar-popover {
                                position: absolute;
                                top: 50%;
                                left: calc(100% + 8px);
                                transform: translateY(-50%);
                                background: rgba(255, 255, 255, 0.95);
                                backdrop-filter: blur(20px);
                                border: 1px solid rgba(0, 0, 0, 0.1);
                                color: #333;
                                padding: 16px;
                                border-radius: 12px;
                                font-size: 13px;
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                z-index: 1000;
                                min-width: 140px;
                                max-width: 140px;
                                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), 0 2px 8px rgba(0, 0, 0, 0.1);
                                line-height: 1.4;
                                animation: popover-appear 0.15s ease-out;
                            }

                            .calendar-popover-arrow {
                                position: absolute;
                                right: 100%;
                                top: 50%;
                                transform: translateY(-50%);
                                width: 0;
                                height: 0;
                                border-top: 8px solid transparent;
                                border-bottom: 8px solid transparent;
                                border-right: 8px solid rgba(255, 255, 255, 0.95);
                                filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.05));
                            }

                            /* 移动端样式 */
                            @media (max-width: 768px) {
                                .calendar-popover {
                                    left: auto;
                                    right: calc(100% + 8px);
                                }

                                .calendar-popover-arrow {
                                    right: auto;
                                    left: 100%;
                                    border-right: none;
                                    border-left: 8px solid rgba(255, 255, 255, 0.95);
                                }
                            }

                            @keyframes popover-appear {
                                from {
                                    opacity: 0;
                                    transform: translateY(-50%) translateX(-4px) scale(0.95);
                                }
                                to {
                                    opacity: 1;
                                    transform: translateY(-50%) translateX(0) scale(1);
                                }
                            }
                            "
                        </style>
                    }.into_any()
                } else {
                    view! { <div></div> }.into_any()
                }
            }}
        </div>
    }
}
