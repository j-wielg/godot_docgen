from state import State
import definitions
from scenedef import SceneDef, NodeDef
from scriptdef import ScriptDef, ScriptGroups
from pathlib import Path


def generate_documentation():
    '''
    The main entry point for programs using this module.
    '''
    # Holds the settings data and other global stuff
    state = State()


def load_files(self, state: State, path: Path):
    '''
    Uses depth-first search to search through an entire file tree
    for .tscn and .xml files, generating ScriptDef and SceneDef
    objects.

    Parameters
    ----------
    path : pathlib.Path
        Path to the root of the Godot project to document.
    '''
    unvisited: list[Path] = [path]
    xml: set[str] = set()
    tscn: set[str] = set()
    # Finds all relevant files
    while unvisited:
        file = unvisited.pop()
        filename = file.name
        # Finds the xml files
        if filename.endswith('.xml'):
            xml.add(str(file))
        # Finds the scene files
        elif filename.endswith('.tscn'):
            tscn.add(str(file))
        # Opens folders
        if file.is_dir():
            for subfile in file.iterdir():
                unvisited.append(subfile)

    # Generates all script files and adds them to the state
    for script_path in xml:
        script = ScriptDef(state)
        script.parse_file(script_path)
    # Generates scene objects and adds them to the state
    for scene_path in tscn:
        scene = SceneDef(state)
        with open(scene_path, 'rt') as scene_file:
            scene.parse_file(scene_file)
