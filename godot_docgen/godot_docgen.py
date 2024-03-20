from state import State
import definitions
from scenedef import SceneDef, NodeDef, ScenesNotParsed
from scriptdef import ScriptDef, ScriptGroups
from pathlib import Path


def generate_documentation():
    '''
    The main entry point for programs using this module.
    '''
    # Holds the settings data and other global stuff
    state = State()


def load_files(state: State):
    '''
    Uses depth-first search to search through an entire file tree
    for .tscn and .xml files, generating ScriptDef and SceneDef
    objects.

    Parameters
    ----------
    path : pathlib.Path
        Path to the root of the Godot project to document.
    '''
    path = state.settings['path']
    unvisited: list[Path] = [path]
    xml: set[Path] = set()
    tscn: list[Path] = []
    # Finds all relevant files
    while unvisited:
        file = unvisited.pop()
        filename = file.name
        # Finds the xml files
        if filename.endswith('.xml'):
            xml.add(file)
        # Finds the scene files
        elif filename.endswith('.tscn'):
            tscn.append(file)
        # Opens folders
        if file.is_dir():
            for subfile in file.iterdir():
                unvisited.append(subfile)
    # Generates all script files and adds them to the state
    for script_path in xml:
        script = ScriptDef(state)
        script.parse_file(str(script_path))
    # Generates scene objects and adds them to the state
    while tscn:
        scene_path = tscn.pop()
        scene = SceneDef(state)
        try:
            scene.parse_file(scene_path)
        except ScenesNotParsed:
            tscn.insert(0, scene_path)
            continue
    for scene_path in state.scenes:
        scene: SceneDef = state.scenes[scene_path]
        scene.connect_scripts()
