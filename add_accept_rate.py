
import os
from ruamel.yaml import YAML
yaml = YAML()
import sys

import json
with open('dict_list.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

data_conf = {}
for item in data:
    # accept_rate = {
    #     "year": item["year"],
    #     "submitted": item["Submitted"],
    #     "accepted": item["Accepted"],
    #     "str":item["str"],
    #     "rate":item["acceptance_rates"],
    #     "source":item["source"]

    # }
    data_conf[item["conference"]] = item

def read_name(yaml_file):
    with open(yaml_file, 'r', encoding='utf-8') as file:
        print(yaml_file)
        data = yaml.load(file)
    return data[0]['title']

def add_accept_rate(yaml_file,item):
    with open(yaml_file, 'r', encoding='utf-8') as file:
        data = yaml.load(file)
    
    data[0]['accept_rate'] = [item]
    
    with open(yaml_file, 'w') as file:
        yaml.dump(data, file)

file_dict = {}
for root, dirs, files in os.walk("conference"):
    for file in files:
        if file.endswith(".yml") and not file.endswith("types.yml"):
            yaml_file = os.path.join(root, file)
            name = read_name(yaml_file)
            file_dict[name] = yaml_file

for data_key in data_conf:
    if data_key in file_dict:
        data_value = data_conf[data_key]
        accept_rate = {
        "year": data_value["year"],
        "submitted": data_value["Submitted"],
        "accepted": data_value["Accepted"],
        "str":data_value["str"],
        "rate":data_value["acceptance_rates"]
    }
        add_accept_rate(file_dict[data_key],accept_rate)
        print(file_dict[data_key])
    # sys.exit()


