import os, json
import pandas as pd
import math
import gurobipy as gp
from gurobipy import GRB
from collections import defaultdict

def parse_demands():
    excel_data = pd.read_excel(r'FBWMLocationsDemands.xlsx')
    extra_nodes_idx = 137
    ref_to_nodes_idx = defaultdict(list)
    pallets_demands = {0: 0}
    idx_to_ref = {}
    idx_to_ref[0] = 0
    for idx in range(1, 137):
        # 0: Ref number, 1: Name, 6: Number of pallets, 7: monthly demands
        ref, num_pals, freq = excel_data.iloc[idx][0], excel_data.iloc[idx][6], excel_data.iloc[idx][7]
        if type(freq) == float and math.isnan(freq):
            num_times = 1
        elif freq.lower() == "weekly":
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
        nodes = []
        for i in range(num_times):
            if type(num_pals) == list:
                cur_demand = num_pals[0]
                num_pals.pop(0)
            else:
                cur_demand = num_pals

            if i == 0:
                pallets_demands[idx] = cur_demand
                idx_to_ref[idx] = idx
            elif i > 0:
                pallets_demands[extra_nodes_idx] = cur_demand
                idx_to_ref[extra_nodes_idx] = idx
                extra_nodes_idx += 1  
    return pallets_demands, idx_to_ref

class DataModel:
    def __init__(self):
        # How load a json file as python object
        # variable_name = json.load(open("/path/to/your/file", "r"))
        self._locations = json.load(open(os.path.abspath("./locations.json"), "r"))

        # Distance Matrix
        # 136x136 Matrix - Distances stored as Meters
        self._distances = json.load(open(os.path.abspath("./distances_matrix.json"), "r"))
        #Travel Times Matrix
        # 136x136 Matrix - Time travelled stored as Seconds
        self._travel_times = json.load(open(os.path.abspath("./travel_times_matrix.json"), "r"))
            
        # Demands
        # A list for demand of node at index i
        pallet_demands, idx_to_ref = parse_demands()
        self._demands = pallet_demands
        # A dictionary to map idx to its ref_number. This will allow us to identify pseudo-nodes that were created to represent demands over a month.
        self._idx_to_ref = idx_to_ref

    def _set_travel_matrix(self, travel_time_matrix):
        self._travel_times = travel_time_matrix
        
def run(data):
    # data = DataModel()
    m = gp.Model()
    # Preset the truck's capacity to 9
    Q = 9

    num_of_nodes = len(data._demands)

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
            # If j references the same node, we shouldn't include this edge.
            if i == j or (data._idx_to_ref[j] == data._idx_to_ref[i]): 
                continue
            cur_sum_enters += x[i, j]
        m.addConstr(cur_sum_enters == 1)

    for j in range(1, num_of_nodes):
        cur_sum_leaves = 0
        for i in range(num_of_nodes):
            # If j references the same node, we shouldn't include this edge.
            if i == j or (data._idx_to_ref[j] == data._idx_to_ref[i]): continue
            cur_sum_leaves += x[i, j]
        m.addConstr(cur_sum_leaves == 1)

    for i in range(1, num_of_nodes):
        for j in range(1, num_of_nodes):
            if i == j: continue
            get_demand = data._demands[j]
            m.addConstr(u[i] - u[j] + Q * x[i,j] <= Q - data._demands[j])

    for i in range(1, num_of_nodes):
        m.addConstr(data._demands[i] <= u[i])
        m.addConstr(u[i] <= Q)

    cumul_sum = 0
    for i in range(num_of_nodes):
        for j in range(num_of_nodes):
            ref_num = data._idx_to_ref[i]
            dest_ref_num = data._idx_to_ref[j]
            if ref_num == dest_ref_num:
                travel_time = 0
            else:
                travel_time = data._travel_times[ref_num][dest_ref_num]
            cumul_sum += travel_time * x[i,j]

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
    data = DataModel()
    run(data)