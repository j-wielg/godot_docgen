#!/usr/bin/env python3

import sys
import re


def parse_for_value(line: str, key: str, start=0):
    '''
    Looks for the [key="value"] format in a .tscn file, and returns the value
    '''
    start = line.find(key + '="')
    if start < 0:
        return None
    start += len(key) + 2
    end = line.find('"', start)
    return line[start:end]


class Node:
    '''
    A node within a Godot scene tree
    '''
    children: list
    parent = None
    script: str = None
    name: str
    node_type: str

    def __init__(self, tscn_data: str):
        '''
        Generates a node from a line in a tscn file
        '''
        self.children = []
        self.name = parse_for_value(tscn_data, "name")
        self.node_type = parse_for_value(tscn_data, "type")
        parents = parse_for_value(tscn_data, "parent")
        if parents is not None:
            self.parent = parents.split('/')[-1]
        else:
            self.parent = parents


class Scene:
    '''
    Represents an entire scene in godot
    '''

    tree: Node = None
    ignore: re.Pattern

    def __init__(self, **kwargs):
        pattern = kwargs.get('ignore', '')
        self.ignore = re.compile(pattern)

    def parse_file(self, path: str):
        '''
        Generates a scene object by parsing a Godot generated .tscn file.
        '''
        scripts: dict[str, str] = {}
        nodes: dict[str, Node] = {}
        parsing_node_properties: bool = False
        cur_node: Node = None
        with open(path, 'r') as f:
            for line in f:
                # Parses node properties
                if parsing_node_properties:
                    line = line.strip()
                    if not line:
                        parsing_node_properties = False
                        continue
                    if not line.startswith('script'):
                        continue
                    start = len('script = ExtResource("')  # )
                    end = line.find('"', start)
                    cur_node.script = line[start:end]
                # Parses nodes and scripts
                if not line.startswith("["):  # ]
                    continue
                line = line.strip()[1:-1]
                # Checks for external scripts
                if line.startswith('ext_resource') and 'type="Script"' in line:
                    script_path = parse_for_value(line, "path")[6::]
                    scripts[parse_for_value(line, "id")] = script_path
                # Checks for other nodes
                elif line.startswith('node'):
                    name = parse_for_value(line, 'name')
                    if self.ignore.fullmatch(name) is not None:
                        continue
                    cur_node = Node(line)
                    nodes[cur_node.name] = cur_node
                    if cur_node.parent is None:
                        self.tree = cur_node
                    parsing_node_properties = True
        # Goes back through all the nodes to set node.children and such
        for node_name, node in nodes.items():
            # Resolves scripts
            if node.script is not None:
                node.script = scripts[node.script]
            # Resolves children and parents
            if node.parent == '.':
                node.parent = self.tree
                self.tree.children.append(node)
            elif node.parent in nodes:
                nodes[node.parent].children.append(node)
                node.parent = nodes[node.parent]

    def print_tree(self, stream=sys.stdout, node=None, depth=0):
        '''
        Prints the file structure of the scene to a file stream. Will generate
        a tree-like strucutre if rendered as a .rst file.
        '''
        if node is None:
            node = self.tree
        stream.write('|')
        if depth:
            stream.write(" " + "-" * (3 * depth))
        stream.write(f" {node.name}\n")
        for child in node.children:
            self.print_tree(stream, child, depth + 1)

    def test(self):
        pass
