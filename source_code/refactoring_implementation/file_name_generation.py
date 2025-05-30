from openai import OpenAI   
import os
from refactoring_implementation.utils import string_content

def generate_name_for_one_file(file_content, key, URL):
    os.environ["HTTP_PROXY"] = URL
    os.environ["HTTPS_PROXY"] = URL
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": "Please generate a name for the following code file. Make sure that the name is end with .h. Only return the file name! No explaination! \n File content: \n"+ file_content ,
            }
        ],
        temperature=0,
        stream=False
    )

    name = response.choices[0].message.content
    # name = response.choices[0]['message']['content']
    print(name)
    # print(file_content)
    return name


def generate_file_names(target_header_file, community_index, use_gpt, key, URL):

    if not use_gpt:
        header_file_name = target_header_file.file_path.split(os.sep)[-1]
        file_names = []
        for i in range(max(community_index.values())+1):
            file_names.append("sub_" + header_file_name.replace(".h", "") + "_" + str(i) + ".h")
        return file_names

    file_contents = []
    for i in range(max(community_index.values())+1):
        file_contents.append("")
    for ce in target_header_file.code_elements:
        index = community_index[ce.name+'+'+ce.type]
        ce_content = string_content(target_header_file.code_content, ce.start, ce.end)
        file_contents[index] += ce_content
    
    file_names = []
    for file_content in file_contents:
        file_name = generate_name_for_one_file(file_content, key, URL)
        if file_name in file_names:
            file_name = file_name.replace(".h", "_1.h")
        file_names.append(file_name)
    return file_names
    