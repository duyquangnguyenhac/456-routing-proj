import os, json
import pandas as pd
import math
import gurobipy as gp
from gurobipy import GRB
from collections import defaultdict

_locations, _distances, _travel_times, _demands = None, None, None, None

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
class DataModel:
    def __init__(self):
        # HOW TO load a json file as python object
        # variable_name = json.load(open("/path/to/your/file", "r"))
        self._locations = json.load(open(os.path.abspath("./locations.json"), "r"))

        # Distance Matrix
        # 136x136 Matrix - Distances stored as Meters
        self._distances = json.load(open(os.path.abspath("./distances_matrix.json"), "r"))
        #Travel Times Matrix
        # 136x136 Matrix - Time travelled stored as Seconds
        self._travel_times = json.load(open(os.path.abspath("./travel_times_matrix.json"), "r"))
            
        #Demands
        #Dict containing node i and n_th constraints representing times it in a month
        self._demands = parse_demands()
        self._demands = [0, 4, 4, 6]

    def _set_travel_matrix(self, travel_time_matrix):
        self._travel_times = travel_time_matrix
        
def run(data):
    # data = DataModel()
    m = gp.Model()
    num_of_nodes = 4
    Q = 8
    # for i in range(3):
    #     monthly_demands = len(data._demands[i])
    #     num_of_nodes += monthly_demands

    x = m.addMVar((num_of_nodes, num_of_nodes), vtype=GRB.INTEGER, lb=0, name="x")
    K = m.addVar(vtype=GRB.INTEGER, lb=0, name="K")
    u = m.addVars(num_of_nodes, vtype=GRB.INTEGER, lb = 0, name="u")

    cur_sum = 0
    for j in range(1, num_of_nodes):
        cur_sum += x[0, j]

    m.addConstr(cur_sum == K)

    for i in range(1, num_of_nodes):
        cur_sum_enters = 0
        m.addConstr(x[i,i] == 0)
        for j in range(num_of_nodes):
            if i == j or data._distances[i][j] == 0: 
                continue
            cur_sum_enters += x[i, j]
        m.addConstr(cur_sum_enters == 1)

    for j in range(1, num_of_nodes):
        cur_sum = 0
        for i in range(num_of_nodes):
            if i == j or data._distances[i][j] == 0: continue
            cur_sum += x[i, j]
        m.addConstr(cur_sum == 1)

    for i in range(1, num_of_nodes):
        for j in range(1, num_of_nodes):
            if i == j: continue
            m.addConstr(u[i] - u[j] + Q * x[i,j] <= Q - data._demands[j])

    for i in range(1, num_of_nodes):
        m.addConstr(data._demands[i] <= u[i])
        m.addConstr(u[i] <= Q)

    # for i in range(num_of_nodes):
    #     for j in range(num_of_nodes):
    #         m.addConstr((x[i,j] == 0) >> data._distances[i][j] * x[i,j] >= 0)

    cumul_sum = 0
    for i in range(num_of_nodes):
        for j in range(num_of_nodes):
            cumul_sum += data._travel_times[i][j] * x[i,j]

    m.setObjective(cumul_sum, GRB.MINIMIZE)
    m.optimize()

    for v in m.getVars():
        if (v.varName.find('x') != -1) and v.x == 1:
            idx = v.varName.find("[") + 1
            end_idx = len(v.varName) - 1
            num = v.varName[idx:end_idx]
            i_row = int(num) // num_of_nodes
            j_row = int(num) % num_of_nodes
            print(f"x({i_row}, {j_row})", 1)
        if (v.varName.find('K') != -1):
            print(v.varName, "=", v.x)
        
if __name__ == "__main__":
    print("BEGIN TESTS =>")
    # Test Case 1
    data = DataModel()
    # Depot on the Side
    travel_times = [[0, 4, 7, 7], [4, 0, 3, 3], [7, 3, 0, 0], [7, 3, 0, 0]]
    data._set_travel_matrix(travel_times)
    run(data)

    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    # Test Case 2
    # Depot in the middle
    travel_times = [[0, 4, 3, 3], [4, 0, 7, 7], [3, 7, 0, 0], [3, 7, 0, 0]]
    data._set_travel_matrix(travel_times)
    run(data)

    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    # Test Case 3 
    # Depot in the middle shifted down a little 
    travel_times = [[0, 4, 3, 3], [4, 0, 6, 6], [3, 6, 0, 0], [3, 6, 0, 0]]
    data._set_travel_matrix(travel_times)
    run(data)

    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    # Test Case 4
    # Depot in the middle shifted down a little 
    travel_times = [[0, 4, 3, 3], [4, 0, 6, 6], [3, 6.5, 0, 0], [3, 6.5, 0, 0]]
    data._set_travel_matrix(travel_times)
    run(data)
