import os
from reference_graph_construction.weighted_edge import *

# given a header file object, save its graph to a dot file
def save_graphs_as_dot(file_path, header_file, prefix_length=49):
    print("saving graph of {}".format(header_file.file_path))
    graph_name = header_file.file_path[prefix_length:].replace(":", "_").replace("/", "_").replace(".", "_") + ".dot"
    with open(os.path.join(file_path, graph_name), 'w') as f:
        f.write("digraph G {\n")
        # code elements
        for code_element in header_file.code_elements:
            try:
                f.write(code_element.name + "+" + code_element.type + ";\n")
            except:
                print(header_file.file_path)
                print(code_element.start, code_element.end)
                print(code_element.name)
                print(code_element.type)
        print("code elements: ", len(header_file.code_elements))
        # c files/ other h files
        for c_file in header_file.included_by:
            f.write(c_file + ";\n") # for dagP
        for h_file in header_file.include:
            if h_file in header_file.included_by:
                continue
            f.write(h_file + ";\n")
        print("included code files:", len(header_file.included_by))
        print("include code files:", len(header_file.include))
        # edges 
        edge_num = 0
        for code_element in header_file.code_elements:
            # kind 1: this code element --use--> other code element in the same file
            for other_code_element in code_element.reference:
                f.write(code_element.name + "+" + code_element.type + " -> " + other_code_element.name + "+" + other_code_element.type + ";\n")
                edge_num += 1
            # kind 2: this code element --include--> other h file
            for h_file in code_element.include:
                f.write(code_element.name + "+" + code_element.type + " -> " + h_file + ";\n")
                edge_num += 1
            # kind 3: c file --use--> this code element
            for c_file in code_element.referenced_by:
                f.write(c_file + " -> " + code_element.name + "+" + code_element.type + ";\n")
                edge_num += 1
            # kind 4: h file --use--> this code element
            for h_file in code_element.referenced_by_hce.keys():
                f.write(h_file + " -> " + code_element.name + "+" + code_element.type + ";\n")
                edge_num += 1
        print("edges: ", edge_num) 
        f.write("}\n")



def save_code_elements_location(file_path, header_file):
    graph_name = header_file.file_path.replace(":", "_").replace("\\", "_").replace(".", "_") + ".txt"
    with open(os.path.join(file_path, graph_name), 'w') as f:
        for code_element in header_file.code_elements:
            f.write(code_element.name + "+" + code_element.type + "\t" + str(code_element.start) + "\t" + str(code_element.end) + "\n")

