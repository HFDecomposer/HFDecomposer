import os
import networkx as nx

def generate_quotient_graph(community_index, graph):
    quotient_graph = nx.DiGraph()
    quotient_graph.add_nodes_from(community_index.values())
    # generate quotient graph without self-loop
    for edge in graph.edges():
        if community_index[edge[0]] != community_index[edge[1]]:
            quotient_graph.add_edge(community_index[edge[0]], community_index[edge[1]])
    return quotient_graph


def toporlogical_processing_order(quotient_graph):
    return list(nx.topological_sort(quotient_graph))



def code_element_count_in_range(code_element_list, start_point, end_ponit):
    count = 0
    for code_element in code_element_list:
        if code_element.start >= start_point and code_element.end <= end_ponit:
            count += 1
    return count

def code_elements_in_range(code_element_list, start_point, end_ponit):
    code_elements = []
    for code_element in code_element_list:
        if code_element.start >= start_point and code_element.end <= end_ponit:
            code_elements.append(code_element)
    return code_elements


# 整行copy
def string_content(original_string_list, start_point, end_point):
    if start_point[0] == end_point[0]:
        return original_string_list[start_point[0]]
    else:
        content = original_string_list[start_point[0]]
        for i in range(start_point[0]+1, end_point[0]):
            content += original_string_list[i]
        if end_point[1] != 0:
            content += original_string_list[end_point[0]]
        return content
   
#comment copy 
def comment_content(original_string_list, start_point, end_point):
    first_line = original_string_list[start_point[0]]
    if start_point[0] == end_point[0] :
        return first_line[start_point[1]:end_point[1]]
    else:
        content = first_line[start_point[1]:]
        for i in range(start_point[0]+1, end_point[0]):
            content += original_string_list[i]
        if end_point[1] != 0:
            end_line = original_string_list[end_point[0]]
            content += end_line[:end_point[1]]
        return content