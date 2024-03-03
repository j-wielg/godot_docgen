#!/usr/bin/env python3

import sys
import io
import re
from definitions import DefinitionBase, SignalDef, TypeName
from scriptdef import ScriptDef
from state import State


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


class NodeDef(DefinitionBase):
    '''
    Used to document a node within a Godot scene.

    Attributes
    ----------
    children : list[NodeDef]
        A list of children of the node.
    parent : Optional[NodeDef]
        The parent of the node in the scene tree.
    script_id : Optional[str]
        The resource id of the script attached to the node.
    script : Optional[ScriptDef]
        Stores documentation data for the node's script.
    type_name : TypeName
        The type of the node
    state : State
    '''
    children: list['NodeDef']
    parent: 'NodeDef' = None
    script_path: str = None
    script: ScriptDef = None
    type_name: TypeName = None
    state: State

    def __init__(self, state: State):
        self.children = []
        self.state = state

    def from_tscn_file(self, tscn_data: list[str]):
        '''
        Documents a node using data from a .tscn file.

        Parameters
        ----------
        tscn_data : list[str]
            A list of strings corresponding to the description of the node
            in the .tscn file. The first line takes the form
            [node name='name' ...]
            and the other lines are key-value pairs
        '''
        super().__init__('node', parse_for_value(tscn_data[0], "name"))
        node_type = parse_for_value(tscn_data[0], "type")
        self.type_name = TypeName(node_type)
        parents = parse_for_value(tscn_data[0], "parent")
        if parents is not None:
            self.parent = parents.split('/')[-1]
        else:
            self.parent = parents


class SceneDef:
    '''
    Documents a scene tree in Godot.

    Parameters
    ----------
    state : State
        The global state of the document generation script.

    Attributes
    ----------
    root : NodeDef
        The root of the scene tree.
    state : State
        The state of the parsing program.
    '''
    root: NodeDef
    state: State

    def __init__(self, state: State):
        self.state = state

    def parse_file(self, scene_file: io.TextIOWrapper):
        '''
        Fills out the scene's attributes by parsing a .tscn file.

        Parameters
        ----------
        scene_file : io.TextIOWrapper
            The .tscn file containing the scene data.

        Warnings
        --------
        This function will modify the state object.
        '''
        # Stores the scripts attached to each node
        # scripts['id'] = script_path
        scripts: dict[str, str] = {}
        nodes: dict[str, NodeDef] = {}
        # Loops through the lines in the .tscn file
        for line in scene_file:
            if line.startswith('['):  # ]
                line = line[1:-1]
                if line.startswith('ext_resource'):
                    resource_type = parse_for_value(line, 'type')
                    if resource_type == 'Script':
                        script_id = parse_for_value(line, 'id')
                        scripts[script_id] = parse_for_value(line, 'path')[6:]
                elif line.startswith('node'):
                    node_lines = [line]
                    while (node_line := scene_file.readline().strip()):
                        node_lines.append(node_line)
                    node = NodeDef(self.state)
                    node.from_tscn_file(node_lines)
                    nodes[node.name] = node
