from state import State
import definitions
from scenedef import SceneDef, NodeDef, ScenesNotParsed
from scriptdef import ScriptDef, ScriptGroups
from pathlib import Path
import utils


def generate_documentation():
    '''
    The main entry point for programs using this module.
    '''
    # Holds the settings data and other global stuff
    state = State()
    # Loads files into the state object
    load_files(state)
    # Generates rst for classes


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
    path = state.path
    unvisited: list[Path] = [path]
    xml: set[Path] = set()
    tscn: list[Path] = []
    # Finds all relevant files
    utils.print_log(
        f'Searching {str(path)} for files...',
        state
    )
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
    utils.print_log(
        f'Parsing {len(xml)} xml files...',
        state
    )
    for script_path in xml:
        script = ScriptDef(state)
        script.parse_file(str(script_path))
    # Generates scene objects and adds them to the state
    utils.print_log(
        f'Parsing {len(tscn)} scene files...',
        state
    )
    while tscn:
        skipped = 0
        size = len(tscn)
        for i in range(size - 1, -1, -1):
            scene_path = tscn[i]
            scene = SceneDef(state)
            try:
                scene.parse_file(scene_path)
            except ScenesNotParsed:
                skipped += 1
                continue
            scene_path = tscn.pop(i)
        if skipped == size:
            utils.print_error(f'Failed to parse {size} scenes:', state)
            for scene_path in tscn:
                utils.print_error(f'Could not parse {scene_path}', state)
            break
    # Attaches scenes to scripts
    utils.print_log(
        'Attaching scripts to scenes...',
        state
    )
    for scene_path in state.scenes:
        scene: SceneDef = state.scenes[scene_path]
        scene.connect_scripts()


def document_classes(state: State):
    '''
    Generates RST documentation for all of the classes.

    Creates a .rst file for each class

    Paramters
    ---------
    state : State
        The state of the program
    '''
    pass
