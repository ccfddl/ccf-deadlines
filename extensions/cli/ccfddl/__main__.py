import requests
import yaml
from termcolor import colored
from argparse import ArgumentParser
from datetime import datetime, timezone
from tabulate import tabulate


def parse_tz(tz: str) -> str:
    if tz == "AoE":
        return "-1200"
    elif tz.startswith("UTC-"):
        return "-{:02d}00".format(int(tz[4:]))
    elif tz.startswith("UTC+"):
        return "+{:02d}00".format(int(tz[4:]))
    else:
        return "+0000"


def parse_args():
    parser = ArgumentParser(description="cli for ccfddl")
    parser.add_argument("--conf", type=str, nargs='+',
                        help="A list of conference ids you want to filter, e.g.: '--conf CVPR ICML'")
    parser.add_argument("--sub", type=str, nargs='+',
                        help="A list of subcategories ids you want to filter, e.g.: '--sub AI CG'")
    parser.add_argument("--rank", type=str, nargs='+',
                        help="A list of ranks you want to filter, e.g.: '--rank C N'")
    args = parser.parse_args()
    if args.conf:
        args.conf = [arg.lower() for arg in args.conf]
    if args.sub:
        args.sub = [arg.lower() for arg in args.sub]
    if args.rank:
        args.rank = [arg.lower() for arg in args.rank]
    return args


def format_duration(ddl_time: datetime, now: datetime) -> str:
    duration = ddl_time - now
    months, days = duration.days // 30, duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    day_word_str = "days" if days > 1 else "day "
    months_str, days_str = str(months).zfill(2), str(days).zfill(2)
    hours_str, minutes_str = str(hours).zfill(2), str(minutes).zfill(2)

    if days < 1:
        return colored(f'{hours_str}:{minutes_str}:{seconds}', "red")
    if days < 30:
        return colored(f'{days_str} {day_word_str}, {hours_str}:{minutes_str}', "yellow")
    if days < 100:
        return colored(f"{days_str} {day_word_str}", "blue")
    return colored(f"{months_str} months", "green")


def extract_alpha_id(with_digits: str) -> str:
    return ''.join(char for char in with_digits.lower() if char.isalpha())


def main():
    args = parse_args()
    yml_str = requests.get(
        "https://ccfddl.github.io/conference/allconf.yml").content.decode("utf-8")
    all_conf = yaml.safe_load(yml_str)

    all_conf_ext = []
    now = datetime.now(tz=timezone.utc)
    for conf in all_conf:
        base_info = {
            "title": conf["title"],
            "sub": conf["sub"],
            "rank": conf["rank"]["ccf"],
            "dblp": conf.get("dblp", ""),
        }
        for c in conf["confs"]:
            cur_conf = {**base_info, **c}
            cur_conf["title"] = base_info["title"] + str(c["year"])
            time_obj = None
            tz = parse_tz(c["timezone"])
            for d in c["timeline"]:
                deadline_str = d.get("deadline", "")
                if not deadline_str or deadline_str == "TBD":
                    continue
                try:
                    cur_d = datetime.strptime(
                        f"{deadline_str} {tz}", '%Y-%m-%d %H:%M:%S %z')
                    if cur_d < now:
                        continue
                    if time_obj is None or cur_d < time_obj:
                        time_obj = cur_d
                except ValueError:
                    continue
            if time_obj is not None and time_obj > now:
                cur_conf["time_obj"] = time_obj
                all_conf_ext.append(cur_conf)

    all_conf_ext.sort(key=lambda x: x['time_obj'])

    table = [["Title", "Sub", "Rank", "DDL", "Link"]]
    for x in all_conf_ext:
        if args.conf and extract_alpha_id(x["id"]) not in args.conf:
            continue
        if args.sub and extract_alpha_id(x["sub"]) not in args.sub:
            continue
        if args.rank and x["rank"].lower() not in args.rank:
            continue
        table.append([
            x["title"],
            x["sub"],
            x["rank"],
            format_duration(x["time_obj"], now),
            x["link"]
        ])

    print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))


if __name__ == "__main__":
    main()