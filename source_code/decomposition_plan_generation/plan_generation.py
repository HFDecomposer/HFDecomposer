import networkx as nx
import networkx.algorithms.community as nx_comm
from code_element_graph_construction.weighted_edge import *
# from decomposition_plan_generation.graph_coarsening.graph_coarsening import graph_coarsening
# from decomposition_plan_generation.multi_view_graph_clustering.DuaLGR import DuaLGR_main
# from decomposition_plan_generation.circular_dependency_fixing.utils import convert_community_index_to_partition
from decomposition_plan_generation.utils import convert2nx_graph, compute_modularity
from refactoring_implementation.utils import generate_quotient_graph

# def decomposing_through_DuaLGR(parts, target_header_file):
#     print("Decomposing through DuaLGR...")
#     blocks, bundled_usage, bundled_semantic, original_weights =  graph_coarsening(target_header_file)
#     cluster_id = DuaLGR_main(parts, len(target_header_file.code_elements), blocks, bundled_usage, bundled_semantic, original_weights)

#     community_index = {}
#     for i in range(len(cluster_id)):
#         ce = target_header_file.code_elements[i]
#         community_index[ce.name + '+' + ce.type] = cluster_id[i]
#     return community_index


def CDM(header_file):
    length = len(header_file.code_elements)
    dependency = call_based_dependency_for_file(header_file)
    cdm = np.zeros((length, length))
    for i in range(length):
        for j in range(i+1, length):

            isum = np.sum(dependency[:,i])
            jsum = np.sum(dependency[:,j])
            wi = 0
            wj = 0
            if isum > 0:
                wi = dependency[j,i] / isum
            if jsum > 0:
                wj = dependency[i,j] / jsum
            cdm[i, j] = max(wi, wj)
            cdm[j, i] = max(wi, wj)
    return cdm

def position_dividing(community_index,position_list):
    last_index = community_index[f'{position_list[0].name}+{position_list[0].type}']
    new_index_now = 0
    for element in position_list:
        if community_index[f'{element.name}+{element.type}'] == last_index:
            community_index[f'{element.name}+{element.type}'] = new_index_now
        else:
            new_index_now += 1
            last_index = community_index[f'{element.name}+{element.type}']
            community_index[f'{element.name}+{element.type}'] = new_index_now
    return community_index



def decomposing_through_Louvain(target_header_file):
    print("Decomposing through Louvain...")
    resolution = 1
    saw = shared_dependency(target_header_file)
    miw = CDM(target_header_file)
    fcw = functional_coupling_for_file(target_header_file)
    ssw = LSI_similarity_for_file(target_header_file)
    th1 = np.median(ssw)
    ssw[ssw<th1] = 0
    matrix = 0.5*saw + 0.2*miw + 0.2*fcw + 0.1*ssw
    # matrix = 0.5*saw + 0.2*miw + 0.3*fcw

    graph = nx.Graph()
    for i in range(matrix.shape[0]):
        graph.add_node(i)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if matrix[i][j] > 0:
                graph.add_edge(i, j, weight=matrix[i][j])

    partition = nx_comm.louvain_communities(graph)
    print("before position division:")
    # print("resolution: ", resolution)
    print("parts: ", len(partition))

    community_index = {}
    for i, n in enumerate(partition):
        for j in n:
            ce = target_header_file.code_elements[j]
            community_index[ce.name + '+' + ce.type] = i

    position_list = sorted(target_header_file.code_elements,key=lambda x: (x.start[0], x.start[1]))
    community_index = position_dividing(community_index,position_list)
    print("after position division:")
    print("parts:", int(max(community_index.values()))+1)

    return community_index

def decomposing_through_Louvain_no_semantic(target_header_file):
    print("Decomposing through Louvain...")
    resolution = 1
    saw = shared_dependency(target_header_file)
    miw = CDM(target_header_file)
    fcw = functional_coupling_for_file(target_header_file)
    matrix = 0.5*saw + 0.2*miw + 0.3*fcw

    graph = nx.Graph()
    for i in range(matrix.shape[0]):
        graph.add_node(i)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if matrix[i][j] > 0:
                graph.add_edge(i, j, weight=matrix[i][j])

    partition = nx_comm.louvain_communities(graph)
    print("before position division:")
    print("parts: ", len(partition))

    community_index = {}
    for i, n in enumerate(partition):
        for j in n:
            ce = target_header_file.code_elements[j]
            community_index[ce.name + '+' + ce.type] = i

    position_list = sorted(target_header_file.code_elements,key=lambda x: (x.start[0], x.start[1]))
    community_index = position_dividing(community_index,position_list)
    print("after position division:")
    print("parts:", int(max(community_index.values()))+1)

    return community_index

def decomposing_through_Louvain_no_co_usage(target_header_file,parts):
    print("Decomposing through Louvain...")
    resolution = 1
    miw = CDM(target_header_file)
    fcw = functional_coupling_for_file(target_header_file)
    ssw = LSI_similarity_for_file(target_header_file)
    th1 = np.median(ssw)
    ssw[ssw<th1] = 0
    matrix = 0.4*miw + 0.4*fcw + 0.2*ssw

    graph = nx.Graph()
    for i in range(matrix.shape[0]):
        graph.add_node(i)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if matrix[i][j] > 0:
                graph.add_edge(i, j, weight=matrix[i][j])
    
    partition = []
    step = 0.2
    flag = 0
    while True:
        partition = nx_comm.louvain_communities(graph, resolution=resolution)
        print("resolution: ", resolution)
        print("parts: ", len(partition))
        if len(partition) == parts:
            break
        if len(partition) < parts:
            if flag == 1:
                step = step / 2
            flag = -1
            resolution = resolution + step
        else:
            if flag == -1:
                step = step / 2
            flag = 1
            resolution = resolution - step

    # partition = nx_comm.louvain_communities(graph)
    print("resolution: ", resolution)
    print("parts: ", len(partition))

    community_index = {}
    for i, n in enumerate(partition):
        for j in n:
            ce = target_header_file.code_elements[j]
            community_index[ce.name + '+' + ce.type] = i
    return community_index

def plan_overview(target_header_file, community_index, file_names):
    graph_str = ""
    graph, code_elements, code_files = convert2nx_graph(target_header_file)
    quotient_graph = generate_quotient_graph(community_index, graph.subgraph(code_elements))
    
    new_partition = {}
    for i in range(len(file_names)):
        new_partition[file_names[i]] = list()
    for ce in target_header_file.code_elements:
        key = ce.name + '+' + ce.type
        new_partition[file_names[community_index[key]]].append(key)

    graph_str += "digraph G {\n\tgraph[size=\"6,4!\"\nratio=0.575;];\n\trankdir=BT;\n"
    for node in quotient_graph.nodes():
        graph_str += "\t{}[label=\"{}\\n(size:{})\"];\n".format(node, file_names[node], len(new_partition[file_names[node]]))
    for edge in quotient_graph.edges():
        graph_str += "\t{} -> {};\n".format(edge[0], edge[1])
    graph_str += "}"

    modularity = compute_modularity(target_header_file, community_index, 'all')

    return_json = {
        "graph_str": graph_str,
        "modularity": modularity
    }

    
    return_json["partition"] = new_partition

    return return_json