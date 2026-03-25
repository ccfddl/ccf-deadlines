import uuid
from datetime import datetime, timedelta
from icalendar import Calendar, Event, Timezone, TimezoneStandard
import yaml

from ccfddl.utils import load_mapping, get_timezone, reverse_index


def create_vtimezone(tz) -> Timezone:
    tz_offset = tz.utcoffset(datetime.now())
    offset_hours = tz_offset.total_seconds() // 3600
    tzid = f"UTC{offset_hours:+03.0f}:00"

    vtz = Timezone()
    vtz.add("TZID", tzid)

    std = TimezoneStandard()
    std.add("DTSTART", datetime(1970, 1, 1))
    std.add("TZOFFSETFROM", timedelta(hours=offset_hours))
    std.add("TZOFFSETTO", timedelta(hours=offset_hours))
    std.add("TZNAME", tzid)

    vtz.add_component(std)
    return vtz


def convert_to_ical(
    file_paths: list[str],
    output_path: str,
    lang: str = "en",
    sub_mapping: dict | None = None,
) -> None:
    if sub_mapping is None:
        sub_mapping = {}

    cal = Calendar()
    cal.add("prodid", "-//会议截止日历//ccfddl.com//")
    cal.add("version", "2.0")

    added_tzids: set[str] = set()
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

                    tz_offset = tz.utcoffset(datetime.now())
                    offset_hours = tz_offset.total_seconds() // 3600
                    tzid = f"UTC{offset_hours:+03.0f}:00"

                    if tzid not in added_tzids:
                        vtz = create_vtimezone(tz)
                        cal.add_component(vtz)
                        added_tzids.add(tzid)

                    deadlines_to_process = []

                    if "abstract_deadline" in entry:
                        deadlines_to_process.append(
                            (("摘要截稿", "Abstract Deadline"), entry["abstract_deadline"])
                        )

                    if "deadline" in entry:
                        deadlines_to_process.append(
                            (("截稿日期", "Deadline"), entry["deadline"])
                        )

                    if not deadlines_to_process:
                        continue

                    for deadline_type, deadline_str in deadlines_to_process:
                        if deadline_str == "TBD":
                            continue

                        is_all_day = False
                        try:
                            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
                                is_all_day = True
                            except ValueError:
                                continue

                        event = Event()
                        event.add("uid", uuid.uuid4())
                        event.add("dtstamp", datetime.now(tz))

                        if is_all_day:
                            event.add("dtstart", deadline_dt.date())
                            event.add("dtend", (deadline_dt + timedelta(days=1)).date())
                        else:
                            aware_dt = deadline_dt.replace(tzinfo=tz)
                            event.add("dtstart", aware_dt)
                            event.add("dtend", aware_dt + timedelta(minutes=1))

                        if lang == "en":
                            summary = f"{title} {year} {deadline_type[1]}"
                        else:
                            summary = f"{title} {year} {deadline_type[0]}"

                        if "comment" in entry:
                            summary += f" [{entry['comment']}]"
                        event.add("summary", summary)

                        level_desc = [
                            f"CCF {rank['ccf']}" if rank["ccf"] != "N" else None,
                            f"CORE {rank['core']}" if rank.get("core", "N") != "N" else None,
                            f"THCPL {rank['thcpl']}" if rank.get("thcpl", "N") != "N" else None,
                        ]
                        level_desc = [line for line in level_desc if line]
                        level_str = ", ".join(level_desc) if level_desc else None

                        if lang == "en":
                            description = [
                                f"{conf_data['description']}",
                                f"Date: {date}",
                                f"Location: {place}",
                                f"Original Deadline ({timezone_str}): {deadline_str}",
                                f"Category: {sub_chinese} ({sub})",
                                level_str,
                                f"Conference Website: {link}",
                                f"DBLP: https://dblp.org/db/conf/{dblp}",
                            ]
                        else:
                            description = [
                                f"{conf_data['description']}",
                                f"会议时间: {date}",
                                f"会议地点: {place}",
                                f"原始截止时间 ({timezone_str}): {deadline_str}",
                                f"分类: {sub_chinese} ({sub})",
                                level_str,
                                f"会议官网: {link}",
                                f"DBLP索引: https://dblp.org/db/conf/{dblp}",
                            ]
                        description = [line for line in description if line]
                        event.add("description", "\n".join(description))

                        event.add("location", place)
                        event.add("url", link)

                        cal.add_component(event)

    with open(output_path, "wb") as f:
        f.write(cal.to_ical())


if __name__ == "__main__":
    from xlin import ls, element_mapping

    sub_mapping = load_mapping("conference/types.yml")
    paths = ls("conference", filter=lambda f: f.name != "types.yml")
    index = reverse_index(paths, list(sub_mapping.keys()))
    for lang in ["zh", "en"]:
        convert_to_ical(paths, f"deadlines_{lang}.ics", lang, sub_mapping)
        f = lambda key: (
            len(index[key]) > 0,
            convert_to_ical(
                index[key],
                f"deadlines_{lang}_{key.replace('*', 'star')}.ics",
                lang,
                sub_mapping,
            ),
        )
        element_mapping(index.keys(), f, thread_pool_size=8)
    print("转换完成")
