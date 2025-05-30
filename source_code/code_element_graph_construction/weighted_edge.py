import numpy as np
import re
import nltk
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

# structural dependency
def structural_dependency_for_elements(code_element_1, code_element_2):
    if code_element_1 in code_element_2.reference:
        # print(code_element_1.name, code_element_2.name)
        return 1
    if code_element_2 in code_element_1.reference:
        # print(code_element_1.name, code_element_2.name)
        return 1
    return 0

def structural_dependency_for_file(header_file):
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(i+1, len(code_elements)):
            w = structural_dependency_for_elements(code_elements[i], code_elements[j])
            result[i, j] = w
            result[j, i] = w
    return result


# call-based dependency from bavota
# [i,j] represents how many times cei uses cej (but no times)

def call_based_dependency_for_elements(code_element_1, code_element_2):
    if code_element_2 in code_element_1.reference:
        # print(code_element_1.name, code_element_2.name)
        return 1
    return 0

def call_based_dependency_for_file(header_file):
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(len(code_elements)):
            if i != j:
                result[i,j] = call_based_dependency_for_elements(code_elements[i], code_elements[j])
        
    return result


# cdm from bavota
def normalized_dependency(header_file):
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

            if cdm[i,j] > 0.6 and cdm[i,j] < 0.7:
                print(i,j,cdm[i,j])
                print(dependency[j,i], isum, dependency[i,j], jsum)
    return cdm


# shared attributes
def shared_dependency(header_file):
    length = len(header_file.code_elements)
    dependency = call_based_dependency_for_file(header_file)
    dependency = dependency.astype(int)
    result = np.zeros((length, length))
    for i in range(length):
        for j in range(i+1, length):
            and_array = np.bitwise_and(dependency[i], dependency[j])
            or_array = np.bitwise_or(dependency[i], dependency[j])
            or_num = np.sum(or_array)
            if or_num == 0:
                continue
            and_num = np.sum(and_array)
            result[i,j] = and_num / or_num
            result[j,i] = and_num / or_num

    return result

# functional coupling v2
def functional_coupling(header_file):
    length = len(header_file.code_elements)
    dependency = call_based_dependency_for_file(header_file)
    dependency = dependency.astype(int)
    result = np.zeros((length, length))
    for i in range(length):
        for j in range(i+1, length):
            and_array = np.bitwise_and(dependency[:, i], dependency[:, j])
            or_array = np.bitwise_or(dependency[:, i], dependency[:, j])
            or_num = np.sum(or_array)
            if or_num == 0:
                continue
            and_num = np.sum(and_array)
            result[i,j] = and_num / or_num
            result[j,i] = and_num / or_num

    return result


# shared usage
'''
param: two code elements
return: how many times the two code elements are used by a same file
'''
def shared_usage_for_elements(code_element_1, code_element_2):
    shared_files = code_element_1.referenced_by.intersection(code_element_2.referenced_by)
    union_files = code_element_1.referenced_by.union(code_element_2.referenced_by)
    if len(union_files) == 0 or len(shared_files) == 0:
        return 0
    return len(shared_files) / len(union_files)

'''
param: header file (header_file.code_elements)
return: matrix
'''
def shared_usage_for_file(header_file):
    threshold = 0.0
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(i+1, len(code_elements)):
            w = shared_usage_for_elements(code_elements[i], code_elements[j])
            result[i, j] = w
            result[j, i] = w
    result[result < threshold] = 0
    return result

# FCW from wang 2018
def functional_coupling_for_elements(code_element_1, code_element_2):
    shared_files = code_element_1.referenced_by.intersection(code_element_2.referenced_by)
    all_files = len(code_element_1.referenced_by) + len(code_element_2.referenced_by)
    if all_files == 0 or len(shared_files) == 0:
        return 0
    return len(shared_files) / all_files
# v1
def functional_coupling_for_file(header_file):
    threshold = 0.0
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(i+1, len(code_elements)):
            w = functional_coupling_for_elements(code_elements[i], code_elements[j])
            result[i, j] = w
            result[j, i] = w
    result[result < threshold] = 0
    return result

