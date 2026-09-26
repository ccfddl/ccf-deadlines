use chrono::prelude::*;
use gloo_net::http::Request;
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use web_sys::RequestCache;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conference {
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
    pub place: String,
}

#[derive(Debug, Deserialize)]
pub struct ConfAccRate {
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
    pub notification_deadline: Option<String>,
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
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct ConfItem {
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
    pub estimated_deadlines: Vec<EstimatedDeadline>,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct EstimatedDeadline {
    pub deadline: String,
    pub is_abstract: bool,
    pub source_year: i32,
}

pub async fn fetch_all_conf(base_url: &str) -> Result<Vec<Conference>, Box<dyn std::error::Error>> {
    let url = format!("{base_url}/conference/allconf.json");
    fetch_json_with_cache_recovery(&url).await
}

pub async fn fetch_all_acc(base_url: &str) -> Result<Vec<ConfAccRate>, Box<dyn std::error::Error>> {
    let url = format!("{base_url}/conference/allacc.json");
    fetch_json_with_cache_recovery(&url).await
}

async fn fetch_json_with_cache_recovery<T: DeserializeOwned>(
    url: &str,
) -> Result<T, Box<dyn std::error::Error>> {
    match fetch_json(url, false).await {
        Ok(data) => Ok(data),
        Err(_) => fetch_json(url, true).await,
    }
}

async fn fetch_json<T: DeserializeOwned>(
    url: &str,
    reload: bool,
) -> Result<T, Box<dyn std::error::Error>> {
    let mut request = Request::get(url);
    if reload {
        request = request.cache(RequestCache::Reload);
    }

    let response = request.send().await?;
    if !response.ok() {
        return Err(std::io::Error::other(format!(
            "request for {url} returned HTTP {}",
            response.status()
        ))
        .into());
    }

    let body = response.text().await?;
    Ok(serde_json::from_str(&body)?)
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
