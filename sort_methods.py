from typing import *
import pandas as pd
import libcst as cst
import re
import sys


def sort_methods(file_code: str):
    code_cst = cst.parse_module(file_code)
    transformer = TypingTransformer()
    modified_tree = code_cst.visit(transformer)
    return modified_tree.code


class TypingTransformer(cst.CSTTransformer):
    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.CSTNode:
        if isinstance(original_node, cst.ClassDef):
            print('changing')
            new_body = updated_node.body.with_changes(body=self._sort_functions(updated_node.body.body))
            updated_node_2 = updated_node.with_changes(body=new_body)
            return updated_node_2
        return updated_node

    def _sort_functions(self, nodes_iterator: Iterable):
        functions_nodes_list = [node for node in nodes_iterator if isinstance(node, cst.FunctionDef)]
        not_functions_nodes_list = [node for node in nodes_iterator if not isinstance(node, cst.FunctionDef)]
        if functions_nodes_list:
            df = pd.DataFrame([(node.name.value, node) for node in functions_nodes_list], columns=['func_name', 'body'])
            df['is_magic'] = df['func_name'].str.startswith('__') & df['func_name'].str.endswith('__')
            df['is_public'] = ~df['func_name'].apply(lambda x: re.search('^_[a-zA-Z]', x) is not None)
            df_2 = df.sort_values(['is_magic', 'is_public'], ascending=False)
            sorted_functions_nodes_list = df_2['body'].tolist()
        else:
            sorted_functions_nodes_list = []
        if not_functions_nodes_list:
            not_functions_nodes_list[0] = not_functions_nodes_list[0].with_changes(leading_lines=[])
            if sorted_functions_nodes_list:
                sorted_functions_nodes_list[0] = sorted_functions_nodes_list[0].with_changes(leading_lines=[
                    self._create_empty_line()])
        elif sorted_functions_nodes_list:
            sorted_functions_nodes_list[0] = sorted_functions_nodes_list[0].with_changes(leading_lines=[])
        sorted_functions_list = not_functions_nodes_list + sorted_functions_nodes_list
        return sorted_functions_list

    @staticmethod
    def _create_empty_line():
        return cst.EmptyLine(
            indent=True,
            whitespace=cst.SimpleWhitespace(
                value='',
            ),
            comment=None,
            newline=cst.Newline(
                value=None,
            ),
        )


if __name__ == "__main__":
    if len(sys.argv) not in [3]:
        print("usage: sort_methods.py input_file_path output_file_path")
    else:
        read_file_path = sys.argv[1]
        write_file_path = sys.argv[2]
        original_code = open(read_file_path, 'r').read()

        modified_code = sort_methods(original_code)

        open(write_file_path, 'w').write(modified_code)
