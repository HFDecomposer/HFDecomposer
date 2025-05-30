import os
import copy
from queue import Queue
import networkx as nx

from decomposition_plan_generation.circular_dependency_fixing.utils import *
from decomposition_plan_generation.utils import convert2nx_graph

# in_edges
def fixing_up(graph, cutting_edges, cluster):
    remove_nodes = []
    new_remove_nodes = Queue()
    for u, _ in cutting_edges:
        new_remove_nodes.put(u)
    while not new_remove_nodes.empty():
        node = new_remove_nodes.get()
        if node in remove_nodes:
            continue
        remove_nodes.append(node)
        for (i, _) in graph.in_edges(node):
            if i in cluster:
                new_remove_nodes.put(i)
    return remove_nodes

# out_edges
def fixing_down(graph, cutting_edges, cluster):
    remove_nodes = []
    new_remove_nodes = Queue()
    for _, v in cutting_edges:
        new_remove_nodes.put(v)
    while not new_remove_nodes.empty():
        node = new_remove_nodes.get()
        if node in remove_nodes:
            continue
        remove_nodes.append(node)
        for (_, o) in graph.out_edges(node):
            if o in cluster:
                new_remove_nodes.put(o)
    return remove_nodes

# based on dependency
def move_gain(graph, move_nodes, from_cluster, to_cluster):
    new_from_cluster = from_cluster.difference(set(move_nodes))
    move_gain = -len(move_nodes)
    for node in move_nodes:
        for (i, _) in graph.in_edges(node):
            if i in new_from_cluster:
                move_gain -= 1
            elif i in to_cluster:
                move_gain += 1
        for (_, o) in graph.out_edges(node):
            if o in new_from_cluster:
                move_gain -= 1
            elif o in to_cluster:
                move_gain += 1
    return move_gain


def distance(graph, move_nodes, cluster):
    result = 0
    for node in move_nodes:
        for (i, _) in graph.in_edges(node):
            if i in cluster:
                result += 1
        for (_, o) in graph.out_edges(node):
            if o in cluster:
                result += 1
    return result

def fixing_two_nodes(graph, partition, id1, id2):
    # print("fixing two:", id1, id2)

    cluster1 = partition[id1]
    cluster2 = partition[id2]

    # edges from 2 to 1
    cutting_edges_1 = []
    # edges from 1 to 2
    cutting_edges_2 = []

    for u, v in graph.edges():
        if u in cluster2 and v in cluster1:
            cutting_edges_1.append((u,v))
        elif u in cluster1 and v in cluster2:
            cutting_edges_2.append((u,v))

    if len(cutting_edges_1) == 0 or len(cutting_edges_2) == 0:
        print("no move: 0")
        return [cluster1, cluster2], 0, 0
    
    # print(cutting_edges_1)
    # print(cutting_edges_2)

    moving_result = []
    gain = []

    # case 1: remain cluster1 -> cluster2
    # case 1.1 node from 2 to 1
    moving_result.append(fixing_up(graph, cutting_edges_1, cluster2))
    gain.append(move_gain(graph, moving_result[0], cluster2, cluster1))
    # print("move from {} to {}:".format(id2, id1), moving_result[0])
    # print(gain[0])
    # case 1.2 node from 1 to 2
    moving_result.append(fixing_down(graph, cutting_edges_1, cluster1))
    gain.append(move_gain(graph, moving_result[1], cluster1, cluster2))
    # print("move from {} to {}:".format(id1, id2),moving_result[1])
    # print(gain[1])
    # case 2: remain cluster2 -> cluster1
    # case 2.1 node from 1 to 2
    moving_result.append(fixing_up(graph, cutting_edges_2, cluster1))
    gain.append(move_gain(graph, moving_result[2], cluster1, cluster2))
    # print("move from {} to {}:".format(id1, id2),moving_result[2])
    # print(gain[2])
    # case 2.2 node from 2 to 1
    moving_result.append(fixing_down(graph, cutting_edges_2, cluster2))
    gain.append(move_gain(graph, moving_result[3], cluster2, cluster1))
    # print("move from {} to {}:".format(id2, id1),moving_result[3])
    # print(gain[3])

    best_move = 0
    for i in range(1, 4):
        # if len(moving_result[i]) < len(moving_result[best_move]) or (len(moving_result[i]) == len(moving_result[best_move]) and gain[i] > gain[best_move]):
        if gain[i] > gain[best_move] or ( gain[i] == gain[best_move] and len(moving_result[i]) < len(moving_result[best_move])):
            best_move = i
    
    if best_move == 0 or best_move == 3:
        cluster2 = cluster2.difference(set(moving_result[best_move]))
        cluster1 = cluster1.union(set(moving_result[best_move]))
        # print("best move:", best_move, "move from {} to {}:".format(id2, id1), moving_result[best_move])
    else:
        cluster1 = cluster1.difference(set(moving_result[best_move]))
        cluster2 = cluster2.union(set(moving_result[best_move]))
        # print("best move:", best_move, "move from {} to {}:".format(id1, id2), moving_result[best_move])

    # print(len(cluster1), len(cluster2), len(moving_result[best_move]), gain[best_move])
    return [cluster1, cluster2], len(moving_result[best_move]), gain[best_move]


