import numpy as np
import networkx as nx
from code_element_graph_construction.weighted_edge import *


def convert_community_index_to_name_partition(header_file, community_index):
    index_partition = []
    if len(community_index) == 0:
        return index_partition
    for i in range(max(community_index.values())+1):
        index_partition.append([])
    for i in range(0, len(header_file.code_elements)):
        ce = header_file.code_elements[i]
        name = ce.name +'+'+ ce.type
        if name in community_index.keys():
            index_partition[community_index[name]].append(name)
    return index_partition

def compute_modularity(header_file, community_index, adj_type):
    adj_matrix = None

    if adj_type == 'dependency':
        adj_matrix = normalized_dependency(header_file)
    elif adj_type == 'cousage':
        adj_matrix = shared_usage_for_file(header_file)
    elif adj_type == 'semantic':
        adj_matrix = semantic_similarity_for_file(header_file)
    elif adj_type == 'all':
        adj_matrix = normalized_dependency(header_file) + shared_usage_for_file(header_file) + semantic_similarity_for_file(header_file)
    else:
        return 0

    G = nx.Graph()
    nodes = [ce.name +'+'+ce.type for ce in header_file.code_elements]
    edges = []
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            edges.append((nodes[i], nodes[j], adj_matrix[i,j]))
    G.add_nodes_from(nodes)
    G.add_weighted_edges_from(edges)
    
    communities = convert_community_index_to_name_partition(header_file, community_index)

    modularity = nx.community.modularity(G, communities)
    
    return modularity

def simplify_community_index(community_index):
    if len(community_index) == 0:
        return community_index
    max_index = max(community_index.values())
    new_community_index = {}
    new_index = {}
    count = {}
    for i in range(max_index+1):
        count[i] = 0
    for key, value in community_index.items():
        count[value] += 1
    current_index = 0
    for i in range(max_index+1):
        if count[i] > 0:
            new_index[i] = current_index
            current_index += 1
    for key, value in community_index.items():
        new_community_index[key] = new_index[value]
    return new_community_index


def convert2nx_graph(target_header_file):
    code_elements = []
    code_files = []
    graph = nx.DiGraph()
    for code_element in target_header_file.code_elements:
        code_elements.append(code_element.name + '+' + code_element.type)
    graph.add_nodes_from(code_elements)
    for file in target_header_file.included_by:
        code_files.append(file)
    graph.add_nodes_from(code_files)
    edges = []
    for code_element in target_header_file.code_elements:
        for other_code_element in code_element.reference:
            if other_code_element.name + '+' + other_code_element.type in code_elements:
                edges.append((code_element.name + '+' + code_element.type, other_code_element.name + '+' + other_code_element.type))
        for c_file in code_element.referenced_by:
            if c_file in code_files:
                edges.append((c_file, code_element.name + '+' + code_element.type))
        for h_file in code_element.referenced_by_hce.keys():
            if h_file in code_files:
                edges.append((h_file, code_element.name + '+' + code_element.type))
    graph.add_edges_from(edges)
    return graph, code_elements, code_files