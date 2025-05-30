import json
import sys
import os

from tree_sitter import Language, Parser
import tree_sitter_c as tsc

from refactoring_implementation.utils import *

# dfs a parse tree, return the first node whose type is preproc_ifdef
def find_first_ifdef(node):
    if node.type == "preproc_ifdef":
        return node
    else:
        for child in node.children:
            res = find_first_ifdef(child)
            if res is not None:
                return res
        return None
    

def write_file_content(original_code_content, target_header_file, community_index, sub_header_files, graph):

    buffer = "" # save comment lines
    environment_stack = list() # save environment
    subfile_environment = list()
    for i in range(len(sub_header_files)):
        subfile_environment.append(0)
    last_handle = -1

    def write_node(start_point, end_point):
        nonlocal last_handle
        nonlocal buffer

        code_elements = code_elements_in_range(target_header_file.code_elements, start_point, end_point)

        handle = None
        
        if len(code_elements) == 1:
            handle = community_index[code_elements[0].name + "+" + code_elements[0].type]
        else:
            affiliated_subfiles = dict()
            for code_element in code_elements:
                index = community_index[code_element.name + "+" + code_element.type]
                if index not in affiliated_subfiles:
                    affiliated_subfiles[index] = 1
                else:
                    affiliated_subfiles[index] += 1
            handle = max(affiliated_subfiles, key=affiliated_subfiles.get)
        
        if not handle == last_handle:
            sub_header_files[handle].write("\n")

        # ifdef environment
        if subfile_environment[handle] < len(environment_stack) - 1:
            for i in range(subfile_environment[handle]+1, len(environment_stack)):
                sub_header_files[handle].write(environment_stack[i])
            subfile_environment[handle] = len(environment_stack) - 1

        # print(code_elements[0].name, start_point, end_point, community_index[code_elements[0].name + "+" + code_elements[0].type])

        sub_header_files[handle].write(buffer)
        buffer = ""
        sub_header_files[handle].write(comment_content(original_code_content, start_point, end_point))
        sub_header_files[handle].write("\n")
        last_handle = handle

        return

    # TODO:        
    def add_include(include_node):
        include_content = string_content(original_code_content, include_node.start_point, include_node.end_point)
        for i in range(int(max(community_index.values()))+1):
            sub_header_files[i].write(include_content)
        # if include_content.find("<") >= 0:
        #     for i in range(max(community_index.values())+1):
        #         sub_header_files[i].write(include_content)
        # else:
        #     file_name = include_content[include_content.find("\"")+1:include_content.rfind("\"")]
        #     file_node = None
        #     for node in graph.nodes():
        #         if node.endswith('/'+file_name):
        #             file_node = node
        #             break
        #     if file_node is None:
        #         print("Error: no such file", file_name)
        #         return
        #     handle_set = set()
        #     for edge in graph.in_edges(file_node):
        #         handle_set.add(community_index[edge[0]])
        #     for handle in handle_set:
        #         sub_header_files[handle].write(include_content)
        return


    def dfs_parse_tree(node):
        nonlocal buffer
        
        if node.type == "translation_unit":
            for child in node.children:
                dfs_parse_tree(child)
            return
        
        if node.type == "comment":
            buffer += comment_content(original_code_content, node.start_point, node.end_point)
            buffer += '\n'
            return 
        # TODO: 也许可以优化？
        elif node.type == "preproc_include":
            add_include(node)
            return
    
        ce_cnt = code_element_count_in_range(target_header_file.code_elements, node.start_point, node.end_point)

        # TODO: include stmt under ifdef
        if ce_cnt == 0:
            if node.type == "preproc_ifdef" or node.type == "preproc_if" :
                include_stmt = False
                call_stmt = False
                for child in node.children:
                    if child.type == "preproc_include":
                        include_stmt =True
                    if child.type == "preproc_call":
                        call_stmt =True
                if include_stmt:
                    add_include(node)
                    return
                if call_stmt:
                    buffer += string_content(original_code_content, node.start_point, node.end_point)
                    buffer += '\n'
                    return
            elif node.type == "expression_statement" or node.type == "preproc_call" :
                print("copy", node.start_point, node.end_point)
                sub_header_files[last_handle].write(comment_content(original_code_content, node.start_point, node.end_point))
                return
            elif node.type == "declaration":
                buffer += comment_content(original_code_content, node.start_point, node.end_point)
                buffer += " "
                return
            elif(comment_content(original_code_content, node.start_point, node.end_point)==';'):
                sub_header_files[last_handle].write(';\n')
                return
            print("Error: no code element in range", node.start_point, node.end_point)
            return

        # record environment
        elif node.type == "preproc_ifdef" or node.type == "preproc_if":
            if ce_cnt <= 10:
                write_node(node.start_point, node.end_point)
                # print(node.start_point, node.end_point)
                return
            
            # extern C
            if node.children[2].type == "linkage_specification":
                environment_stack.append("\n#ifdef __cplusplus \nextern \"C\" \n\{ \n#endif \n ")
                for child in node.children[2].children[2].children[2:-2]:
                    dfs_parse_tree(child)
                for i in range(len(sub_header_files)):
                    if subfile_environment[i] == len(environment_stack) - 1:
                        sub_header_files[i].write("\n#ifdef __cplusplus \n\} \n#endif \n")
                        subfile_environment[i] -= 1
                environment_stack.pop()
            # first one
            elif len(environment_stack) == 0:
                environment_stack.append(original_code_content[node.start_point[0]])
                for child in node.children[3:-1]:
                    dfs_parse_tree(child)
            # elif condition is modified

            else:
                environment_stack.append(original_code_content[node.start_point[0]])
                print("environment", len(environment_stack) - 1, original_code_content[node.start_point[0]])
                for child in node.children[2:-1]:
                    dfs_parse_tree(child)
                for i in range(len(sub_header_files)):
                    if subfile_environment[i] == len(environment_stack) - 1:
                        sub_header_files[i].write("\n#endif \n")
                        subfile_environment[i] -= 1
                environment_stack.pop()
        
        
        else:
            # print(node.type)
            # print(node.start_point, node.end_point)
            write_node(node.start_point, node.end_point)
            

    C_LANGUAGE = Language(tsc.language())
    parser = Parser(C_LANGUAGE)
    tree = parser.parse(bytes(''.join(original_code_content),"utf8"))
    cursor = tree.walk()
    # print(cursor.node.start_point, cursor.node.end_point)
    root_node = find_first_ifdef(cursor.node)
    # print(root_node.start_point, root_node.end_point)
    if cursor.node != None and root_node != None:
        ce_cnt = code_element_count_in_range(target_header_file.code_elements, cursor.node.start_point, root_node.start_point)
    if root_node == None or ce_cnt != 0:
        root_node = cursor.node
    # print(root_node.start_point, root_node.end_point)
    # print("!!!!!!!!!!!!!!!!!!!!")
    dfs_parse_tree(root_node)


    


