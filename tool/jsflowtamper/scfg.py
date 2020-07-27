import networkx as nx
from draw_cfg import draw_cfg
import equip_graph
import json

class SimplifiedCFG:

    def __init__(self):
        self.graph = nx.DiGraph()
        self.function_name = None
        self.fuid = None
        self.script_id = None
        self.function_id = None
        self.source_url = None
        self.trace_calls = None
        self.sbbs = None
        self.json_data = None
        self.cd_graph = None

    def load_from_json(self, data):
        try:
            data = json.loads(data)
        except ValueError:
            return False
        self.function_name = data["function_name"]
        self.fuid = data["fuid"]
        self.script_id = data["script_id"]
        self.function_id = data["function_id"]
        self.source_url = data["source_url"]
        self.trace_calls = data["trace_calls"]
        self.sbbs = data["sbbs"]
        self.json_data = data

        self.construct_graph()
        self.cal_dependency()

        return True

    def construct_graph(self):
        for sbb in self.sbbs:
            id = sbb['id']
            self.graph.add_node(id)

            for i, succ in enumerate(sbb['successors']):
                self.graph.add_edge(id, succ)
                self.graph[id][succ]['branch_index'] = i

    def draw(self):
        draw_cfg(self.json_data)

    def draw_with_cd(self, sbb_id, cds):
        draw_cfg(self.json_data, sbb_id, cds)

    def cal_dependency(self):
        # wrapper for equip graph
        g = equip_graph.DiGraph()
        nodes = {}
        node_list = []
        for sbb in self.sbbs:
            id = sbb['id']
            node = g.make_add_node(data=id)
            nodes[id] = node
            node_list.append(node)

        for sbb in self.sbbs:
            id = sbb['id']
            for succ in sbb['successors']:
                g.make_add_edge(nodes[id], nodes[succ])

        class EQUIP_CFG:
            graph = None
            entry_node = None
            exit_node = None
            dominators = None

        equip_cfg = EQUIP_CFG()
        equip_cfg.graph = g
        equip_cfg.entry_node = node_list[0]
        equip_cfg.exit_node = node_list[-1]
        equip_cfg.dominators = equip_graph.DominatorTree(equip_cfg)
        self.cd_graph = equip_graph.ControlDependence(equip_cfg).graph

    def get_cd(self, sbb_id):
        # find this node from cd graph
        nodes = list(self.cd_graph.nodes)
        cur_node = None
        for node in nodes:
            if node.data == sbb_id:
                cur_node = node
                break

        if cur_node == None:
            return []

        cd_nodes = []
        while True:
            in_edges = self.cd_graph.in_edges(cur_node)
            if len(in_edges) == 0:
                break
            pred = in_edges[0].source
            cd_nodes.append(pred.data)
            cur_node = pred

        return cd_nodes

    def get_sbb_index(self, sbb_id):
        for i, sbb in enumerate(self.sbbs):
            if sbb['id'] == sbb_id:
                return i

        return None

    def get_sbb(self, sbb_id):
        for i, sbb in enumerate(self.sbbs):
            if sbb['id'] == sbb_id:
                return sbb

        return None

    def get_stmt_index(self, sbb, offset):
        if sbb is None:
            return None

        for i, stmt in enumerate(sbb['statements']):
            if stmt['position'] == offset:
                return i

        return None

    def get_connected_edge(self, start_id, end_id):
        for succ in self.graph[start_id]:
            if nx.has_path(self.graph, succ, end_id):
                return self.graph[start_id][succ]['branch_index']

        return None












