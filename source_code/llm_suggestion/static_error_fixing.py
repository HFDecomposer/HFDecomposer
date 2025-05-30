import networkx as nx
import numpy as np
import json
import networkx.algorithms.community as nx_comm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from code_element_graph_construction.weighted_edge import tokenize_and_lemmatize, check_anonymous_enum

def get_LSI_vectors_for_two_elements(elem1, elem2):
    corpus = [
        ' '.join(tokenize_and_lemmatize(elem1.name)),
        ' '.join(tokenize_and_lemmatize(elem2.name))
    ]
    if corpus[0] == '' or corpus[1] == '':
        return 0
    # tfidf_vectorizer = TfidfVectorizer()
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(corpus)
    # num_topics = 1
    # lsa = TruncatedSVD(n_components=num_topics)
    # lsa_matrix = lsa.fit_transform(tfidf_matrix)

    vec1 = tfidf_matrix[0].toarray().flatten()  # 第一个文档的向量
    vec2 = tfidf_matrix[1].toarray().flatten()  # 第二个文档的向量
    
    # 计算余弦相似度
    similarity = cosine_similarity(vec1.reshape(1, -1), vec2.reshape(1, -1))[0][0]
    
    return similarity    
    return tfidf_matrix[0], tfidf_matrix[1]

def LSI_similarity(elem1, elem2):
    vec1, vec2 = get_LSI_vectors_for_two_elements(elem1, elem2)
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if not (check_anonymous_enum(elem1) or check_anonymous_enum(elem2)):
        return similarity
    return 0.0  

def dependency(code_element_1, code_element_2):
    if code_element_1 in code_element_2.reference:
        return 1
    if code_element_2 in code_element_1.reference:
        return 1
    return 0

def invocation(code_element_1, code_element_2):
    if (code_element_2.type == "declaration") and (code_element_1 in code_element_2.invocation):
        return 1
    if (code_element_1.type == "declaration") and (code_element_2 in code_element_1.invocation):
        return 1
    return 0

def fixing(element,position_dict,code_elements):
    result = 0
    index = 0
    # print(len(code_elements[0]),len(code_elements[1]))
    for i in range(len(code_elements)):
        temp_sum = 0
        for code_element in code_elements[i]:
            ss = get_LSI_vectors_for_two_elements(element,code_element)
            ivc = invocation(element,code_element)
            dp = dependency(element,code_element)
            pos = 1/abs(position_dict[f"{element.name}+{element.type}"]-position_dict[f"{code_element.name}+{code_element.type}"])
            temp_sum += (ss+dp+ivc+pos)
        if temp_sum/len(code_elements[i]) > result:
            result = temp_sum/len(code_elements[i])
            index = i
    return index
    
def static_checking_and_fixing(community_index,target_header_file,project_name,basename):
    missing_list = []
    code_elements = [[] for _ in range(int(max(community_index.values()))+1)]
    for code_element in target_header_file.code_elements:
        # print(code_element.name)
        if code_element.name in community_index:
            index = community_index[code_element.name]
            code_elements[index].append(code_element)
        else:
            if not code_element.name.endswith(".h"):
            # print(community_index[code_element.name])
                missing_list.append(code_element)
    if len(missing_list) != 0:
        sorted_code_elements = sorted(target_header_file.code_elements,key=lambda x: (x.start[0], x.start[1]))
        position_dict = {f"{element.name}+{element.type}": idx + 1 for idx, element in enumerate(sorted_code_elements)}
        # print(position_dict)
        print(f"static_error_checking_and_fixing:")
        fixing_list = []
        for element in missing_list:
            if element.name not in fixing_list:
                fixing_index = fixing(element,position_dict,code_elements)
                community_index[element.name] = fixing_index
                print(f"missing: {code_element.name}, fixing_index: {fixing_index}")
                fixing_list.append(code_element.name)
    return community_index