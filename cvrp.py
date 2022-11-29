import os, json
import pandas as pd
import math
import gurobipy as gp
from gurobipy import GRB
from collections import defaultdict

def parse_demands():
    # demands are represented by dict where key is the ref number. the number of demands in the list
    # represents how many times it needs to be delivered each month, and how many pallets in each turn.
    excel_data = pd.read_excel(r'FBWMLocationsDemands.xlsx')
    pallets_demands = defaultdict(list)
    for idx in range(1, 137):
        # 0: Ref number, 1: Name, 6: Number of pallets, 7: monthly demands
        ref, num_pals, freq = excel_data.iloc[idx][0], excel_data.iloc[idx][6], excel_data.iloc[idx][7]
        if type(freq) == float and math.isnan(freq):
            num_times = 1
        elif freq.lower() == "weekly":
            # 4 times a month
            num_times = 4
        elif freq.lower() == "twice a month":
            num_times = 2

        if num_pals == "1 to 2":
            num_pals = 2
        elif num_pals == "6 to 9":
            num_pals = 9
        elif num_pals == "2 (one time) 1 (the other time)":
            num_pals = [2, 1]
        else:
            num_pals = num_pals

        for i in range(num_times):
            if type(num_pals) == list:
                pallets_demands[ref].append(num_pals[0])
                num_pals.pop(0)
            else:
                pallets_demands[ref].append(num_pals)

    return pallets_demands

def create_data_model():
    # HOW TO load a json file as python object
    # variable_name = json.load(open("/path/to/your/file", "r"))
    _locations = json.load(open(os.path.abspath("./locations.json"), "r"))

    # Distance Matrix
    # 136x136 Matrix - Distances stored as Meters
    _distances = json.load(open(os.path.abspath("./distances_matrix.json"), "r"))

    #Travel Times Matrix
    # 136x136 Matrix - Time travelled stored as Seconds
    _travel_times = json.load(open(os.path.abspath("./travel_times_matrix.json"), "r"))

    #Demands
    #Dict containing node i and n_th constraints representing times it in a month
    _demands = parse_demands()
