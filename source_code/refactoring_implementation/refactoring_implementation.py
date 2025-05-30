import networkx as nx
import os
import shutil

from refactoring_implementation.utils import *
from refactoring_implementation.subfiles_generation import *
from refactoring_implementation.include_modification import *
from decomposition_plan_generation.utils import convert2nx_graph

def refactoring(project_dir, target_header_file_path, target_header_file, community_index, file_names):
    print("Implementing refactoring...")
    graph, code_elements, code_files = convert2nx_graph(target_header_file)

    god_header_file_path = ''
    if target_header_file_path.rfind(os.sep) == -1:
        god_header_file_path = project_dir.split(os.sep)[-1] + os.sep
    else:
        god_header_file_path = project_dir.split(os.sep)[-1] + os.sep + target_header_file_path[0: target_header_file_path.rfind(os.sep) + 1]

    # 这个跑通啦，大成功！
    args = {
        # input›
        "project_dir" : project_dir[0: project_dir.rfind(os.sep) + 1],
        "project_name" : project_dir.split(os.sep)[-1],
        "god_header_file_path" : god_header_file_path,
        "god_header_file_name" : target_header_file_path.split(os.sep)[-1],
        "community_index" : community_index,
        "graph" : graph,
        "target_header_file" : target_header_file,
        "code_elements" : code_elements,
        "code_files" : code_files,
        "file_names" : file_names
    }

    # backup
    new_project_dir = project_dir + "_copy"
    if not os.path.exists(new_project_dir):
        print("Backing up project directory...")
        shutil.copytree(project_dir, new_project_dir, symlinks=True)
    
    generate_subfiles(args)
    # modify_includes(args)

    print("Refactoring completed!")