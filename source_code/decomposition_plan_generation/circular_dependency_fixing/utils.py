import networkx as nx
import json


def convert_community_index_to_partition(community_index: dict) -> dict:
    partition = dict()
    for node, community in community_index.items():
        if community not in partition:
            partition[community] = set()
        partition[community].add(node)
    return partition

def convert_partition_to_community_index(partition: dict) -> dict:
    community_index = dict()
    for i, community in partition.items():
        for node in community:
            community_index[node] = i
    return community_index

def my_quotient_graph(graph, community_index):
    quotient_graph = nx.DiGraph()
    edges = set()
    for u, v in graph.edges():
        try:
            if community_index[u] != community_index[v]:
                edges.add((community_index[u], community_index[v]))
        except:
            continue
    edges = list(edges)
    quotient_graph.add_edges_from(edges)
    return quotient_graph


def save_community_index_to_json(community_index, file_path):
    with open(file_path, 'w') as f:
        json.dump(community_index, f)

