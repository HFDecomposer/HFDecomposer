import httpx
from openai import OpenAI
import re
import os
import json
from decomposition_plan_generation.utils import convert2nx_graph
from refactoring_implementation.utils import generate_quotient_graph

def get_new_name_from_llm(entities_list,key):
    try:
        input = f'''I want to create a new class which contains {entities_list}. 
                    Please give me a class name that can summart these entities. 
                    The output should be just a name , don't give any code, reason or analyzation'''
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "I am an AI trained to give suggestions on merging files in C++ code."},
                {"role": "user", "content": input }
            ],          
            temperature=0,
            stream=False
        )
        if response.choices:
            model_response = response.choices[0].message.content if response.choices[0].message else ""
        else:
            model_response = ""
    except Exception as e:
        print(f"Error while detecting code smells: {e}")
        model_response = "error"  

    return model_response

def summary_entity_json(project_name,entity_list,basename,parts,co_usage='',dependency='',reference='',code=True,key=""):
    try:
        # prompt
        dependency_prompt = '''Here are the internal dependency relationships within this file. 
                        Files with dependency relationships are more likely to be grouped into the same subfile.''' + dependency
        reference_prompt = '''Here are the internal reference relationships within this file. 
                        Files with reference relationships are more likely to be grouped into the same subfile.''' + reference
        if not code:
            code_content = ''
        else:
            code_content = "Here is the header file:\n" + code_content + '\n'
        input = f'''There are too many definitions and functions in one header file. I want to decompose it into smaller ones to increase the maintainability.
                    Please give a plan for decomposing the header file according to their dependency, functional similarity and semantic similarity.
                    There are {len(entity_list)} entities to be decomposed. The list is:{entity_list}\n{co_usage}\n{dependency_prompt}\n{reference_prompt}\n
                    The answer you give should be a json file that classify different entities to different labels. The example json is:
                    {{{{
                        "GinNextPostingListSegment": 0,
                        "GinGetPendingListCleanupSize": 0,
                        "SizeOfGinPostingList": 1,
                        "GinPostingList": 1,
                        "ginPostingListDecodeAllSegmentsToTbm": 2,
                        "ginPostingListDecode": 3
                        }}}}
                    Please classify the {len(entity_list)} entities into {parts} parts.
                    Don't give the reason and the analyzation.
                    ''' 
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "I am an AI trained to generate a plan for decomposing header files in C++ code."},
                {"role": "user", "content": input }
            ],
            temperature=0,
            stream=False
        )
        if response.choices:
            model_response = response.choices[0].message.content if response.choices[0].message else ""
        else:
            model_response = ""
    except Exception as e:
        print(f"Error while getting response: {e}")
        model_response = "error"  
    return model_response

def summary_response_to_json(project_name,model_response,basename,summary_dict):
    pattern = r'```json\n(.*?)```'
    clean_code = re.findall(pattern, model_response, re.DOTALL)
    community_index = json.loads(clean_code[0])
    new_community_index = {}
    for element in community_index:
        if element in summary_dict:
            for name in summary_dict[element]:
                new_community_index[name] = community_index[element]
    with open(f"init_result.json", 'w') as json_file:
        json.dump(new_community_index, json_file)
    return new_community_index

def set_find_function_dependency(declaration_code,code_elements,name,entity_dict):
    name_list = []
    for code_element in code_elements:
        if (code_element.name != name) and (code_element.name in declaration_code):
            if entity_dict[code_element.name] not in name_list:
                name_list.append(entity_dict[code_element.name])
    return name_list

def set_dependency_prompt(project_name,code_elements,basename,entity_dict):
    dependency_dict={}
    for code_element in code_elements:
        if code_element.type == "declaration":
            for file_path in code_element.referenced_by:
                path = os.path.normpath(file_path)
                with open(path,'r',encoding='gbk',errors='ignore') as f:
                    file_content = f.read()
                declaration_code = find_function_definition(file_content, code_element.name)
                if declaration_code:
                    name_list = set_find_function_dependency(declaration_code,code_elements,code_element.name,entity_dict)
                    if entity_dict[code_element.name] not in dependency_dict:
                        dependency_dict[entity_dict[code_element.name]] = name_list
                    else:
                        for name in name_list:
                            if name not in dependency_dict[entity_dict[code_element.name]]:
                                dependency_dict[entity_dict[code_element.name]].append(name)
                    break
    prompt = ''
    for name in dependency_dict:
        prompt += f'{name} calls'
        for called in dependency_dict[name]:
            prompt += f' {called}'
        prompt += '.\n'
    return prompt

