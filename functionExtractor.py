import os
import argparse
import ast

class FunctionExtractor:
    def extract_python_files(self, folder_path):
        all_files = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if not (file.endswith(".py")):
                    continue
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                
        return all_files
    
    def extract_function_declarations(self, file_path):
        with open(file_path, 'r') as f:
            code = f.read()
        
        tree = ast.parse(code)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        return functions
    
    def is_integer_function(self, function_node):
        # Check if all arguments are annotated as integers
        for arg in function_node.args.args:
            if arg.annotation:
                if not isinstance(arg.annotation, ast.Name) or arg.annotation.id != 'int':
                    return False
            else:
                return False  # TODO: write appropriate logic to handle case when "not arg.annotation"
                
        # Check if the return type is annotated as integer
        if function_node.returns:
            if not isinstance(function_node.returns, ast.Name) or function_node.returns.id != 'int':
                return False
        else:
            return False  # TODO: write appropriate logic to handle case when "not function_node.returns"
            
        
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract python files")
    parser.add_argument("-p", "--path", help="Path to the folder to read files from", required=True)
    args = parser.parse_args()

    extractor = FunctionExtractor()

    files = extractor.extract_python_files(args.path)  # contains the path to all python files within a folder
    function_database = []

    for file in files:
        functions = extractor.extract_function_declarations(file)
        if functions:
            for function in functions:
                # print(ast.dump(function, indent=4))
                if extractor.is_integer_function(function):
                    function_database.append(function)

    for function in function_database:
        print(function.name)
            




'''
bare functions, class methods -> extract out both.
for functions it should be like below

def <function-name>(<parameter>*): | def <function-name>(<parameter>*) -> <return-type>: (if the return type is present we can directly check from here if it is an integer return type)

Will also have to check whether it is a class method or just a bare function. If it is bare function, we can add the function to our database directly. If class method, then, for now I am just rejecting it as right now I cannot think of anything that can convert (any) class method into a function
'''