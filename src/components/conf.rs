use chrono::prelude::*;
use gloo_net::http::Request;
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use wasm_bindgen::{JsCast, closure::Closure};
use web_sys::{AbortController, RequestCache};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conference {
    #[serde(default)]
    pub conference_key: Option<String>,
    pub title: String,
    pub description: String,
    pub sub: String,
    pub rank: Rank,
    pub dblp: String,
    pub confs: Vec<ConferenceYear>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rank {
    pub ccf: String,
    pub core: Option<String>,
    pub thcpl: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConferenceYear {
    pub year: i32,
    pub id: String,
    pub link: String,
    pub timeline: Vec<Timeline>,
    pub timezone: String,
    pub date: String,
    #[serde(default)]
    pub opening: Option<String>,
    pub place: String,
}

#[derive(Debug, Deserialize)]
pub struct ConfAccRate {
    #[serde(default)]
    pub conference_key: Option<String>,
    pub title: String,
    pub accept_rates: Vec<AccYear>,
}

#[derive(Debug, Deserialize)]
pub struct AccYear {
    pub year: i32,
    #[serde(rename = "str", alias = "srt")]
    pub label: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Timeline {
    pub abstract_deadline: Option<String>,
    pub deadline: String,
    pub rebuttal_deadline: Option<String>,
    pub decision_deadline: Option<String>,
    pub comment: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Category {
    pub name: String,
    pub name_en: String,
    pub sub: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct TimePoint {
    pub timepoint: DateTime<FixedOffset>,
    pub r#type: i32,
    pub round: usize,
    #[serde(default)]
    pub comment: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct ConfItem {
    #[serde(default)]
    pub conference_key: Option<String>,
    pub title: String,
    pub description: String,
    pub sub: String,
    pub rank: String,
    pub corerank: Option<String>,
    pub thcplrank: Option<String>,
    pub displayrank: String,
    pub dblp: String,
    pub year: i32,
    pub id: String,
    pub link: String,
    pub abstract_deadline: Option<String>,
    pub deadline: String,
    pub deadline_type: i32,
    pub comment: Option<String>,
    pub timezone: String,
    pub date: String,
    pub place: String,
    pub status: String, // "RUN", "FIN", "TBD"
    pub is_like: bool,
    pub remain: u64,
    pub subname: String,
    pub subname_en: String,
    pub acc_str: Option<String>,
    pub ddls: Vec<TimePoint>,
    #[serde(default)]
    pub opening: Option<TimePoint>,
    pub estimated_deadlines: Vec<EstimatedDeadline>,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct EstimatedDeadline {
    pub deadline: String,
    pub is_abstract: bool,
    pub source_year: i32,
}

#[derive(Debug, Deserialize)]
pub struct InitialConferences {
    pub conferences: Vec<Conference>,
    pub archive: Option<String>,
}

pub async fn fetch_initial_conf(
    base_url: &str,
) -> Result<InitialConferences, Box<dyn std::error::Error>> {
    let url = format!("{base_url}/conference/initial.json");
    match fetch_json_with_cache_recovery(&url).await {
        Ok(data) => Ok(data),
        Err(_) => Ok(InitialConferences {
            conferences: fetch_json_with_cache_recovery(&format!(
                "{base_url}/conference/allconf.json"
            ))
            .await?,
            archive: None,
        }),
    }
}

pub async fn fetch_all_conf(base_url: &str) -> Result<Vec<Conference>, Box<dyn std::error::Error>> {
    fetch_json_with_cache_recovery(&format!("{base_url}/conference/allconf.json")).await
}

pub async fn fetch_archive_conf(
    base_url: &str,
    archive: &str,
) -> Result<Vec<Conference>, Box<dyn std::error::Error>> {
    if !archive.starts_with("parts/history-")
        || !archive.ends_with(".json")
        || archive.contains("..")
        || archive.contains('\\')
        || archive.contains('?')
        || archive.contains('#')
    {
        return Err(std::io::Error::other("invalid conference archive path").into());
    }
    match fetch_json_with_cache_recovery(&format!("{base_url}/conference/{archive}")).await {
        Ok(data) => Ok(data),
        Err(_) => {
            fetch_json_with_cache_recovery(&format!("{base_url}/conference/allconf.json")).await
        }
    }
}

pub fn merge_conferences(current: &mut Vec<Conference>, additional: Vec<Conference>) {
    for conference in additional {
        if let Some(existing) = current
            .iter_mut()
            .find(|item| item.title == conference.title && item.sub == conference.sub)
        {
            for edition in conference.confs {
                if !existing.confs.iter().any(|item| item.id == edition.id) {
                    existing.confs.push(edition);
                }
            }
            existing.confs.sort_by_key(|edition| edition.year);
        } else {
            current.push(conference);
        }
    }
}

pub fn acceptance_bucket(title: &str) -> u32 {
    title.as_bytes().iter().fold(2166136261u32, |hash, byte| {
        (hash ^ u32::from(*byte)).wrapping_mul(16777619)
    }) % 16
}

pub async fn fetch_conference_acc(
    base_url: &str,
    title: &str,
) -> Result<Vec<ConfAccRate>, Box<dyn std::error::Error>> {
    let url = format!(
        "{base_url}/conference/parts/acceptance-{:02}.json",
        acceptance_bucket(title)
    );
    match fetch_json_with_cache_recovery(&url).await {
        Ok(data) => Ok(data),
        Err(_) => {
            fetch_json_with_cache_recovery(&format!("{base_url}/conference/allacc.json")).await
        }
    }
}

async fn fetch_json_with_cache_recovery<T: DeserializeOwned>(
    url: &str,
) -> Result<T, Box<dyn std::error::Error>> {
    match fetch_json(url, false).await {
        Ok(data) => Ok(data),
        Err(error)
            if error
                .downcast_ref::<std::io::Error>()
                .is_some_and(|error| error.kind() == std::io::ErrorKind::TimedOut) =>
        {
            Err(error)
        }
        Err(_) => fetch_json(url, true).await,
    }
}

struct RequestDeadline {
    controller: AbortController,
    window: web_sys::Window,
    timer: i32,
    _callback: Closure<dyn FnMut()>,
}

impl RequestDeadline {
    fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let window =
            web_sys::window().ok_or_else(|| std::io::Error::other("browser unavailable"))?;
        let controller = AbortController::new()
            .map_err(|_| std::io::Error::other("unable to create request deadline"))?;
        let timer_controller = controller.clone();
        let callback =
            Closure::wrap(Box::new(move || timer_controller.abort()) as Box<dyn FnMut()>);
        let timer = window
            .set_timeout_with_callback_and_timeout_and_arguments_0(
                callback.as_ref().unchecked_ref(),
                10_000,
            )
            .map_err(|_| std::io::Error::other("unable to start request deadline"))?;
        Ok(Self {
            controller,
            window,
            timer,
            _callback: callback,
        })
    }
}

impl Drop for RequestDeadline {
    fn drop(&mut self) {
        self.window.clear_timeout_with_handle(self.timer);
    }
}

async fn fetch_json<T: DeserializeOwned>(
    url: &str,
    reload: bool,
) -> Result<T, Box<dyn std::error::Error>> {
    let deadline = RequestDeadline::new()?;
    let mut request = Request::get(url).abort_signal(Some(&deadline.controller.signal()));
    if reload {
        request = request.cache(RequestCache::Reload);
    }

    let result = async {
        let response = request.send().await?;
        if !response.ok() {
            return Err(std::io::Error::other(format!(
                "request for {url} returned HTTP {}",
                response.status()
            ))
            .into());
        }

        let body = response.binary().await?;
        Ok(serde_json::from_slice(&body)?)
    }
    .await;
    if deadline.controller.signal().aborted() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::TimedOut,
            "conference request timed out",
        )
        .into());
    }
    result
}

pub fn get_categories() -> Vec<Category> {
    vec![
        Category {
            name: "计算机体系结构/并行与分布计算/存储系统".to_string(),
            name_en: "Computer Architecture".to_string(),
            sub: "DS".to_string(),
        },
        Category {
            name: "计算机网络".to_string(),
            name_en: "Network System".to_string(),
            sub: "NW".to_string(),
        },
        Category {
            name: "网络与信息安全".to_string(),
            name_en: "Network and System Security".to_string(),
            sub: "SC".to_string(),
        },
        Category {
            name: "软件工程/系统软件/程序设计语言".to_string(),
            name_en: "Software Engineering".to_string(),
            sub: "SE".to_string(),
        },
        Category {
            name: "数据库/数据挖掘/内容检索".to_string(),
            name_en: "Database".to_string(),
            sub: "DB".to_string(),
        },
        Category {
            name: "计算机科学理论".to_string(),
            name_en: "Computing Theory".to_string(),
            sub: "CT".to_string(),
        },
        Category {
            name: "计算机图形学与多媒体".to_string(),
            name_en: "Graphics".to_string(),
            sub: "CG".to_string(),
        },
        Category {
            name: "人工智能".to_string(),
            name_en: "Artificial Intelligence".to_string(),
            sub: "AI".to_string(),
        },
        Category {
            name: "人机交互与普适计算".to_string(),
            name_en: "Computer-Human Interaction".to_string(),
            sub: "HI".to_string(),
        },
        Category {
            name: "交叉/综合/新兴".to_string(),
            name_en: "Interdiscipline".to_string(),
            sub: "MX".to_string(),
        },
    ]
}

#[cfg(test)]
mod loading_tests {
    use super::*;

    #[test]
    fn acceptance_buckets_match_python_generator() {
        assert_eq!(acceptance_bucket("ICLR"), 11);
        assert_eq!(acceptance_bucket("VLDB"), 9);
        assert_eq!(acceptance_bucket("中文"), 5);
    }

    #[test]
    fn historical_loading_merges_editions_without_duplicate_cards() {
        let conference = |years: &[i32]| -> Conference {
            serde_json::from_value(serde_json::json!({
                "title": "Example", "description": "Example conference", "sub": "AI",
                "rank": {"ccf": "A"}, "dblp": "example",
                "confs": years.iter().map(|year| serde_json::json!({
                    "year": year, "id": format!("example{year}"), "link": "https://example.com",
                    "timeline": [{"deadline": "TBD"}], "timezone": "UTC", "date": "TBD", "place": "TBD"
                })).collect::<Vec<_>>()
            })).expect("valid conference fixture")
        };
        let mut current = vec![conference(&[2027])];
        merge_conferences(&mut current, vec![conference(&[2025, 2026, 2027])]);
        merge_conferences(&mut current, vec![conference(&[2025, 2026])]);
        assert_eq!(current.len(), 1);
        assert_eq!(
            current[0]
                .confs
                .iter()
                .map(|edition| edition.year)
                .collect::<Vec<_>>(),
            vec![2025, 2026, 2027]
        );
    }
}