def set_reference_prompt(project_name,code_elements,target_header_file,basename,entity_dict):
    prompt = ''
    reference_dict={}
    for i in range(len(code_elements)):
        if len(code_elements[i].reference) == 0:
            continue
        if entity_dict[code_elements[i].name] not in reference_dict:
            reference_dict[entity_dict[code_elements[i].name]] = []
        for elem in code_elements[i].reference:
            if entity_dict[elem.name] not in reference_dict[entity_dict[code_elements[i].name]]:
                reference_dict[entity_dict[code_elements[i].name]].append(entity_dict[elem.name])

    for name in reference_dict:
        prompt += f'{name} calls'
        for called in reference_dict[name]:
            prompt += f' {called}'
        prompt += '.\n'
    return prompt

def cluster_llm_refactoring(project_name,community_index,target_header_file,target_header_file_path,useGPT,plan_overview,parts,semantic,key,URL):

    os.environ["HTTP_PROXY"] = URL
    os.environ["HTTPS_PROXY"] = URL
    basename = os.path.basename(target_header_file_path)

    summary_dict = {}
    entity_dict = {}
    new_name_list = []
    for i in range(int(max(community_index.values()))+1):
        entities = plan_overview['partition'].get(f"sub_{basename.replace('.h', '')}_{i}.h", [])
        entities_list = [item.split('+')[0] for item in entities]
        new_name = get_new_name_from_llm(entities_list,key).replace('"','').replace("'",'').replace("`",'')
        new_name_list.append(new_name)
        for entity in entities_list:
            entity_dict[entity] = new_name
        if new_name not in summary_dict:
            summary_dict[new_name]= entities_list
        else:
            for entity in entities_list:
                summary_dict[new_name].append(entity)

    dependency = set_dependency_prompt(project_name,target_header_file.code_elements,basename,entity_dict)
    reference = set_reference_prompt(project_name,target_header_file.code_elements,target_header_file,basename,entity_dict)

    model_response = summary_entity_json(project_name,new_name_list,basename,parts,"",dependency,reference,False,key)
    community_index = summary_response_to_json(project_name,model_response,basename,summary_dict)
 
    return community_index    

def content_llm_json(project_name,code_elements,basename,parts,code_content,co_usage='',dependency='',reference='',code=True,key="",URL=""):
    try:
        # os.environ["HTTP_PROXY"] = URL
        # os.environ["HTTPS_PROXY"] = URL

        entity_prompt = f'''There are {len(code_elements)} entities to be decomposed. The list is:[''' 
        for code_element in code_elements:
            entity_prompt += (code_element.name + ',')
        entity_prompt += '].'
        entity_prompt = ''
        if dependency != '':
            dependency = '''Here are the internal dependency relationships within this file. 
                            Files with dependency relationships are more likely to be grouped into the same subfile.''' + dependency
        if reference != '':
            reference = '''Here are the internal reference relationships within this file. 
                           Files with reference relationships are more likely to be grouped into the same subfile.''' + reference
        if not code:
            code_content = ''
        else:
            code_content = "Here is the header file:\n" + code_content + '\n'
        input = f'''There are too many definitions and functions in one header file. I want to decompose it into smaller ones to increase the maintainability.
                    Please give a plan for decomposing the header file according to their dependency, functional similarity and semantic similarity.
                    {code_content}{entity_prompt}\n{co_usage}\n{dependency}\n{reference}\n
                    The answer you give should be a json file that classify different entities to different labels. The example json is:
                    {{{{
                        "GinNextPostingListSegment": 0,
                        "GinGetPendingListCleanupSize": 0,
                        "SizeOfGinPostingList": 1,
                        "GinPostingList": 1,
                        "ginPostingListDecodeAllSegmentsToTbm": 2,
                        "ginPostingListDecode": 3
                        }}}}
                    Please classify the {len(code_elements)} entities into {parts} parts.
                    Don't give the reason and the analyzation.
                    ''' 

        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "I am an AI trained to generate a plan for decomposing header files in C++ code."},
                {"role": "user", "content": input }
            ],
            temperature=0,
            stream=False
        )
        if response.choices:
            model_response = response.choices[0].message.content if response.choices[0].message else ""
        else:
            model_response = ""
    except Exception as e:
        print(f"Error while getting response: {e}")
        model_response = "error"  
    return model_response

