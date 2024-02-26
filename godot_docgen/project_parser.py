#!/usr/bin/env python3

from scene import Scene, Node
from pathlib import Path
from script import Script
import xml.etree.ElementTree as ET

DEFAULT_PATH: str = '../project'
CONFIG_PATH: str = '../docgen_ignore.json'


class GodotFileParser:
    '''
    Parses a Godot project to search for gdscript xml docs and scene scripts.
    The parser returns a dictionary of scenes, nodes, and gdscript xml trees
    These are later used to render the .rst files which will be passed to
    Sphinx
    '''
    scripts: dict[str, Script]
    scenes: dict[str, Scene]
    source_path: Path

    def __init__(self, **kwargs):
        path = kwargs.get('path', DEFAULT_PATH)
        self.source_path = Path(path).resolve()
        self.scripts = {}
        self.scenes = {}

    def search_files(self):
        '''
        Helper function which searches for a project's xml doc files and .tscn
        files.
        '''
        frontier: list[Path] = [self.source_path]
        while frontier:
            path = frontier.pop()
            if path.is_dir():
                for file in path.iterdir():
                    frontier.append(file)
                continue
            if path.name.endswith('.tscn'):
                scene: Scene = Scene()
                scene.parse_file(str(path))
                scene_path = str(path).removeprefix(str(self.source_path))
                scene_path = scene_path.strip('/').strip('\\')
                self.scenes[scene_path] = scene
            elif path.name.endswith('.xml'):
                script_path = str(path).removeprefix(str(self.source_path))
                script_path  = script_path.strip('/').strip('\\')
                self.scripts[script_path] = None