def reduce_three_to_two(graph, partition, id1, id2, id3):
    # print("order:", id1, id2, id3)
    ori_cluster1 = partition[id1]
    ori_cluster2 = partition[id2]
    ori_cluster3 = partition[id3]

    # (id1, (id2, id3))
    # 合并2和3，解开1与(2,3)之间的环
    partition[id2] = partition[id2].union(partition[id3])
    partition[id3] = set()
    cluster1, cluster23, steps_1, gain_1 = fixing_two_nodes(graph, partition, id1, id2)
    # 更新2，3的元素
    cluster2 = set()
    cluster3 = set()
    if len(cluster1) > len(ori_cluster1):
        cluster2 = ori_cluster2.intersection(cluster23)
        cluster3 = ori_cluster3.intersection(cluster23)
    else:
        move_nodes = ori_cluster1.difference(cluster1)
        # 看看多出来的节点放哪边
        pseudo_gain = move_gain(graph, move_nodes, cluster2, cluster3) + len(move_nodes)
        if pseudo_gain < 0 or (pseudo_gain == 0 and len(ori_cluster2) < len(ori_cluster3)):
            cluster2 = ori_cluster2.union(move_nodes)
            cluster3 = ori_cluster3
        else:
            cluster2 = ori_cluster2
            cluster3 = ori_cluster3.union(move_nodes)
    partition[id1] = cluster1
    partition[id2] = cluster2
    partition[id3] = cluster3
    cluster2, cluster3, steps_2, gain_2 = fixing_two_nodes(graph, partition, id2, id3)

    return cluster1, cluster2, cluster3, steps_1+steps_2, gain_1+gain_2



def fixing_three_nodes(graph, partition, id1, id2, id3):
    # print("fixing three:", id1, id2, id3)
    ori_cluster1 = partition[id1]
    ori_cluster2 = partition[id2]
    ori_cluster3 = partition[id3]
    # print("=====", len(ori_cluster1) + len(ori_cluster2) +len(ori_cluster3))

    results = []

    results.append(reduce_three_to_two(graph, partition, id1, id2, id3))
    partition[id1] = ori_cluster1
    partition[id2] = ori_cluster2
    partition[id3] = ori_cluster3
    results.append(reduce_three_to_two(graph, partition, id2, id1, id3))
    partition[id1] = ori_cluster1
    partition[id2] = ori_cluster2
    partition[id3] = ori_cluster3
    results.append(reduce_three_to_two(graph, partition, id3, id2, id1))

    best_result = max(results, key=lambda x: x[4])
    # print("=====", len(best_result[0]) + len(best_result[1]) +len(best_result[2]))

    return best_result[0], best_result[1], best_result[2], best_result[3]


