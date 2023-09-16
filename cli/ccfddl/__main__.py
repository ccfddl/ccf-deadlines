import string
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
    parser.add_argument("--conf", type=str, nargs='+', 
                        help="A list of conference ids you want to filter, e.g.: '--conf CVPR ICML'")
    parser.add_argument("--sub", type=str, nargs='+', 
                        help="A list of subcategories ids you want to filter, e.g.: '--sub AI CG'")
    parser.add_argument("--rank", type=str, nargs='+', 
                        help="A list of ranks you want to filter, e.g.: '--rank C N'")
    args = parser.parse_args()
    # Convert all arguments to lowercase
    for arg_name in vars(args):
        arg_value = getattr(args, arg_name)
        if arg_value:
            setattr(args, arg_name, [arg.lower() for arg in arg_value])
    return args


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

    # This is not an elegant solution. 
    # The purpose is to keep the above logic untouched, 
    # return alpha id(conf name) without digits(year)
    def alpha_id(with_digits:string) -> string:
        return ''.join(char for char in with_digits.lower() if char.isalpha())

    table = [["title", "sub", "rank", "ddl", "link"]]
    # Filter intersection by args
    for x in all_conf_ext:
        skip = False
        if args.conf and alpha_id(x["id"]) not in args.conf:
            skip = True
        if args.sub and x["sub"] not in args.sub:
            skip = True
        if args.rank and x["rank"] not in args.rank:
            skip = True
        if not skip:
            table.append(
                [x["title"], 
                 x["sub"], 
                 x["rank"],
                 str(x["time_obj"] - now), 
                 x["link"]]
                )

    print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))


if __name__ == "__main__":
    main()
