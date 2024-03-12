#!/usr/bin/env python3

import sys
import io
import re
from definitions import DefinitionBase, SignalDef, TypeName, MethodDef
from scriptdef import ScriptDef
from state import State
from typing import Optional, Union

# Regular expressions
match_subres = re.compile(r'([^ ]+) = SubResource\("(.+?)"\)')
match_extres = re.compile(r'([^ ]+) = ExtResource\("(.+?)"\)')


def parse_for_value(line: str, key: str, start=0) -> str:
    '''
    Looks for the [key="value"] format in a .tscn file, and returns the value
    '''
    pattern = re.compile(f' {key}=(".+?"|\d+)')
    value = pattern.search(line).group(1)
    if '"' in value:
        return value.strip('"')
    else:
        return int(value)


def tscn_to_dict(line: str) -> dict:
    '''
    Turns a resource line in a .tscn file into a dictionary
    '''
    pattern = re.compile(r'(\w+)=(".+?"|\d+|ExtResource\(".+?"\))')
    pairs = pattern.findall(line.strip())
    d = {}
    for key, value in pairs:
        if '"' in value:
            value = value.strip('"')
        else:
            value = int(value)
        d[key] = value
    return d


class ConnectionDef(DefinitionBase):
    '''
    Documents an instantiated signal in a scene.

    Attributes
    ----------
    emitters : list[NodeDef]
        Nodes which emit this signal.
    receivers : list[(NodeDef, Union[str, MethodDef])]
        A list containing the nodes which receive the signal, and the method
        that they use as a signal handler.
    signal : SignalDef
        The signal that this object represents.
    '''
    emitters: list['NodeDef']
    receivers: list[tuple['NodeDef', Union[str, MethodDef]]]
    signal: SignalDef

    def __init__(self):
        self.emitters = []
        self.receivers = []