def reduce_one_less_nodes(graph, partition, id1, node_ids):
    # print("order:", id1)

    ori_clusters = dict()
    ori_clusters[id1] = partition[id1]
    for id in node_ids:
        ori_clusters[id] = partition[id]
    
    for i in range(1, len(node_ids)):
        partition[node_ids[0]] = partition[node_ids[0]].union(partition[node_ids[i]])
        partition[node_ids[i]] = set()

    results_1, steps_1, gain_1 = fixing_two_nodes(graph, partition, id1, node_ids[0])

    partition[id1] = results_1[0]
    if len(partition[id1]) > len(ori_clusters[id1]):
        for id in node_ids:
            partition[id] = partition[id].intersection(results_1[1])
    else:
        move_nodes = ori_clusters[id1].difference(partition[id1])
        pseudo_gains = dict()
        for id in node_ids:
            pseudo_gains[id] = distance(graph, move_nodes, ori_clusters[id])
        max_id = max(pseudo_gains, key=pseudo_gains.get)
        for id in node_ids:
            if id == max_id:
                partition[id] = ori_clusters[id].union(move_nodes)
            else:
                partition[id] = ori_clusters[id]

    # results_2, steps_2, gain_2 = fixing_nodes(graph, partition, node_ids)

    # return results_1[0], results_2, steps_1+steps_2, gain_1+gain_2

    results_2 = [partition[id] for id in node_ids]
    # print(steps_1, gain_1)
    return results_1[0], results_2, steps_1, gain_1






def fixing_nodes(graph, partition, node_ids):
    # print("fixing more:", node_ids)
    if len(node_ids) == 2:
        return fixing_two_nodes(graph, partition, node_ids[0], node_ids[1])
    
    ori_clusters = dict()
    for id in node_ids:
        ori_clusters[id] = partition[id]

    results = []
    for i in range(len(node_ids)):
        new_node_ids = copy.deepcopy(node_ids)
        new_node_ids.pop(i)
        i_cluster, cluster_list, steps, gains = reduce_one_less_nodes(graph, partition, node_ids[i], new_node_ids)
        if i == len(node_ids):
            cluster_list.append(i_cluster)
        else:
            cluster_list.insert(i, i_cluster)
        results.append((cluster_list, steps, gains))

        for id in node_ids:
            partition[id] = ori_clusters[id]
    
    best_result = max(results, key=lambda x: x[2])

    return best_result[0], best_result[1], best_result[2]


def fixing_one_file(community_index, graph, subgraph):

    clusters_graph = my_quotient_graph(subgraph, community_index)
    print("quotient graph is DAG: ", nx.is_directed_acyclic_graph(clusters_graph))
    print(list(clusters_graph.edges()))
    cycles = list(nx.simple_cycles(clusters_graph))
    print("cycles:", cycles)
    print(len(cycles))

    round = 1
    new_community_index = community_index
    move_steps = 0
    

    while len(cycles) > 0:
        if round > 1000:
            break
        print("==================== round {} =======================".format(round))
        partition = convert_community_index_to_partition(new_community_index)

        max_len = max([len(cycle) for cycle in cycles])

        for cycle in cycles:
            if len(cycle) == max_len:
                results, step, gain = fixing_nodes(graph, partition, cycle)
                for k in range(len(cycle)):
                    partition[cycle[k]] = results[k]
                move_steps += step

        new_community_index = convert_partition_to_community_index(partition)
        clusters_graph = my_quotient_graph(subgraph, new_community_index)
        print("quotient graph is DAG: ", nx.is_directed_acyclic_graph(clusters_graph))
        print(list(clusters_graph.edges()))
        cycles = list(nx.simple_cycles(clusters_graph))
        print("cycles:", cycles)
        round += 1

    print("move_steps:", move_steps)
    print("\n")
    return new_community_index




def circular_dependency_fixing(target_header_file, community_index):
    print("Cyclic dependency fixing...")

    graph, code_elements, code_files = convert2nx_graph(target_header_file)
    
    subgraph = graph.subgraph(code_elements)
    community_index = fixing_one_file(community_index, graph, subgraph)
    new_community_index = {}
    for code_element in target_header_file.code_elements:
        new_community_index[code_element.name+"+"+code_element.type] = community_index[code_element.name]

    return new_community_index
