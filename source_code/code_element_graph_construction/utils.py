import os

# return spelling string of a node
def get_name(node, code_content):
    name_start = node.start_point
    name_end = node.end_point
    if name_start[0] != name_end[0]:
        # print(name_start,name_end)
        # print("\n".join(code_content[name_start[0]:name_end[0]+1]))
        return "\n".join(code_content[name_start[0]:name_end[0]+1])
    return code_content[name_start[0]][name_start[1]:name_end[1]]


def get_include_name(node, code_content):
    include_file_name = get_name(node.child_by_field_name("path"), code_content)
    include_file_name = include_file_name.replace("\"", "").replace("<", "").replace(">", "").replace("..", "")
    return include_file_name


def get_include_header_file(file_name, header_files):
    file_name = os.path.normpath(file_name)
    length = len(file_name)
    for header_file in header_files.values():
        if header_file.file_path[-length:] == file_name and (header_file.file_path[-length-1] == '/' or header_file.file_path[-length] == '/' or header_file.file_path[-length-1] == '\\' or header_file.file_path[-length] == '\\'):
            return header_file
    return None


# seperate a string by non-identifier characters
def seperate_by_non_identifier(string):
    result = []
    start = 0
    for i in range(len(string)):
        if not string[i].isalnum() and string[i] != "_":
            if start != i:
                result.append(string[start:i])
            start = i + 1
    if start != len(string):
        result.append(string[start:])
    return result


# this code element --use--> other code element in the given header file
def get_reference(node, code_content, header_file):
    references = []
    def inner_dfs(node):

        if node == None:
            return

        if node.type == "identifier" or node.type == "type_identifier":
            name = get_name(node, code_content)

            if name in header_file.new_names.keys():
                references.append(header_file.new_names[name])
        if node.type == "preproc_arg":
            seperated_names = seperate_by_non_identifier(get_name(node, code_content))
            for seperated_name in seperated_names:
                if seperated_name in header_file.new_names.keys():
                    references.append(header_file.new_names[seperated_name])
        if node.child_count == 0:
            return
        else:
            for child in node.children:
                inner_dfs(child)
    
    inner_dfs(node)

    if node.start_point[1] != 0:
        inner_dfs(node.prev_sibling)

    return set(references)


def read_content(file_path):
    code_content = []
    try:
        with open(file_path, 'r', encoding='utf8') as f:
            code_content = f.readlines()
            return code_content
    except:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                code_content = f.readlines()
                return code_content
        except:
            return code_content

# c/h file --use--> code element
def get_referenced_by(file_path, c_parser, header_files):
    # print("================================")
    # print("parse include relationship of " + file_path)

    code_content = read_content(file_path)

    tree = c_parser.parse(bytes(''.join(code_content),"utf8"))
    cursor = tree.walk()
    new_names = {}

    def dfs_for_include_file(node, depth):
        if depth > 8:
            return
        if node.type == "preproc_include":
            header_file_name = get_include_name(node, code_content)
            header_file = get_include_header_file(header_file_name, header_files)

            # if file_path.endswith('fipsinstall.c'):
            #     print(header_file_name)
            #     print(header_file is not None)
            if header_file is not None:
                header_file.included_by.add(file_path)
                # print(header_file.file_path)
                new_names.update(header_file.new_names)
            return
        if node.child_count == 0:
            return
        else:
            for child in node.children:
                dfs_for_include_file(child, depth+1)

    def dfs_for_reference(node, depth):
        if depth > 900:
            return
        if node.type == "identifier" or node.type == "type_identifier":
            name = get_name(node, code_content)
            if name in new_names.keys():
                new_names[name].referenced_by.add(file_path)
        if node.type == "preproc_arg":
            seperated_names = seperate_by_non_identifier(get_name(node, code_content))
            for seperated_name in seperated_names:
                if seperated_name in new_names.keys():
                    new_names[seperated_name].referenced_by.add(file_path)
        if node.child_count == 0:
            return
        else:
            try:
                for child in node.children:
                    dfs_for_reference(child, depth+1)
            except:
                pass
    
    dfs_for_include_file(cursor.node, 0)
    dfs_for_reference(cursor.node, 0)