# semantic similarity

def only_uppercase_and_underscore(s):
    # macro name or others
    pattern = r'^[A-Z_]+$'
    if re.match(pattern, s):
        return True
    else:
        return False

def has_upper_and_lower(text):
    has_upper = False
    has_lower = False

    for char in text:
        if char.isupper():
            has_upper = True
        elif char.islower():
            has_lower = True
        if has_upper and has_lower:
            break
    return has_upper and has_lower

def tokenize_and_lemmatize(name):
    # split by "_" or upper character
    stop_words = {
        'set', 'get', 'is', 'use', 'of', 
    }
    split_names = []
    if name.startswith('_'):
        name = name[1:]
    if only_uppercase_and_underscore(name) or '_' in name:
        split_names = name.split('_')
    elif has_upper_and_lower(name) and name[0].islower():
        tmp = name[0].upper()
        name = tmp + name[1:]
        split_names = re.findall('[A-Z]+[a-z]*|[0-9]+', name)
    else:
        split_names = re.findall('[A-Z]+[a-z]*|[0-9]+', name)
    if len(split_names) == 0:
        split_names = [name]
    stemmer = PorterStemmer()
    words = []
    for split_name in split_names:
        if has_upper_and_lower(split_name):
            l = re.findall('[A-Z]+[a-z]*', split_name)
            words.extend(l)
        else:
            words.append(split_name)
    res = []
    for split_name in words:            
        split_name = split_name.strip().lower()
        # word = stemmer.stem(split_name)
        word = split_name
        # if split_name.endswith('e'):
        #     word += 'e'
        res.append(word)
    # print(set(res))
    return set(res) - stop_words


def Jaccard_distance_for_elements(code_element_1, code_element_2):
    set1 = tokenize_and_lemmatize(code_element_1.name)
    set2 = tokenize_and_lemmatize(code_element_2.name)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    distance = intersection / union
    return distance

def check_anonymous_enum(code_element):
    if code_element.name.startswith('_data') or code_element.name.startswith('/data'):
        return True
    return False

'''
code_element.name
'''
def semantic_similarity_for_file(header_file):

    threshold = 0.0
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(i+1, len(code_elements)):
            w = Jaccard_distance_for_elements(code_elements[i], code_elements[j])
            if not (check_anonymous_enum(code_elements[i]) or check_anonymous_enum(code_elements[j])):
                result[i, j] = w
                result[j, i] = w
    result[result < threshold] = 0
    return result


def normalize_matrix(matrix):
    mean = np.mean(matrix)
    std = np.std(matrix)
    normalized_matrix = (matrix - mean) / std
    sigmoid_matrix = 1 / (1 + np.exp(-normalized_matrix))
    return sigmoid_matrix
    

# LSI version 
def  get_LSI_matrix(header_file):
    code_elements = header_file.code_elements
    corpus = []
    for code_elem in code_elements:
        corpus.append(list(tokenize_and_lemmatize(code_elem.name)))
    corpus = [' '.join(document) for document in corpus]
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(corpus)
    num_topics = 7
    lsa = TruncatedSVD(n_components=num_topics)
    lsa_matrix = lsa.fit_transform(tfidf_matrix)
    return lsa_matrix

def LSI_similarity_for_file(header_file):
    lsa_matrix = get_LSI_matrix(header_file)
    code_elements = header_file.code_elements
    result = np.zeros((len(code_elements), len(code_elements)))
    for i in range(len(code_elements)):
        for j in range(i+1, len(code_elements)):
            w = np.dot(lsa_matrix[i], lsa_matrix[j]) / (np.linalg.norm(lsa_matrix[i]) * np.linalg.norm(lsa_matrix[j]))
            if not (check_anonymous_enum(code_elements[i]) or check_anonymous_enum(code_elements[j])):
                result[i, j] = w
                result[j, i] = w
    return np.nan_to_num(result)

