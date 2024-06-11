import os
import argparse
import ast
import random
import builtins

all_f_code = ""

class FunctionCallChecker(ast.NodeVisitor):
    def __init__(self):
        self.has_function_call = False
        self.calls = []
        self.imports = set()

    # def visit_Import(self, node):
    #     for alias in node.names:
    #         self.imports.add(alias.name)
    #     self.generic_visit(node)

    # def visit_ImportFrom(self, node):
    #     module = node.module
    #     for alias in node.names:
    #         self.imports.add(f"{module}.{alias.name}")
    #     self.generic_visit(node)

    def visit_Call(self, node):
        self.has_function_call = True
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name):
                full_call = f"{value.id}.{node.func.attr}"
                self.calls.append(full_call)
            else:
                self.calls.append(node.func.attr)
        self.generic_visit(node)


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
    
    def extract_function_declarations_and_import_statements(self, file_path):
        with open(file_path, 'r') as f:
            code = f.read()
        
        tree = ast.parse(code)
        self.functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        self.imports = [node.module if isinstance(node, ast.ImportFrom) else alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names]
        self.import_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]


        
        return self.functions, self.imports, self.import_nodes
    
    def has_function_call(self, function_node):
        checker = FunctionCallChecker()
        checker.visit(function_node)
        return checker.has_function_call
    
    def return_function_calls(self, function_node):
        checker = FunctionCallChecker()
        checker.visit(function_node)
        
        return checker.calls
    
    def is_integer_function(self, function_node):
        global all_f_code
        # Check if all arguments are annotated as integers
        for arg in function_node.args.args:
            if arg.annotation:
                if not isinstance(arg.annotation, ast.Name) or arg.annotation.id != 'int':
                    return False
            else:
                # TODO: probably don't need to handle it anymore since it seems to have been handled in the returns logic
                # return False  # TODO: write appropriate logic to handle case when "not arg.annotation"
                # TODO: wherever in the function you get this variable name, add a node to check the type of the variable using the type() function call. Then unparse that node and check if the output is int. If not int, return False
                pass
                
                
        # Check if the return type is annotated as integer
        if function_node.returns:
            if not isinstance(function_node.returns, ast.Name) or function_node.returns.id != 'int':
                return False
        else:
            f_src = (ast.unparse(function_node))
            n_args = len(function_node.args.args)
            random_args = [str(random.randint(0, 100)) for _ in range(n_args)]
            f_call = f"{function_node.name}({', '.join(random_args)})"
            result = None

            try:
                result = eval(f_call)       # Execute the function call and get the result
            except:
                return False                # if any error occured during the execution of the function, then it must be because of passing integer arguments to the function. Here we are assuming that the projects from which we are deriving our functions for the database, has syntactically correct functions.

            if(isinstance(result, int)):
                return True
            else:
                return False
            
        
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract python files")
    parser.add_argument("-p", "--path", help="Path to the folder to read files from", required=True)
    args = parser.parse_args()

    extractor = FunctionExtractor()

    files = extractor.extract_python_files(args.path)  # contains the path to all python files within a folder
    function_database = []

    for file in files:
        functions, imports, import_nodes = extractor.extract_function_declarations_and_import_statements(file)
        # all_import_code = "\n".join(ast.unparse(node) for node in import_nodes)
        # all_f_code = "\n".join(ast.unparse(function) for function in functions)
        # all_code = all_import_code + "\n" + all_f_code
        exec(all_f_code)            # Define the function in the current context

        if functions:
            for function in functions:
                # print(function.name)
                # print(ast.dump(function, indent=4))
                if extractor.is_integer_function(function):
                    if extractor.has_function_call(function):
                        calls = extractor.return_function_calls(function)
                        builtins_set = set(dir(builtins))
                        for call in calls:
                            # print(calls)
                            # print(imports)
                            if (call in builtins_set):
                                # print(f"Function call within scope: {call}")
                                pass
                
                    function_database.append(function)

    for function in function_database:
        print(function.name)
            




'''
bare functions, class methods -> extract out both.
for functions it should be like below

def <function-name>(<parameter>*): | def <function-name>(<parameter>*) -> <return-type>: (if the return type is present we can directly check from here if it is an integer return type)

Will also have to check whether it is a class method or just a bare function. If it is bare function, we can add the function to our database directly. If class method, then, for now I am just rejecting it as right now I cannot think of anything that can convert (any) class method into a function
'''
