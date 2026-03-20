import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime

import yaml

from ccfddl.utils import load_mapping, get_timezone, reverse_index


def convert_to_rss(
    file_paths: list[str],
    output_path: str,
    lang: str = "en",
    sub_mapping: dict | None = None,
) -> None:
    if sub_mapping is None:
        sub_mapping = {}

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = (
        "CCF Conference Deadlines" if lang == "en" else "CCF 会议截止日期"
    )
    ET.SubElement(channel, "link").text = "https://ccfddl.com"
    ET.SubElement(channel, "description").text = (
        "Conference submission deadline tracking"
        if lang == "en"
        else "会议投稿截止日期追踪"
    )
    ET.SubElement(channel, "language").text = "en" if lang == "en" else "zh-CN"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

        for conf_data in conferences:
            title = conf_data["title"]
            sub = conf_data["sub"]
            sub_chinese = sub_mapping.get(sub, sub)
            rank = conf_data["rank"]
            dblp = conf_data["dblp"]

            for conf in conf_data["confs"]:
                year = conf["year"]
                link = conf["link"]
                timeline = conf["timeline"]
                timezone_str = conf["timezone"]
                place = conf["place"]
                date = conf["date"]

                for entry in timeline:
                    try:
                        tz = get_timezone(timezone_str)
                    except ValueError:
                        continue

                    deadlines_to_process = []

                    if "abstract_deadline" in entry:
                        deadlines_to_process.append(
                            (("摘要截稿", "Abstract Deadline"), entry["abstract_deadline"], "abstract")
                        )

                    if "deadline" in entry:
                        deadlines_to_process.append(
                            (("截稿日期", "Deadline"), entry["deadline"], "deadline")
                        )

                    if not deadlines_to_process:
                        continue

                    for deadline_type, deadline_str, type_key in deadlines_to_process:
                        if deadline_str == "TBD":
                            continue

                        try:
                            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
                            except ValueError:
                                continue

                        aware_dt = deadline_dt.replace(tzinfo=tz)

                        item = ET.SubElement(channel, "item")

                        if lang == "en":
                            summary = f"{title} {year} {deadline_type[1]}"
                        else:
                            summary = f"{title} {year} {deadline_type[0]}"

                        if "comment" in entry:
                            summary += f" [{entry['comment']}]"

                        ET.SubElement(item, "title").text = summary
                        ET.SubElement(item, "link").text = link

                        level_desc = [
                            f"CCF {rank['ccf']}" if rank["ccf"] != "N" else None,
                            f"CORE {rank['core']}" if rank.get("core", "N") != "N" else None,
                            f"THCPL {rank['thcpl']}" if rank.get("thcpl", "N") != "N" else None,
                        ]
                        level_desc = [x for x in level_desc if x]
                        level_str = ", ".join(level_desc) if level_desc else None

                        if lang == "en":
                            desc_lines = [
                                conf_data["description"],
                                f"Date: {date}",
                                f"Location: {place}",
                                f"Deadline ({timezone_str}): {deadline_str}",
                                f"Category: {sub_chinese} ({sub})",
                                level_str,
                                f"Conference Website: {link}",
                                f"DBLP: https://dblp.org/db/conf/{dblp}",
                            ]
                        else:
                            desc_lines = [
                                conf_data["description"],
                                f"会议时间: {date}",
                                f"会议地点: {place}",
                                f"截止时间 ({timezone_str}): {deadline_str}",
                                f"分类: {sub_chinese} ({sub})",
                                level_str,
                                f"会议官网: {link}",
                                f"DBLP索引: https://dblp.org/db/conf/{dblp}",
                            ]
                        desc_lines = [x for x in desc_lines if x]
                        ET.SubElement(item, "description").text = "\n".join(desc_lines)

                        ET.SubElement(item, "pubDate").text = format_datetime(aware_dt)

                        guid = ET.SubElement(item, "guid", isPermaLink="false")
                        guid.text = f"{title}-{year}-{type_key}-{deadline_str}@ccfddl.com"

                        ET.SubElement(item, "category").text = sub

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    with open(output_path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    from xlin import ls, element_mapping

    sub_mapping = load_mapping("conference/types.yml")
    paths = ls("conference", filter=lambda f: f.name != "types.yml")
    index = reverse_index(paths, list(sub_mapping.keys()))
    for lang in ["zh", "en"]:
        convert_to_rss(paths, f"deadlines_{lang}.xml", lang, sub_mapping)
        f = lambda key: (
            len(index[key]) > 0,
            convert_to_rss(
                index[key],
                f"deadlines_{lang}_{key.replace('*', 'star')}.xml",
                lang,
                sub_mapping,
            ),
        )
        element_mapping(index.keys(), f, thread_pool_size=8)
    print("RSS feed generation complete")