def response_to_json(project_name,model_response,basename):
    pattern = r'```json\n(.*?)```'
    clean_code = re.findall(pattern, model_response, re.DOTALL)
    community_index = json.loads(clean_code[0])
    new_dict = dict(community_index.items())  # 复制原字典的键值对到新字典
    for element in new_dict:
        if element.endswith(".h"):
            del community_index[element]
    with open(f"init_result.json", 'w') as json_file:
        json.dump(community_index, json_file)
    return community_index

def old_co_usage_prompt(project_name,code_elements,target_header_file,basename):
    co_usage_dict={}
    for code_element in code_elements:
        # print(f"代码元素名称: {code_element.name}, referenced_by 长度: {len(code_element.referenced_by)}， reference 长度：{len(code_element.reference)}")
        if not code_element.referenced_by:
            continue
        for referenced in code_element.referenced_by:
            # print(referenced)
            referenced_basename = os.path.basename(os.path.normpath(referenced))
            if referenced_basename not in co_usage_dict:
                co_usage_dict[referenced_basename] = []
            co_usage_dict[referenced_basename].append(code_element.name)
    prompt = ''
    for key in co_usage_dict:
        if len(co_usage_dict[key]) > 1:
            prompt += f'{key} calls'
            for name in co_usage_dict[key]:
                prompt += f' {name}'
            prompt += '.\n'
    prompt = '''Here are the external dependency relationship about how other files call the definitions in this header file. 
                Definitions that are called simultaneously by a file are more likely to be grouped into the same subfile.\n''' + prompt
    return prompt

def find_function_definition(file_content, function_name):
    escaped_name = re.escape(function_name)
    pattern = re.compile(rf'\b{escaped_name}\s*\([^)]*\)\s*{{', re.DOTALL | re.MULTILINE)
    match = pattern.search(file_content)

    if not match:
        return ""
    start_index = match.end() - 1 
    brace_count = 1  
    end_index = start_index + 1
    while brace_count > 0 and end_index < len(file_content):
        if file_content[end_index] == '{':
            brace_count += 1
        elif file_content[end_index] == '}':
            brace_count -= 1
        end_index += 1
    if brace_count != 0:
        return ""
    
    function_code = file_content[match.start():end_index]
    return function_code

def old_find_function_dependency(declaration_code,code_elements,name):
    prompt = (name+" calls") 
    for code_element in code_elements:
        if (code_element.name != name) and (code_element.name in declaration_code):
            prompt += (" " + code_element.name)
    prompt += '.\n'
    if prompt == (name+" calls.\n"):
        prompt = ''
    return prompt

def old_dependency_prompt(project_name,code_elements,target_header_file,basename):
    prompt = ''
    for code_element in code_elements:
        if code_element.type == "declaration":
            for file_path in code_element.referenced_by:
                path = os.path.normpath(file_path)
                with open(path,'r',encoding='gbk',errors='ignore') as f:
                    file_content = f.read()
                declaration_code = find_function_definition(file_content, code_element.name)
                if declaration_code:
                    prompt += old_find_function_dependency(declaration_code,code_elements,code_element.name)
                    break
    return prompt

def reference_prompt(project_name,code_elements,target_header_file,basename):
    prompt = ''
    for i in range(len(code_elements)):
        if len(code_elements[i].reference) == 0:
            continue
        prompt += f'{code_elements[i].name} calls'
        for elem in code_elements[i].reference:
            prompt += f' {elem.name}'
        prompt += '.\n'

    return prompt    

def content_refactoring(project_name,code_elements,basename,target_header_file,parts,code_content,key,URL):

    co_usage = old_co_usage_prompt(project_name,code_elements,target_header_file,basename)
    dependency = old_dependency_prompt(project_name,code_elements,target_header_file,basename)
    reference = reference_prompt(project_name,code_elements,target_header_file,basename)    

    model_response = content_llm_json(project_name,code_elements,basename,parts,code_content,'',dependency,reference,True,key,URL)
    community_index = response_to_json(project_name,model_response,basename)

    return
