use chrono::prelude::*;
use gloo_net::http::Request;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct Conference {
    pub title: String,
    pub description: String,
    pub sub: String,
    pub rank: Rank,
    pub dblp: String,
    pub confs: Vec<ConferenceYear>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Rank {
    pub ccf: String,
    pub core: Option<String>,
    pub thcpl: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ConferenceYear {
    pub year: i32,
    pub id: String,
    pub link: String,
    pub timeline: Vec<Timeline>,
    pub timezone: String,
    pub date: String,
    pub place: String,
    pub acc_str: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Timeline {
    pub abstract_deadline: Option<String>,
    pub deadline: String,
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
}

pub async fn fetch_all_conf(
    base_url: &str,
    archived: bool,
) -> Result<Vec<Conference>, Box<dyn std::error::Error>> {
    let filename = if archived {
        "allconf_archive.json"
    } else {
        "allconf.json"
    };
    let url = format!("{base_url}/conference/{filename}");
    Ok(Request::get(&url)
        .send()
        .await?
        .json::<Vec<Conference>>()
        .await?)
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
