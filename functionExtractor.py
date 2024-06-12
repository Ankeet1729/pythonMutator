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

    def visit_Call(self, node):
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
    def extract_python_files(self, folder_path):
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
        return all_files
    
    def extract_function_declarations(self, file_path):
        with open(file_path, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        self.functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        return self.functions
    
    def has_function_call(self, function_node, function_return_types):
        checker = FunctionCallChecker(function_return_types)
        checker.visit(function_node)
        return checker.has_function_call
    
    def return_function_calls(self, function_node, function_return_types):
        checker = FunctionCallChecker(function_return_types)
        checker.visit(function_node)
        return checker.calls
    
    def is_integer_function(self, function_node):
        flag = False
        for arg in function_node.args.args:
            if not arg.annotation:
                return False
        if not function_node.returns:
            return False

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

    def visit_Call(self, node):
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

def extract_function_return_types(functions):
    return_types = {}
    for function in functions:
        if function.returns and isinstance(function.returns, ast.Name):
            return_types[function.name] = function.returns.id
        else:
            return_types[function.name] = "Unknown"
    return return_types

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract python files")
    parser.add_argument("-p", "--path", help="Path to the folder to read files from", required=True)
    args = parser.parse_args()

    extractor = FunctionExtractor()
    files = extractor.extract_python_files(args.path)
    function_database = []

    all_functions = []
    for file in files:
        functions = extractor.extract_function_declarations(file)
        all_functions.extend(functions)
    
    function_return_types = extract_function_return_types(all_functions)

    for function in all_functions:
        flag = True
        if extractor.is_integer_function(function):
            if extractor.has_function_call(function, function_return_types):
                calls = extractor.return_function_calls(function, function_return_types)
                builtins_set = set(dir(builtins))
                for call, return_type in calls:
                    if call not in builtins_set:
                        value_to_be_replaced = None
                        if return_type != "Unknown":
                            value_to_be_replaced = sample_values[return_type]
                            # Replace the function call with the sample value
                            replacer = CallReplacer(function_return_types)
                            function = replacer.visit(function)
                        else:
                            flag = False
            if flag:
                function_database.append(function)

    for function in function_database:
        print((function).name)




# TODO: check the Django error