'''
Given a clustering result (community index), generate the sub-header files for each cluster.
'''
def generate_subfiles(kwargs):
    # input
    project_dir = kwargs['project_dir']

    god_header_file_path = kwargs['god_header_file_path']
    god_header_file_name = kwargs['god_header_file_name']

    community_index = kwargs['community_index']
    for k in community_index.keys():
        community_index[k] = int(community_index[k])

    graph = kwargs['graph']
    code_elements = kwargs['code_elements']
    target_header_file = kwargs['target_header_file']
    file_names = kwargs['file_names']

    # for code_element in target_header_file.code_elements:
    #     print(code_element.name, code_element.type, code_element.start, code_element.end)

    original_code_content = list()
    with open(project_dir + god_header_file_path + god_header_file_name, 'r') as f:
        original_code_content = f.readlines()
    # os.remove(project_dir+god_header_file_path+god_header_file_name)

    
    qoutient_graph = generate_quotient_graph(community_index, graph.subgraph(code_elements))
    # print("quotient graph:", qoutient_graph.edges())
    # processing_order = toporlogical_processing_order(qoutient_graph)
    # print("processing order:", processing_order)

    # create the sub-header files
    sub_header_files = list()
    for i in range(int(max(community_index.values()))+1):
        file_handle = open(project_dir + god_header_file_path + file_names[i], 'w+')
        sub_header_files.append(file_handle)

    # protection macros start
    for i in range(int(max(community_index.values()))+1):
        sub_header_files[i].write("#ifndef " + file_names[i].replace("-", "_").replace(".", "_").upper() + "\n")
        sub_header_files[i].write("#define " + file_names[i].replace("-", "_").replace(".", "_").upper() + "\n")
        sub_header_files[i].write("\n")

    # include other header files
    for edge in qoutient_graph.edges():
        if edge[0] != edge[1]:
            sub_header_files[edge[0]].write("#include \"" + file_names[edge[1]] + "\"\n")



    # writing file content
    write_file_content(original_code_content, target_header_file, community_index, sub_header_files, graph)

    # protection macros end
    for i in range(int(max(community_index.values()))+1):
        sub_header_files[i].write("#endif\n")
        sub_header_files[i].close()