class NodeDef(DefinitionBase):
    '''
    Used to document a node within a Godot scene.

    Attributes
    ----------
    children : list[NodeDef]
        A list of children of the node.
    parent : Optional[NodeDef]
        The parent of the node in the scene tree.
    script_path : Optional[str]
        Path to the script attached to this node, if one exists.
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
    resources: list

    def __init__(self, state: State):
        self.children = []
        self.state = state
        self.resources = {}
        self.definition_name = 'node'
        self.resources = []

    def from_tscn_file(
            self,
            file: io.TextIOWrapper,
            ext_res_map: dict[str, 'ResourceDef'],
            sub_res_map: dict[str, 'ResourceDef'],
            node_map: dict[str, 'NodeDef'],
            line: str = None):
        '''
        Generates a node's documentation from a tscn file.

        Parameters
        ----------
        file : io.TextIOWrapper
            An open filestream for a .tscn file, with the file head at a
            line which defines a node.
        ext_res_map : dict[str, ResourceDef]
            Maps a resource id to an external resource.
        sub_res_map : dict[str, ResourceDef]
            Maps a resource id to an internal resource.
        node_map : dict[str, NodeDef]
            Maps the name of a node to its NodeDef object
        line: str, default = None
            The first line of the node definition.
        '''
        if line is None:
            line = file.readline()
        if not line.startswith('[node'):  # ]
            return line
        # Gets the node's name
        node_info = tscn_to_dict(line)
        super().__init__('node', node_info['name'])
        # Sets the node's parent
        if (parent := node_info.get('parent')) is not None:
            self.parent = node_map[parent]
            node_map[parent].children.append(self)
            if parent != '.':
                path = f'{parent}/{self.name}'
            else:
                path = self.name
            node_map[path] = self
        # Gets the node's type
        type_name: str = node_info.get('type')
        if type_name is not None:
            self.type_name = TypeName(type_name)
        # If there is no type, then it is an instance of a scene
        else:
            self.definition_name = 'scene'
            id = node_info['instance']
            start = id.find('"') + 1
            end = id.find('"', start)
            id = id[start:end]
            path = ext_res_map[id].path
            type_name = path.split('/')[-1]
            print(path)
            if not type_name.endswith('.tscn'):
                # TODO: Raise exception
                return
            self.type_name = TypeName(type_name[:-5])
        # Reads the rest of the lines
        while line := file.readline().strip():
            # Checks for scripts
            if 'script' in line:
                try:
                    id = match_extres.search(line)[2]
                except TypeError:
                    print('ERROR: The program does not match internal scripts')
                    continue
                self.script_path = ext_res_map[id].path
            # Checks for external resources
            elif 'ExtResource' in line:
                id = match_extres.search(line)[2]
                self.resources.append(ext_res_map[id])
            # Checks for internal resources
            elif 'SubResource' in line:
                id = match_subres.search(line)[2]
                self.resources.append(sub_res_map[id])
        return None


class SceneDef(DefinitionBase):
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
    external_scenes: dict[str, Optional["SceneDef"]]
    signals: dict[str, ConnectionDef]

    def __init__(self, state: State):
        self.state = state
        self.definition_name = 'scene'
        self.signals = {}

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
        # Stores all of the external resources
        ext_resources: dict[str, ResourceDef] = {}
        # Stores all of the internal resources
        sub_resources: dict[str, ResourceDef] = {}
        # Grabs the first line of the file to make sure it is using Godot 4
        line = scene_file.readline()
        tscn_version = parse_for_value(line, 'format')
        if tscn_version != 3:
            # TODO: Print an error message
            return
        line = scene_file.readline()
        current = ''
        # Locates external resources
        while line:
            if line.startswith('[ext_resource'):  # ]
                resource = ResourceDef()
                resource.from_tscn_data(line)
                id = parse_for_value(line, 'id')
                ext_resources[id] = resource
            elif line.startswith('['):  # ]
                current = ''
                break
            elif current:
                pass
            line = scene_file.readline()
        # Locates internal resources
        while line:
            if line.startswith('[sub_resource'):  # ]
                resource = ResourceDef()
                resource.from_tscn_data(line)
                id = parse_for_value(line, 'id')
                sub_resources[id] = resource
                current = id
            elif line.startswith('['):  # ]
                current = ''
                break
            elif current and 'ExtResource' in line:
                match = match_extres.search(line.strip())
                resource = ext_resources.get(match[2])
                if resource is not None:
                    sub_resources[current].sub_resources.append(resource)
                else:
                    # TODO: Error
                    print(f'ERROR: Resource with id {match[2]} does not exist')
                    return
            elif current and 'SubResource' in line:
                match = match_subres.search(line.strip())
                resource = sub_resources.get(match[2])
                if resource is not None:
                    sub_resources[current].sub_resources.append(resource)
                else:
                    print(f'ERROR: Resource with id {match[2]} does not exist')
                    return
            line = scene_file.readline()
        # Gets the root node
        if not line.startswith('[node'):  # ]
            # TODO: print error
            return
        nodes: dict[str, NodeDef] = {}
        node: NodeDef = NodeDef(self.state)
        node.from_tscn_file(scene_file, ext_resources, sub_resources, nodes, line)
        nodes['.'] = node
        self.root = node
        super().__init__('scene', self.root.name)
        # Gets the other nodes
        while True:
            node: NodeDef = NodeDef(self.state)
            line = node.from_tscn_file(scene_file, ext_resources, sub_resources, nodes)
            if line is not None:
                break
        while line:
            if not line.startswith('[connection'):  # ]
                line = scene_file.readline()
                continue
            signal_info = tscn_to_dict(line)
            if 'signal' not in signal_info:
                line = scene_file.readline()
                continue
            if signal_info['signal'] in self.signals:
                signal = self.signals[signal_info['signal']]
            else:
                signal = ConnectionDef()
                signal.definition_name = 'signal'
                signal.name = signal_info['signal']
                self.signals[signal.name] = signal
            emitter = nodes.get(signal_info['from'])
            receiver = nodes.get(signal_info['to'])
            if emitter is not None and receiver is not None:
                signal.emitters.append(emitter)
                signal.receivers.append((receiver, signal_info['method']))
            line = scene_file.readline()


class ResourceDef(DefinitionBase):
    '''
    Documents a Godot resource within a scene file.

    Attributes
    ----------
    path : str
        Path to the resource from res://, if it is external
    type_name : TypeName
        The type of resource.
    sub_resources : list[ResourceDef]
        Any subresources contained within the resource.
    is_external : bool
        Whether or not it is an external resource.
    '''
    path: Optional[str] = None
    type_name: TypeName
    sub_resources: list['ResourceDef']
    is_external: bool

    def __init__(self):
        self.sub_resources = []
        self.definition_name = 'resource'

    def from_tscn_data(self, line: str):
        '''
        Generates attributes from the line where the resource is defined
        in a .tscn file.

        Parameters
        ----------
        line : str
            The line in a tscn file which defines the resource.
        '''
        self.is_external = 'ext_resource' in line
        info = tscn_to_dict(line)
        # Gets the path
        if self.is_external:
            self.path = info.get('path')
        # Gets the type info
        self.type_name = TypeName(info['type'])
