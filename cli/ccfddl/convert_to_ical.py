import yaml
from icalendar import Calendar, Event, Timezone, TimezoneStandard
import re
from datetime import datetime, timedelta, timezone
import uuid

# 中英类别映射表
def load_mapping(path: str="conference/types.yml"):
    with open(path) as f:
        types = yaml.safe_load(f)
    SUB_MAPPING = {}
    for types_data in types:
        SUB_MAPPING[types_data['sub']] = types_data['name']
    return SUB_MAPPING

def get_timezone(tz_str: str) -> timezone:
    """将时区字符串转换为datetime.timezone对象"""
    if tz_str == 'AoE':
        return timezone(timedelta(hours=-12))
    match = re.match(r'UTC([+-])(\d{1,2})$', tz_str)
    if not match:
        raise ValueError(f"无效的时区格式: {tz_str}")
    sign, hours = match.groups()
    offset = int(hours) if sign == '+' else -int(hours)
    return timezone(timedelta(hours=offset))

def create_vtimezone(tz: timezone) -> Timezone:
    """创建VTIMEZONE组件"""
    tz_offset = tz.utcoffset(datetime.now())
    offset_hours = tz_offset.total_seconds() // 3600
    tzid = f"UTC{offset_hours:+03.0f}:00"

    vtz = Timezone()
    vtz.add('TZID', tzid)

    std = TimezoneStandard()
    std.add('DTSTART', datetime(1970, 1, 1))
    std.add('TZOFFSETFROM', timedelta(hours=offset_hours))
    std.add('TZOFFSETTO', timedelta(hours=offset_hours))
    std.add('TZNAME', tzid)

    vtz.add_component(std)
    return vtz

def convert_to_ical(file_paths: list[str], output_path: str, lang: str='en', SUB_MAPPING={}):
    cal = Calendar()
    cal.add('prodid', '-//会议截止日历//ccfddl.com//')
    cal.add('version', '2.0')

    added_tzids = set()
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            conferences = yaml.safe_load(f)

        for conf_data in conferences:
            title = conf_data['title']
            sub = conf_data['sub']
            sub_chinese = SUB_MAPPING.get(sub, sub)
            rank = conf_data['rank']
            dblp = conf_data['dblp']

            for conf in conf_data['confs']:
                year = conf['year']
                link = conf['link']
                timeline = conf['timeline']
                timezone = conf['timezone']
                place = conf['place']
                date = conf['date']

                for entry in timeline:
                    timezone_str = conf['timezone']
                    try:
                        tz = get_timezone(timezone_str)
                    except ValueError:
                        continue

                    # 添加VTIMEZONE组件
                    tz_offset = tz.utcoffset(datetime.now())
                    offset_hours = tz_offset.total_seconds() // 3600
                    tzid = f"UTC{offset_hours:+03.0f}:00"

                    if tzid not in added_tzids:
                        vtz = create_vtimezone(tz)
                        cal.add_component(vtz)
                        added_tzids.add(tzid)

                    # 判断截止类型
                    deadline_type, deadline_str = None, None
                    if 'abstract_deadline' in entry:
                        deadline_type = ('摘要截稿', 'Abstract Deadline')
                        deadline_str = entry['abstract_deadline']
                    elif 'deadline' in entry:
                        deadline_type = ('截稿日期', 'Deadline')
                        deadline_str = entry['deadline']
                    else:
                        continue  # 跳过无效条目

                    if deadline_str == 'TBD':
                        continue  # 忽略待定日期

                    # 解析日期和时间
                    is_all_day = False
                    try:
                        deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d')
                            is_all_day = True
                        except ValueError:
                            continue  # 无效日期格式

                    # 创建事件对象
                    event = Event()
                    event.add('uid', uuid.uuid4())
                    event.add('dtstamp', datetime.now(get_timezone(timezone)))  # UTC时区感知

                    # 处理时间字段
                    if is_all_day:
                        event.add('dtstart', deadline_dt.date())
                        event.add('dtend', (deadline_dt + timedelta(days=1)).date())
                    else:
                        aware_dt = deadline_dt.replace(tzinfo=tz)
                        event.add('dtstart', aware_dt)
                        event.add('dtend', aware_dt + timedelta(minutes=1))

                    # 构建中英双语摘要
                    if lang == 'en':
                        summary = f"{title} {year} {deadline_type[1]}"
                    else:
                        summary = f"{title} {year} {deadline_type[0]}"

                    # 添加注释信息
                    if 'comment' in entry:
                        summary += f" [{entry['comment']}]"
                    event.add('summary', summary)

                    # 构建详细描述
                    level_desc = [
                        f"CCF {rank['ccf']}" if rank['ccf'] != "N" else None,
                        f"CORE {rank['core']}" if rank.get('core', 'N') != "N" else None,
                        f"THCPL {rank['thcpl']}" if rank.get('thcpl', 'N') != "N" else None,
                    ]
                    level_desc = [line for line in level_desc if line]
                    if len(level_desc) > 0:
                        level_desc = ", ".join(level_desc)
                    else:
                        level_desc = None
                    if lang == 'en':
                        description = [
                            f"{conf_data['description']}",
                            f"🗓️ Date: {date}",
                            f"📍 Location: {place}",
                            f"⏰ Original Deadline ({timezone}): {deadline_str}",
                            f"Category: {sub_chinese} ({sub})",
                            level_desc,
                            f"Conference Website: {link}",
                            f"DBLP Index: https://dblp.org/db/conf/{dblp}",
                        ]
                    else:
                        description = [
                            f"{conf_data['description']}",
                            f"🗓️ 会议时间: {date}",
                            f"📍 会议地点: {place}",
                            f"⏰ 原始截止时间 ({timezone}): {deadline_str}",
                            f"分类: {sub_chinese} ({sub})",
                            level_desc,
                            f"会议官网: {link}",
                            f"DBLP索引: https://dblp.org/db/conf/{dblp}",
                        ]
                    description = [line for line in description if line]
                    event.add('description', '\n'.join(description))

                    # 添加其他元信息
                    event.add('location', place)
                    event.add('url', link)

                    cal.add_component(event)

    # 写入输出文件
    with open(output_path, 'wb') as f:
        f.write(cal.to_ical())

if __name__ == '__main__':
    from xlin.util import ls
    SUB_MAPPING = load_mapping("conference/types.yml")
    paths = ls("conference", filter=lambda f: f.name != "types.yml")
    convert_to_ical(paths, 'deadlines_zh.ics', 'zh', SUB_MAPPING)
    convert_to_ical(paths, 'deadlines_en.ics', 'en', SUB_MAPPING)