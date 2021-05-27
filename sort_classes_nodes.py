from typing import *
import pandas as pd
import libcst as cst
import re
import sys
import networkx as nx


def sort_classes_nodes(file_code: str):
    code_cst = cst.parse_module(file_code)
    transformer = TypingTransformer()
    modified_tree = code_cst.visit(transformer)
    return modified_tree.code


class CallGraphCollector(cst.CSTVisitor):
    def __init__(self):
        self._used_methods_list: List[str] = []

    def visit_Attribute(self, node: cst.Attribute):
        if hasattr(node, 'value') and hasattr(node.value, 'value') and node.value.value == 'self':
            self._used_methods_list.append(node.attr.value)

    def get_used_methods_list(self):
        return self._used_methods_list


class TypingTransformer(cst.CSTTransformer):
    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.CSTNode:
        if isinstance(original_node, cst.ClassDef):
            print('changing')
            new_body = updated_node.body.with_changes(body=self._sort_nodes(updated_node.body.body))
            updated_node_2 = updated_node.with_changes(body=new_body)
            return updated_node_2
        return updated_node

    def _sort_nodes(self, nodes_iterator: Iterable):
        functions_nodes_list = [node for node in nodes_iterator if isinstance(node, cst.FunctionDef)]
        not_functions_nodes_list = [node for node in nodes_iterator if not isinstance(node, cst.FunctionDef)]
        if functions_nodes_list:
            sorted_functions_nodes_list = self._get_sorted_functions_nodes_list(functions_nodes_list)
        else:
            sorted_functions_nodes_list = []
        if not_functions_nodes_list:
            not_functions_nodes_list[0] = not_functions_nodes_list[0].with_changes(leading_lines=[])
            if sorted_functions_nodes_list:
                sorted_functions_nodes_list[0] = \
                    sorted_functions_nodes_list[0].with_changes(leading_lines=[
                        self._create_empty_line()])
        elif sorted_functions_nodes_list:
            sorted_functions_nodes_list[0] = sorted_functions_nodes_list[0].with_changes(leading_lines=[])
        sorted_functions_list = not_functions_nodes_list + sorted_functions_nodes_list
        return sorted_functions_list

    def _get_sorted_functions_nodes_list(self, functions_nodes_list):
        df = self._get_func_names_with_distances_from_root_source(functions_nodes_list)
        df['inverse_distance'] = df['distance'].max() - df['distance']
        df['is_magic'] = df['func_name'].str.startswith('__') & df['func_name'].str.endswith('__')
        df['is_public'] = ~df['func_name'].apply(lambda x: re.search('^_[a-zA-Z]', x) is not None)
        df_2 = df.sort_values(['is_magic', 'is_public', 'inverse_distance'], ascending=False)
        print(df_2[['func_name', 'used_functions', 'is_magic', 'is_public', 'distance']])
        sorted_functions_nodes_list = df_2['node'].tolist()
        return sorted_functions_nodes_list

    def _get_func_names_with_distances_from_root_source(self, class_nodes_iter):
        func_df = self._get_calls_df(class_nodes_iter)
        self._add_used_functions(func_df)
        root = 'root'
        directed_graph = self._create_directed_call_graph(func_df, root)
        self._add_distances(func_df, directed_graph, root)
        return func_df

    @staticmethod
    def _add_distances(func_df, directed_graph, root):
        func_df['distance'] = func_df['func_name'].apply(
            lambda y: len(max(nx.all_simple_paths(directed_graph, root, y), key=lambda x: len(x))) - 1)

    @staticmethod
    def _create_directed_call_graph(func_df, root):
        directed_graph = nx.DiGraph()

        directed_graph.add_node(root)
        for index, row in func_df.iterrows():
            directed_graph.add_node(row['func_name'])
        for index, row in func_df.iterrows():
            directed_graph.add_edge(root, row['func_name'])
            for called_func in row['used_functions']:
                directed_graph.add_edge(row['func_name'], called_func)

        return directed_graph

    @staticmethod
    def _add_used_functions(func_df):
        func_names_list = func_df.func_name.tolist()
        func_df['used_functions'] = func_df['used_objects'].apply(lambda x: list(set(x).intersection(func_names_list)))

    @staticmethod
    def _get_calls_df(class_nodes_iter):
        call_graph = []
        for node in class_nodes_iter:
            if isinstance(node, cst.FunctionDef):
                collector = CallGraphCollector()
                node.visit(collector)
                used_methods_list = collector.get_used_methods_list()
                call_graph.append((node.name.value, node, used_methods_list))
        func_df = pd.DataFrame(call_graph, columns=['func_name', 'node', 'used_objects'])
        return func_df

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
        print("usage: sort_classes_nodes.py input_file_path output_file_path")
    else:
        read_file_path = sys.argv[1]
        write_file_path = sys.argv[2]
        original_code = open(read_file_path, 'r').read()

        modified_code = sort_classes_nodes(original_code)

        open(write_file_path, 'w').write(modified_code)
