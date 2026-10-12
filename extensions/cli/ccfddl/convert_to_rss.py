import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote, urlparse

from convert_to_ical import load_mapping, get_timezone, reverse_index

import yaml


ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM_NAMESPACE)


def convert_to_rss(
    file_paths: list[str],
    output_path: str,
    lang: str = "en",
    SUB_MAPPING={},
    feed_url: str | None = None,
):
    if feed_url:
        parsed = urlparse(feed_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Feed URL must be an absolute HTTP(S) URL")
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
    if feed_url:
        ET.SubElement(
            channel, f"{{{ATOM_NAMESPACE}}}link",
            {"href": feed_url, "rel": "self", "type": "application/rss+xml"},
        )
    # Source records do not carry publication/update dates. Neither a deadline
    # nor the build clock establishes when feed content was published or changed.
    items = []

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

        if conferences is None:
            continue

        for conf_data in conferences:
            title = conf_data["title"]
            sub = conf_data["sub"]
            sub_chinese = SUB_MAPPING.get(sub, sub)
            rank = conf_data["rank"]
            dblp = conf_data["dblp"]

            for conf in conf_data["confs"]:
                year = conf["year"]
                try:
                    sort_year = int(year)
                except (TypeError, ValueError):
                    sort_year = 0
                link = conf["link"]
                timeline = conf["timeline"]
                timezone_str = conf["timezone"]
                place = conf["place"]
                date = conf["date"]
                seen_deadlines = set()

                for round_number, entry in enumerate(timeline, start=1):
                    try:
                        get_timezone(timezone_str)
                    except ValueError:
                        continue

                    deadlines_to_process = []

                    if "abstract_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                ("摘要截稿", "Abstract Deadline"),
                                entry["abstract_deadline"],
                                "abstract",
                            )
                        )

                    if "deadline" in entry:
                        deadlines_to_process.append(
                            (("截稿日期", "Deadline"), entry["deadline"], "deadline")
                        )

                    if "rebuttal_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                ("答辩提交", "Rebuttal Submission"),
                                entry["rebuttal_deadline"],
                                "rebuttal",
                            )
                        )

                    if "decision_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                ("最终决定", "Final Decisions"),
                                entry["decision_deadline"],
                                "decision",
                            )
                        )

                    if not deadlines_to_process:
                        continue

                    for deadline_type, deadline_str, type_key in deadlines_to_process:
                        if deadline_str == "TBD":
                            continue

                        try:
                            datetime.strptime(
                                deadline_str, "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            try:
                                datetime.strptime(
                                    deadline_str, "%Y-%m-%d"
                                )
                            except ValueError:
                                continue

                        item = ET.Element("item")
                        items.append((sort_year, item))

                        if lang == "en":
                            summary = f"{title} {year} {deadline_type[1]}"
                        else:
                            summary = f"{title} {year} {deadline_type[0]}"

                        if "comment" in entry:
                            summary += f" [{entry['comment']}]"

                        ET.SubElement(item, "title").text = summary
                        ET.SubElement(item, "link").text = link

                        # Build description
                        level_desc = [
                            f"CCF {rank['ccf']}" if rank["ccf"] != "N" else None,
                            f"CORE {rank['core']}"
                            if rank.get("core", "N") != "N"
                            else None,
                            f"THCPL {rank['thcpl']}"
                            if rank.get("thcpl", "N") != "N"
                            else None,
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

                        guid = ET.SubElement(
                            item, "guid", isPermaLink="false"
                        )
                        # Shared dates can belong to distinct submission rounds.
                        # Keep the first and all noncolliding legacy IDs stable.
                        identity = (type_key, deadline_str)
                        suffix = f"-round-{round_number}" if identity in seen_deadlines else ""
                        seen_deadlines.add(identity)
                        guid.text = f"{title}-{year}-{type_key}-{deadline_str}{suffix}@ccfddl.com"

                        ET.SubElement(item, "category").text = sub

    # Put newer venue years first without inventing publication dates. Python's
    # stable sort keeps source order for conferences, rounds and types in a year.
    channel.extend(
        item for _, item in sorted(items, key=lambda entry: entry[0], reverse=True)
    )

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    with open(output_path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from xlin import ls, element_mapping

    parser = argparse.ArgumentParser(description="Generate conference RSS feeds")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--feed-base-url", help="Published directory URL for RSS self links")
    args = parser.parse_args()
    if args.feed_base_url:
        parsed = urlparse(args.feed_base_url)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.query or parsed.fragment):
            parser.error("--feed-base-url must be an absolute HTTP(S) directory URL without a query or fragment")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    SUB_MAPPING = load_mapping("conference/types.yml")
    paths = ls("conference", filter=lambda f: f.suffix == ".yml" and f.name != "types.yml")
    index = reverse_index(paths, list(SUB_MAPPING.keys()))

    def write_feed(paths, filename, lang):
        feed_url = (f"{args.feed_base_url.rstrip('/')}/{quote(filename)}"
                    if args.feed_base_url else None)
        convert_to_rss(paths, str(output_dir / filename), lang, SUB_MAPPING, feed_url)

    for lang in ["zh", "en"]:
        write_feed(paths, f"deadlines_{lang}.xml", lang)
        f = lambda key: (
            len(index[key]) > 0,
            write_feed(
                index[key],
                f"deadlines_{lang}_{key.replace('*', 'star')}.xml",
                lang,
            ),
        )
        element_mapping(index.keys(), f, thread_pool_size=8)
    print("RSS feed generation complete")
