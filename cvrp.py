from functools import partial
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import os, json
import pandas as pd
import math
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

    _demands = parse_demands()

def manhattan_distance(position_1, position_2):
    """Computes the Manhattan distance between two points"""
    return (
        abs(position_1[0] - position_2[0]) + abs(position_1[1] - position_2[1]))

def create_distance_evaluator(data):
    """Creates callback to return distance between points."""
    _distances = {}
    # precompute distance between location to have distance callback in O(1)
    for from_node in range(data['num_locations']):
        _distances[from_node] = {}
        for to_node in range(data['num_locations']):
            if from_node == to_node:
                _distances[from_node][to_node] = 0
            else:
                _distances[from_node][to_node] = (manhattan_distance(
                    data['locations'][from_node], data['locations'][to_node]))

    def distance_evaluator(manager, from_node, to_node):
        """Returns the manhattan distance between the two nodes"""
        return _distances[manager.IndexToNode(from_node)][manager.IndexToNode(
            to_node)]

    return distance_evaluator

def distance_evaluator(from_node, to_node):
    return _distances[from_node][to_node]

def create_demand_evaluator(data):
    """Creates callback to get demands at each location."""
    _demands = data['demands']

    def demand_evaluator(manager, node):
        """Returns the demand of the current node"""
        return _demands[manager.IndexToNode(node)]

    return demand_evaluator

parse_demands()