import re
import yaml
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from itertools import combinations


def load_mapping(path: str = "conference/types.yml") -> dict:
    with open(path, encoding="utf-8") as f:
        types = yaml.safe_load(f)
    sub_mapping = {}
    for types_data in types:
        sub_mapping[types_data["sub"]] = types_data["name"]
    return sub_mapping


def get_timezone(tz_str: str) -> timezone:
    if tz_str == "AoE":
        return timezone(timedelta(hours=-12))
    if tz_str == "UTC":
        return timezone.utc
    match = re.match(r"UTC([+-])(\d{1,2})$", tz_str)
    if not match:
        raise ValueError(f"Invalid timezone format: {tz_str}")
    sign, hours = match.groups()
    offset = int(hours) if sign == "+" else -int(hours)
    return timezone(timedelta(hours=offset))


def reverse_index(file_paths: list[str], subs: list[str]) -> dict[str, list[str]]:
    index = defaultdict(set)

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

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

            _add_index_entry(index, sub, file_path)

            for size in range(1, len(rank_keys) + 1):
                for combo in combinations(rank_keys, size):
                    key = "_".join(combo)
                    _add_index_entry(index, key, file_path)
                    _add_index_entry(index, f"{key}_{sub}", file_path)

    return {key: sorted(paths) for key, paths in index.items()}


def _add_index_entry(index: dict, key: str, file_path: str) -> None:
    index[key].add(file_path)