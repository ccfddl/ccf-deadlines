import yaml
import re
import uuid
import json
from collections import defaultdict
from itertools import combinations
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from icalendar import Calendar, Event, Timezone, TimezoneStandard

if __package__:
    from .utils import deadline_sort_key, parse_deadline
else:
    from utils import deadline_sort_key, parse_deadline


# 中英类别映射表
def load_mapping(path: str = "conference/types.yml"):
    with open(path, encoding="utf-8") as f:
        types = yaml.safe_load(f)
    if types is None:
        return {}
    SUB_MAPPING = {}
    for types_data in types:
        SUB_MAPPING[types_data["sub"]] = types_data["name"]
    return SUB_MAPPING


def nth_sunday(year: int, month: int, n: int) -> date:
    """返回该年月的第n个星期日"""
    first = date(year, month, 1)
    # date.weekday(): Monday=0 ... Sunday=6
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def is_us_dst(day: date) -> bool:
    """美国夏令时区间: 3月第2个星期日 至 11月第1个星期日"""
    return nth_sunday(day.year, 3, 2) <= day < nth_sunday(day.year, 11, 1)


def get_timezone(tz_str: str, on_date: date | None = None) -> timezone:
    """将时区字符串转换为datetime.timezone对象

    PT (美国太平洋时间) 会随夏令时变化: 夏令时为 UTC-7, 其余为 UTC-8。
    未提供 on_date 时按标准时间 UTC-8 处理。
    """
    if tz_str == "AoE":
        return timezone(timedelta(hours=-12))
    if tz_str == "UTC":
        return timezone.utc
    if tz_str == "PT":
        if on_date is not None and is_us_dst(on_date):
            return timezone(timedelta(hours=-7))
        return timezone(timedelta(hours=-8))
    match = re.match(r"UTC([+-])(\d{1,2})$", tz_str)
    if not match:
        raise ValueError(f"无效的时区格式: {tz_str}")
    sign, hours = match.groups()
    offset = int(hours) if sign == "+" else -int(hours)
    return timezone(timedelta(hours=offset))


def create_vtimezone(tz: timezone) -> Timezone:
    """创建VTIMEZONE组件"""
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
    file_paths: list[str], output_path: str, lang: str = "en", SUB_MAPPING={}
):
    cal = Calendar()
    cal.add("prodid", "-//会议截止日历//ccfddl.com//")
    cal.add("version", "2.0")

    added_tzids = set()
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

        for conf_data in conferences:
            title = conf_data["title"]
            sub = conf_data["sub"]
            sub_chinese = SUB_MAPPING.get(sub, sub)
            rank = conf_data["rank"]
            dblp = conf_data["dblp"]

            for conf in conf_data["confs"]:
                year = conf["year"]
                link = conf["link"]
                timeline = conf["timeline"]
                timezone_str = conf["timezone"]
                place = conf["place"]
                conference_date = conf["date"]

                for round_index, entry in enumerate(timeline):
                    # 收集所有需要处理的截止日期
                    deadlines_to_process = []

                    if "abstract_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                "Abstract Deadline",
                                entry["abstract_deadline"],
                            )
                        )

                    if "deadline" in entry:
                        deadlines_to_process.append(
                            ("Deadline", entry["deadline"])
                        )

                    if "rebuttal_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                "Rebuttal Submission",
                                entry["rebuttal_deadline"],
                            )
                        )

                    if "decision_deadline" in entry:
                        deadlines_to_process.append(
                            (
                                "Final Decisions",
                                entry["decision_deadline"],
                            )
                        )

                    # 如果没有任何截止日期，跳过
                    if not deadlines_to_process:
                        continue

                    # 处理每个截止日期
                    for deadline_type, deadline_str in deadlines_to_process:
                        if deadline_str == "TBD":
                            continue  # 忽略待定日期

                        try:
                            deadline_dt = parse_deadline(deadline_str, timezone_str)
                        except ValueError:
                            continue
                        is_all_day = not isinstance(deadline_dt, datetime)

                        # Calendar dates have no clock or timezone conversion.
                        # DTSTAMP below is the generation instant, not the deadline.
                        if not is_all_day:
                            tz = deadline_dt.tzinfo
                            tz_offset = tz.utcoffset(deadline_dt)
                            offset_hours = tz_offset.total_seconds() // 3600
                            tzid = f"UTC{offset_hours:+03.0f}:00"
                            if tzid not in added_tzids:
                                cal.add_component(create_vtimezone(tz))
                                added_tzids.add(tzid)

                        # 创建事件对象
                        event = Event()
                        event.add(
                            "uid",
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"ccfddl:{conf['id']}:{round_index}:{deadline_type}",
                            ),
                        )
                        event.add("X-CCFDDL-ID", conf["id"])
                        event.add("X-CCFDDL-CONFERENCE", f"{title} {year}")
                        event.add("X-CCFDDL-TIMEZONE", timezone_str)
                        event.add("X-CCFDDL-PRECISION", "date" if is_all_day else "datetime")
                        event.add("dtstamp", datetime.now(timezone.utc))

                        # 处理时间字段
                        if is_all_day:
                            event.add("dtstart", deadline_dt)
                            if deadline_dt < date.max:
                                event.add("dtend", deadline_dt + timedelta(days=1))
                            else:
                                event.add("duration", timedelta(days=1))
                        else:
                            event.add("dtstart", deadline_dt)
                            event.add("dtend", deadline_dt + timedelta(minutes=1))

                        # 两种订阅语言都使用英文事件标题；说明保留所选语言。
                        summary = f"{title} {year} {deadline_type}"

                        # 添加注释信息
                        if "comment" in entry:
                            summary += f" [{entry['comment']}]"
                        event.add("summary", summary)

                        # 构建详细描述
                        level_desc = [
                            f"CCF {rank['ccf']}" if rank["ccf"] != "N" else None,
                            f"CORE {rank['core']}"
                            if rank.get("core", "N") != "N"
                            else None,
                            f"THCPL {rank['thcpl']}"
                            if rank.get("thcpl", "N") != "N"
                            else None,
                        ]
                        level_desc = [line for line in level_desc if line]
                        if len(level_desc) > 0:
                            level_desc = ", ".join(level_desc)
                        else:
                            level_desc = None
                        if lang == "en":
                            description = [
                                f"{conf_data['description']}",
                                f"🗓️ Date: {conference_date}",
                                f"📍 Location: {place}",
                                f"⏰ Original Deadline ({timezone_str}): {deadline_str}",
                                f"Category: {sub_chinese} ({sub})",
                                level_desc,
                                f"Conference Website: {link}",
                                f"DBLP Index: https://dblp.org/db/conf/{dblp}",
                            ]
                        else:
                            description = [
                                f"{conf_data['description']}",
                                f"🗓️ 会议时间: {conference_date}",
                                f"📍 会议地点: {place}",
                                f"⏰ 原始截止时间 ({timezone_str}): {deadline_str}",
                                f"分类: {sub_chinese} ({sub})",
                                level_desc,
                                f"会议官网: {link}",
                                f"DBLP索引: https://dblp.org/db/conf/{dblp}",
                            ]
                        if is_all_day:
                            description.append(
                                "Time of day is unknown; this is a calendar date, not an instant."
                                if lang == "en" else "具体时刻未知；此条目仅表示日期，不表示精确时间。"
                            )
                        description = [line for line in description if line]
                        event.add("description", "\n".join(description))

                        # 添加其他元信息
                        event.add("location", place)
                        event.add("url", link)

                        cal.add_component(event)

    # 写入输出文件
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())


