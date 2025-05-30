# -*- coding:utf-8 -*-

import os
import sys
import time
import json
import pandas as pd
import ast

from code_element_graph_construction.graph_constructor import get_code_element_graph
from decomposition_plan_generation.plan_generation import decomposing_through_Louvain, plan_overview
from decomposition_plan_generation.circular_dependency_fixing.fixing import circular_dependency_fixing
from refactoring_implementation.file_name_generation import generate_file_names
from llm_suggestion.llm_suggestion import *
from llm_suggestion.static_error_fixing import *
from refactoring_implementation.refactoring_implementation import refactoring

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python main.py <project_dir> <target_header_file_path> <parts> <key> <URL>")
        sys.exit(1)
        
    project_dir = sys.argv[1]
    target_header_file_path = (sys.argv[2]).replace('/','\\')
    parts = int(sys.argv[3])  
    key = sys.argv[4]
    URL = sys.argv[5]

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    basename = os.path.basename(target_header_file_path)

    if project_dir[-1] == '/' or project_dir[-1] == '\\':
        project_dir = project_dir[:-1]
    project_dir = os.path.normpath(project_dir)
    project_name = project_dir.split(os.sep)[-1]

    header_files = get_code_element_graph(project_dir,target_header_file_path)
    prefix = list(header_files.keys())[0]
    prefix = prefix[:prefix.find(project_name)]
    target_file = os.path.join(prefix, project_name, target_header_file_path)
    target_header_file = header_files[target_file]
    
    if len(target_header_file.code_elements) >= 200:
        community_index = decomposing_through_Louvain(target_header_file)
        file_names = generate_file_names(target_header_file, community_index, False, key, URL)
        overview = plan_overview(target_header_file, community_index, file_names)
        community_index = cluster_llm_refactoring(project_name,community_index,target_header_file,target_header_file_path,useGPT,overview,parts,True,key,URL)
    else:
        with open(target_file,'r',encoding='gbk',errors='ignore') as f:
            code_content = f.read()
        print(project_name,basename)
        content_refactoring(project_name,target_header_file.code_elements,basename,target_header_file, parts, code_content, key, URL)
    with open(f"init_result.json", 'r', encoding='utf-8') as json_file:
        community_index = json.load(json_file)
    community_index = static_checking_and_fixing(community_index,target_header_file,project_name,basename)
    community_index = circular_dependency_fixing(target_header_file,community_index)
    with open(f"final_result.json", 'w', encoding='utf-8') as json_file:
        json.dump(community_index, json_file)
    print(community_index)        
    
    file_names = generate_file_names(target_header_file, community_index, True, key, URL)
    print(len(file_names), file_names)
    json_content = plan_overview(target_header_file, community_index, file_names)
    file_names = []
    partition_data = json_content.get('partition', {})
    for header_file, items in partition_data.items():
        file_names.append(header_file)

    refactoring(project_dir, target_header_file_path, target_header_file, community_index, file_names)     
        