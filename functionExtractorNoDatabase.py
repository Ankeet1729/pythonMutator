import mysql.connector

import os
import argparse
import ast
import random
import builtins
import datetime
import collections
import types
import re
import pathlib
import decimal
import fractions
import functools

sample_values = {
    'int': 42,
    'float': 3.14,
    'str': 'example string',
    'bool': True,
    'NoneType': None,
    'list': [1, 2, 3, 'a', 'b', 'c'],
    'dict': {'key1': 'value1', 'key2': 42},
    'set': {1, 2, 3, 'a', 'b', 'c'},
    'tuple': (1, 2, 3, 'a', 'b', 'c'),
    'bytes': b'example bytes',
    'bytearray': bytearray(b'example bytearray'),
    'range': range(5),
    'complex': 1+2j,
    'frozenset': frozenset([1, 2, 3, 'a', 'b', 'c']),
    'datetime': datetime.datetime.now(),
    'date': datetime.date.today(),
    'time': datetime.datetime.now().time(),
    'timedelta': datetime.timedelta(days=1),
    'memoryview': memoryview(b'example memoryview'),
    'deque': collections.deque([1, 2, 3, 'a', 'b', 'c']),
    'namedtuple': collections.namedtuple('Point', ['x', 'y'])(1, 2),
    'defaultdict': collections.defaultdict(int, {'key1': 1, 'key2': 2}),
    'Counter': collections.Counter(['a', 'b', 'c', 'a', 'b', 'b']),
    'OrderedDict': collections.OrderedDict([('key1', 'value1'), ('key2', 'value2')]),
    'types.FunctionType': (lambda x: x + 1),
    'types.LambdaType': (lambda x: x + 1),
    'types.BuiltinFunctionType': abs,
    'pattern': re.compile(r'\d+'),
    'match': re.match(r'\d+', '123abc'),
    'Path': pathlib.Path('/usr/bin'),
    'PosixPath': pathlib.PosixPath('/usr/bin'),
    'PurePath': pathlib.PurePath('/usr/bin'),
    'PurePosixPath': pathlib.PurePosixPath('/usr/bin'),
    'decimal.Decimal': decimal.Decimal('3.14'),
    'fractions.Fraction': fractions.Fraction(3, 4),
    'functools.partial': functools.partial(int, base=2),
    'map': map(str, [1, 2, 3]),
    'filter': filter(lambda x: x > 1, [0, 1, 2, 3]),
    'zip': zip([1, 2, 3], ['a', 'b', 'c']),
    'reversed': reversed([1, 2, 3]),
    'enumerate': enumerate(['a', 'b', 'c']),
    'generator': (x * x for x in range(10)),
}


class FunctionCallChecker(ast.NodeVisitor):
    def __init__(self, function_return_types):
        self.has_function_call = False
        self.calls = []
        self.imports = set()
        self.function_return_types = function_return_types

    def visit_Call(self, node):                             # stores the function name and the return type for each Call Node visited
        self.has_function_call = True
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name):
                func_name = f"{value.id}.{node.func.attr}"
            else:
                func_name = node.func.attr
        
        return_type = self.function_return_types.get(func_name, "Unknown")
        self.calls.append((func_name, return_type))
        self.generic_visit(node)

class FunctionExtractor:
    def __init__(self, exclude_integer_parameters=False):
        self.exclude_integer_parameters = exclude_integer_parameters

    def extract_python_files(self, folder_path):            # extracts python files from directory provided as argument
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
        return all_files
    
    def extract_function_declarations(self, file_path):     # extracts the functions found from the python file and returns their ast node    
        with open(file_path, 'r') as f:
            code = f.read()
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            print(f"Syntax error in file {file_path}: {e}")
            return []
        self.functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        return self.functions
    
    def has_function_call(self, function_node, function_return_types):      # checks if the function has another function call within it
        checker = FunctionCallChecker(function_return_types)
        checker.visit(function_node)
        return checker.has_function_call
    
    def return_function_calls(self, function_node, function_return_types):  # returns the function calls within a function
        checker = FunctionCallChecker(function_return_types)
        checker.visit(function_node)
        return checker.calls
    
    def is_integer_function(self, function_node):           # checks if the function has integer arguments and integer return type -> right now works accurately for annotated functions only
        flag = False
        if not self.exclude_integer_parameters:
            for arg in function_node.args.args:
                if not arg.annotation:
                    return False
                
        if not function_node.returns:
            return False
        
        if not self.exclude_integer_parameters:
            for arg in function_node.args.args:
                if arg.annotation:
                    if isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'int':
                        flag = True

        if function_node.returns:
            if isinstance(function_node.returns, ast.Name) and function_node.returns.id == 'int':
                flag = True
        return flag

