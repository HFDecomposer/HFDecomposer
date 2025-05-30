

# Code element in header file
class CodeElement(object):
   
    def __init__(self, node):
        self.type = node.type
        self.start = node.start_point
        self.end = node.end_point
        self.name = ''
        self.new_name = []
        # this code element --use--> other code element in the same file
        self.reference = set()
        # only declaration: --use--> other code element in the same file
        self.invocation = set()
        # this code element --use--> other h file
        self.include = set()
        # c file --use--> this code element
        self.referenced_by = set()
        # other code element in other h file --use--> this code element
        self.referenced_by_hce = dict()

    
    def get_subwords_from_name(self):
        underline_subwords = self.name.split('_')
        for subword in underline_subwords:
            # if all characters in subword are capital letters, turn it into lower case
            if subword.isupper():
                self.subwords.add(subword.lower())
            else:
                # split subword as camel case
                last = 0
                for i in range(1, len(subword)):
                    if subword[i].isupper():
                        self.subwords.add(subword[last:i])
                        last = i
                        break
                self.subwords.add(subword[last:])
        # print(self.subwords)


# header file: define->code element, included_by->c/h file; 
class HeaderFile(object):
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.code_content = []
        self.code_elements = []
        self.new_names = dict()
        self.included_by = set()
        self.include = set()
        
    def add_code_element(self, code_element):
        if code_element.name in ["int", "char", "long", "unsigned", "struct", "label"]:
            return
        for ce in self.code_elements:
            if ce.name == code_element.name and ce.type == code_element.type:
                return
        self.code_elements.append(code_element)
        for name in code_element.new_name:
            self.new_names[name] = code_element

            
    def print_code_elements(self):
        print("count: "+ str(len(self.code_elements)))
        for ce in self.code_elements:
            print(ce.type + "\t" + ce.name + ":\t", end='')
            for rce in ce.reference:
                print(rce.type + "\t" + rce.name + ",", end=' ')
            print("\n")