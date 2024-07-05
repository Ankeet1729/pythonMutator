import ast
import random

class Transformer(ast.NodeTransformer):
    def __init__(self):
        self.substitutions = []

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.FloorDiv):
            new_var = "_" + str(random.randint(1, 10000000))
            
            
            floor_div_source = f"{new_var} = {ast.unparse(node)}"
            self.substitutions.append(floor_div_source)
            
            
            new_assign = ast.Assign(
                targets=[ast.Name(id=new_var, ctx=ast.Store())],
                value=node
            )
            
            
            self.substitutions.append(new_assign)
            
            
            return ast.Name(id=new_var, ctx=ast.Load())
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        
        # Add all new assignments at the beginning of the module body
        new_body = []
        for substitution in self.substitutions:
            if isinstance(substitution, ast.Assign):
                new_body.append(substitution)
        
        new_body.extend(node.body)
        node.body = new_body
        
        return node


source_code = "a = 3 * 4 + (5 // 2 + 3)"
tree = ast.parse(source_code)
# print(ast.dump(tree, indent=4))

transformer = Transformer()
new_tree = transformer.visit(tree)
ast.fix_missing_locations(new_tree)


new_source_code = ast.unparse(new_tree)

print(new_source_code)
