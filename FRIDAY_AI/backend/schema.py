"""Inline local Pydantic references so tool schemas work with more Ollama models."""
from copy import deepcopy

def inline_schema(schema:dict) -> dict:
    schema=deepcopy(schema)
    definitions=schema.pop('$defs',{})
    def visit(node,stack=()):
        if isinstance(node,list):return [visit(x,stack) for x in node]
        if not isinstance(node,dict):return node
        ref=node.get('$ref')
        if isinstance(ref,str) and ref.startswith('#/$defs/'):
            name=ref.split('/')[-1]
            if name in stack or name not in definitions: return node
            result=visit(deepcopy(definitions[name]),stack+(name,))
            result.update({k:visit(v,stack) for k,v in node.items() if k!='$ref'})
            return result
        return {k:visit(v,stack) for k,v in node.items()}
    return visit(schema)