class CallReplacer(ast.NodeTransformer):
    def __init__(self, function_return_types):
        self.function_return_types = function_return_types

    def visit_Call(self, node):                              # visits a Call node and changes the function call itself with a value from the dictionary mapping in sample_values
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name):
                func_name = f"{value.id}.{node.func.attr}"
            else:
                func_name = node.func.attr
        
        return_type = self.function_return_types.get(func_name, "Unknown")
        if return_type != "Unknown" and return_type in sample_values:
            value_to_replace = sample_values[return_type]
            return ast.copy_location(ast.Constant(value_to_replace), node)
        return self.generic_visit(node)

def extract_function_return_types(functions):                # returns the return type of the function node passed as an argument. If there is no annotation, then "Unknown" is returned
    return_types = {}
    for function in functions:
        if function.returns and isinstance(function.returns, ast.Name):
            return_types[function.name] = function.returns.id
        else:
            return_types[function.name] = "Unknown"
    return return_types

def extract_function_parameters(function_node):
    parameters = []
    
    for arg in function_node.args.args:
        param_name = arg.arg
        param_type = ast.unparse(arg.annotation) if arg.annotation else None
        parameters.append((param_name, param_type))
    
    if hasattr(function_node.args, 'kwonlyargs'):
        for arg in function_node.args.kwonlyargs:
            param_name = arg.arg
            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append((param_name, param_type))
   
    if function_node.args.vararg:
        vararg_name = function_node.args.vararg.arg
        vararg_type = ast.unparse(function_node.args.vararg.annotation) if function_node.args.vararg.annotation else None
        parameters.append((vararg_name, vararg_type))

    if function_node.args.kwarg:
        kwarg_name = function_node.args.kwarg.arg
        kwarg_type = ast.unparse(function_node.args.kwarg.annotation) if function_node.args.kwarg.annotation else None
        parameters.append((kwarg_name, kwarg_type))
    return parameters

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract python files")
    parser.add_argument("-p", "--path", help="Path to the folder to read files from", required=True)
    parser.add_argument('-e', '--exclude-integer-parameters', action='store_true', help='Exclude checking integer parameters while extracting functions')
    args = parser.parse_args()

    extractor = FunctionExtractor(exclude_integer_parameters=args.exclude_integer_parameters)
    files = extractor.extract_python_files(args.path)
    function_database = []

    all_functions = []
    for file in files:
        functions = extractor.extract_function_declarations(file)
        all_functions.extend(functions)
    
    function_return_types = extract_function_return_types(all_functions)

    for function in all_functions:
        flag = True
        if extractor.is_integer_function(function):                             # if function has integer return types and parameters
            if extractor.has_function_call(function, function_return_types):    # if function has function call within it
                calls = extractor.return_function_calls(function, function_return_types)
                builtins_set = set(dir(builtins))
                for call, return_type in calls:
                    if call not in builtins_set:                                # if the current call in question is not a builtin
                        value_to_be_replaced = None
                        if return_type != "Unknown":                            # if return type is not unknown then replace the call (if the datatype is in the sample_values dict)
                            try:
                                value_to_be_replaced = sample_values[return_type]
                            except:
                                flag = False
                            # Replace the function call with the sample value
                            replacer = CallReplacer(function_return_types)
                            function = replacer.visit(function)
                        else:                                                   # if not then this function is not included in the database
                            flag = False
            if flag:
                function_database.append(function)

    function_list = []

    for function in function_database:
        function_node = function
        dictionary = dict()
        dictionary["source"] = ast.unparse(function_node)
        dictionary["params"] = extract_function_parameters(function_node)
        function_list.append(dictionary)
        

# To access the source of a function --> function_list[<index>]["source"]
# To access the parameters of a function --> function_list[<index>]["params"]




"""
Drawbacks:
    1. The code currently works correctly only for those functions where the return type of the functions are annotated.
    2. If the -e flag is not provided, the parameters of the function also need to be annotated for the program to work correctly.
"""
