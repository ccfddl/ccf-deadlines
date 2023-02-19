import requests
import yaml
from argparse import ArgumentParser
from copy import deepcopy
from datetime import datetime
from tabulate import tabulate
from datetime import timezone


def parse_tz(tz):
    if tz == "AoE":
        return "-1200"
    elif tz.startswith("UTC-"):
        return "-{:04d}".format(int(tz[4:]))
    elif tz.startswith("UTC+"):
        return "+{:04d}".format(int(tz[4:]))
    else:
        return "+0000"


def parse_args():
    parser = ArgumentParser(description="cli for ccfddl")
    parser.add_argument("--conf", type=str)
    parser.add_argument("--sub", type=str)
    parser.add_argument("--rank", type=str)
    return parser.parse_args()


def main():
    args = parse_args()

    yml_str = requests.get(
        "https://ccfddl.github.io/conference/allconf.yml").content.decode("utf-8")
    all_conf = yaml.safe_load(yml_str)

    all_conf_ext = []
    now = datetime.now(tz=timezone.utc)
    for conf in all_conf:
        for c in conf["confs"]:
            cur_conf = deepcopy(conf)
            cur_conf["title"] = cur_conf["title"] + str(c["year"])
            cur_conf.update(c)
            time_obj = None
            tz = parse_tz(c["timezone"])
            for d in c["timeline"]:
                try:
                    cur_d = datetime.strptime(
                        d["deadline"] + " {}".format(tz), '%Y-%m-%d %H:%M:%S %z')
                    if cur_d < now:
                        continue
                    if time_obj is None or cur_d < time_obj:
                        time_obj = cur_d
                except Exception as e:
                    pass
            if time_obj is not None:
                cur_conf["time_obj"] = time_obj
                if time_obj > now:
                    all_conf_ext.append(cur_conf)

    all_conf_ext = sorted(all_conf_ext, key=lambda x: x['time_obj'])

    table = [["title", "sub", "rank", "ddl", "link"]]
    for x in all_conf_ext:
        skip = False
        if args.conf and args.conf.lower() not in x["id"].lower():
            skip = True
        if args.sub and args.sub.lower() not in x["sub"].lower():
            skip = True
        if args.rank and args.rank.lower() not in x["rank"].lower():
            skip = True
        if not skip:
            table.append([x["title"], x["sub"], x["rank"],
                          str(x["time_obj"] - now), x["link"]])

    print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))


if __name__ == "__main__":
    main()