# indirect c file --directly use--> this code element
def get_referenced_by_for_target_h_file(file_path, header_file, c_parser):
    code_content = read_content(file_path)
    
    tree = c_parser.parse(bytes(''.join(code_content),"utf8"))
    cursor = tree.walk()

    new_names = header_file.new_names

    def dfs_for_reference(node, depth):
        if depth > 900:
            return
        # TODO: complieteness to be confirmed
        if node.type == "identifier" or node.type == "type_identifier":
            name = get_name(node, code_content)
            if name in new_names.keys():
                new_names[name].referenced_by.add(file_path)
        if node.child_count == 0:
            return
        else:
            for child in node.children:
                dfs_for_reference(child, depth+1)
    
    dfs_for_reference(cursor.node, 0)

# this code element --use--> other h file
# this code element --use--> other code element in other header file (recorded in the other header file)
def get_include(header_files, c_parser):
    for header_file in header_files.values():
        new_include = set()
        for include_file in header_file.include:
            included_header_file = get_include_header_file(include_file, header_files)
            if included_header_file is None:
                # print("Could not find file: ", include_file)
                continue
            new_include.add(included_header_file.file_path)
            included_header_file.included_by.add(header_file.file_path)
            for code_element in header_file.code_elements:
                code_element_str = header_file.code_content[code_element.start[0]: code_element.end[0] + 1]
                tree = c_parser.parse(bytes(''.join(code_element_str),"utf8"))
                cursor = tree.walk()
                references = get_reference(cursor.node, code_element_str, included_header_file)

                if len(references) > 0:
                    # this code element --use--> other h file
                    code_element.include.add(included_header_file.file_path)
                    # this code element --use--> other code element in other header file (recorded in the other header file)
                    for other_code_element in references:
                        if header_file.file_path not in other_code_element.referenced_by_hce.keys():
                            other_code_element.referenced_by_hce[header_file.file_path] = set()
                        other_code_element.referenced_by_hce[header_file.file_path].add(code_element)
        header_file.include = new_include
    return 


def get_include_for_target_h_file(header_file, included_header_file, c_parser):
    for code_element in header_file.code_elements:
        code_element_str = header_file.code_content[code_element.start[0]: code_element.end[0] + 1]
        tree = c_parser.parse(bytes(''.join(code_element_str),"utf8"))
        cursor = tree.walk()
        references = get_reference(cursor.node, code_element_str, included_header_file)
        if len(references) > 0:
            for other_code_element in references:
                if header_file.file_path not in other_code_element.referenced_by_hce.keys():
                    other_code_element.referenced_by_hce[header_file.file_path] = set()
                other_code_element.referenced_by_hce[header_file.file_path].add(code_element)
            

# c/h file --(directly/indirectly) use--> this h file
def get_all_include_by(header_file, header_files):
    include_by = set()
    def dfs(header_file, depth):
        for file in header_file.included_by:
            if file not in include_by:
                include_by.add(file)
                # print(depth, file)
                if file.endswith(".h"):
                    dfs(header_files[file], depth+1)
    dfs(header_file, 0)
    if header_file.file_path in include_by:
        include_by.remove(header_file.file_path)
    return include_by


def get_indirect_reference_by(code_element):
    indirect_reference_by = set()
    visited = set()
    def dfs(code_element, depth):
        for ce_set in code_element.referenced_by_hce.values():
            for other_code_element in ce_set:
                if other_code_element in visited:
                    continue
                visited.add(other_code_element)
                indirect_reference_by.update(other_code_element.referenced_by)
                if depth < 900:
                    dfs(other_code_element, depth+1)
    dfs(code_element, 0)
    return indirect_reference_by