def write_deadline_events_index(calendar_path: str, output_path: str):
    """Expose exact instants or date-only metadata to the reminder Worker."""
    calendar = Calendar.from_ical(Path(calendar_path).read_bytes())
    events = []
    for event in calendar.walk("VEVENT"):
        start = event.decoded("DTSTART")
        all_day = isinstance(start, date) and not isinstance(start, datetime)
        if not all_day and (
            start.tzinfo is None
            or str(event.get("X-CCFDDL-TIMEZONE", "")) == "Unknown"
        ):
            raise ValueError("Precise reminders require a known timezone")
        # A calendar date is never converted into midnight for reminders.
        deadline_at = (
            None if all_day
            else start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        events.append(
            {
                "id": str(event["X-CCFDDL-ID"]),
                "conference": str(event["X-CCFDDL-CONFERENCE"]),
                "uid": str(event["UID"]),
                "title": str(event["SUMMARY"]),
                "deadline_at": deadline_at,
                "deadline_date": start.isoformat() if all_day else None,
                "precision": "date" if all_day else "datetime",
                "timezone": str(event.get("X-CCFDDL-TIMEZONE", "Unknown")),
                "all_day": all_day,
                "url": str(event.get("URL", "")),
            }
        )
    def sort_key(item):
        value = (
            date.fromisoformat(item["deadline_date"]) if item["all_day"]
            else datetime.fromisoformat(item["deadline_at"].replace("Z", "+00:00"))
        )
        # The source-zone lower bound orders output but is never serialized.
        return deadline_sort_key(value, item["timezone"]), item["id"], item["uid"]

    events.sort(key=sort_key)
    Path(output_path).write_text(
        json.dumps(events, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def add_index_entry(index, key: str, file_path: str):
    index[key].add(file_path)


def reverse_index(file_paths: list[str], subs: list[str]):
    index = defaultdict(set)

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

        if conferences is None:
            continue

        for conf_data in conferences:
            sub = conf_data["sub"]
            rank = conf_data["rank"]
            ccf_rank = rank.get("ccf", "N")
            core_rank = rank.get("core", "N")
            thcpl_rank = rank.get("thcpl", "N")
            rank_keys = [
                f"ccf_{ccf_rank}",
                f"core_{core_rank}",
                f"thcpl_{thcpl_rank}",
            ]

            add_index_entry(index, sub, file_path)

            for size in range(1, len(rank_keys) + 1):
                for combo in combinations(rank_keys, size):
                    key = "_".join(combo)
                    add_index_entry(index, key, file_path)
                    add_index_entry(index, f"{key}_{sub}", file_path)

    return {key: sorted(paths) for key, paths in index.items()}


if __name__ == "__main__":
    from xlin import ls, element_mapping

    SUB_MAPPING = load_mapping("conference/types.yml")
    paths = ls("conference", filter=lambda f: f.name != "types.yml")
    index = reverse_index(paths, list(SUB_MAPPING.keys()))
    for lang in ["zh", "en"]:
        convert_to_ical(paths, f"deadlines_{lang}.ics", lang, SUB_MAPPING)
        if lang == "en":
            write_deadline_events_index(
                "deadlines_en.ics", "public/conference/deadline_events.json"
            )
        f = lambda key: (
            len(index[key]) > 0,
            convert_to_ical(
                index[key],
                f"deadlines_{lang}_{key.replace('*', 'star')}.ics",
                lang,
                SUB_MAPPING,
            ),
        )
        element_mapping(index.keys(), f, thread_pool_size=8)
    print("转换完成")
