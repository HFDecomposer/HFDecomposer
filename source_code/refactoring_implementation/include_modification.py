import json
import re

from code_element_graph_construction.graph_constructor import load_header_files_from_pickle
from refactoring_implementation.utils import *

# only direct includes?
def identify_new_includes(graph, code_elements, code_files, community_index):
    new_include = dict()
    for n in code_files:
        new_include[n] = set()
    for u, v in graph.edges():
        if (u in code_files) and (v not in code_files):
            new_include[u].add(community_index[v])
    return new_include


def regex_pattern(god_header_file_name, god_header_file_path):
    path_names = god_header_file_path.split("/")
    path_names = [x for x in path_names if x != ""] 
    path_pattern_str = "("
    for i in range(1, len(path_names)):
        if i == len(path_names) - 1:
            path_pattern_str += path_names[i] + "/)?"
        else:
            path_pattern_str += "/".join(path_names[i:]) + "/|"
    if path_pattern_str == "(":
        path_pattern_str = ""
    pattern_str = r'#include\s*\"' + path_pattern_str + god_header_file_name + r'\"'
    # print(pattern_str)
    return re.compile(pattern_str)


def subsitute_include_statement(file_content, original_include_statement, file_include, subfile_names, file_path):
    original_include_statement_str = original_include_statement.group()
    try:
        original_include_path = original_include_statement.groups()[0]
    except:
        original_include_path = ""
    if original_include_path is None:
        original_include_path = ""

    new_include_statement = ""
    for subfile in file_include:
        new_include_statement += "#include \"" + original_include_path + subfile_names[subfile] + "\"\n"
    
    # print("=================================")
    # print(file_path)
    # print(new_include_statement)

    return file_content.replace(original_include_statement_str, new_include_statement)


# TODO: include in #if
def new_include_statement_position(god_header_file_path, file_content):
    # best position: immediately after the last include statement under the same folder
    path_names = god_header_file_path.split("/")
    path_names = [x for x in path_names if x != ""] 
    # path_pattern_str = "(?:"
    # for i in range(1, len(path_names)):
    #     if i == len(path_names) - 1:
    #         path_pattern_str += path_names[i] + "/)"
    #     else:
    #         path_pattern_str += "/".join(path_names[i:]) + "/|"
    path_pattern_str = r"(?:{}/)*".format(r"|".join(path_names))
    pattern_str = r'#include\s*\"' + path_pattern_str + r'.*\.h\"'
    include_pattern = re.compile(pattern_str)
    include_statements = include_pattern.findall(file_content)
    if len(include_statements) > 0:
        return include_statements

    # second position: after all of the include statements (h)
    include_pattern = re.compile(r'#include\s*\".*\.h\"')
    include_statements = include_pattern.findall(file_content)
    return include_statements



def add_new_include_statement(file_content, file_include, subfile_names, file_path, god_header_file_path, god_header_file_name):
    include_path = ""
    # if file_path.find("include") != -1:
    #     include_path = god_header_file_path[god_header_file_path.find("include")+8:]
    #     print("****************************************1")
    #     print(include_path)
    # else:
    god_dir = os.path.dirname(god_header_file_path)
    file_dir = os.path.dirname(file_path)

    project_root = os.path.commonpath([god_dir, file_dir])

    relative_god_path = os.path.relpath(god_header_file_path, project_root)
    relative_file_path = os.path.relpath(file_path, project_root)

    include_path = os.path.relpath(god_header_file_path, file_dir)
    # print("****************************************2")
    # print(relative_god_path)
    # print(relative_file_path)
    # print(include_path)

    if include_path != "":
        include_path += '/' 

    include_path = include_path.replace("\\", "/")
                
    new_include_statement = ""
    for subfile in file_include:
        new_include_statement += "#include \"" + include_path + subfile_names[subfile] + "\"\n"

    # assert these statements immediately after the last include statement
    # include_pattern = re.compile(r'#include\s*\".*\"')
    # include_statements = include_pattern.findall(file_content)
    include_statements = new_include_statement_position(god_header_file_path, file_content)
    if len(include_statements) == 0:
        print("ERROR: no include statement in file: " + file_path)
        #   file_content = new_include_statement + file_content
    else:
        file_content = file_content.replace(include_statements[-1], include_statements[-1] + "\n" + new_include_statement)
        # print("=================================")
        # print(file_path)
        # print(include_statements[-1])
        # print(new_include_statement)
    
    return file_content



def modify_downstream_files(project_dir, file_path, god_header_file_path, file_include, subfile_names, pattern, god_header_file_name):
    # read file content
    file_content = ""
    with open(project_dir + file_path, 'r') as f:
        file_content = f.read()
    
    original_include_statement = pattern.search(file_content)

    if original_include_statement is None:
        if len(file_include) == 0:
            print("No include: ", file_path)
            return
        else:       
            # indirectly include the god header file through other header files, but it now has to directly include the subfiles
            file_content = add_new_include_statement(file_content, file_include, subfile_names, file_path, god_header_file_path, god_header_file_name)
    else :
        file_content = subsitute_include_statement(file_content, original_include_statement, file_include, subfile_names, file_path)

    # print("=================================")
    # print(file_path)
    # print(new_include_statement)

    # print(file_content)

    # write file content

    with open(project_dir + file_path, 'w') as f:
        f.write(file_content)


def modify_includes(kwargs):
    # input
    project_dir = kwargs['project_dir']
    project_name = kwargs['project_name']
    god_header_file_path = kwargs['god_header_file_path']
    god_header_file_name = kwargs['god_header_file_name']
    community_index = kwargs['community_index']
    for k in community_index.keys():
        community_index[k] = int(community_index[k])

    graph = kwargs['graph']
    code_elements = kwargs['code_elements']
    code_files = kwargs['code_files']

    # identify new include relationships
    # only direct include?
    new_includes = identify_new_includes(graph, code_elements, code_files, community_index)

    # file names
    subfile_names = kwargs['file_names']

    # regex pattern
    pattern = regex_pattern(god_header_file_name, god_header_file_path)

    # modify each file
    count = 0 
    for file in code_files:
        file_path = file[file.find(project_name):]
        file_include = new_includes[file]
        count += len(new_includes[file])
        # modify_downstream_files(project_dir, file_path, god_header_file_path, file_include, subfile_names, pattern, god_header_file_name)
    print(count)


