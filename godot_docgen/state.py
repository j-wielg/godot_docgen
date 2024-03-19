from typing import OrderedDict
from pathlib import Path


class State:
    '''
    Singleton which stores the global state of the parser program.
    If any method / function changes a value within this state, the
    change should be documented in the function's docstring.

    Attributes
    ----------
    num_errors : int
        The number of errors encountered
    num_warnings : int
        The number of warnings encountered
    classes : OrderedDict[str, ScriptDef]
        Stores the Godot project's classes. The keys are the name of the class,
        and the values are `ScriptDef` objects
    scripts : OrderedDict[str, ScriptDef]
        Stores scripts which are appended to scenes rather than defining their
        own classes.
    scenes : OrderedDict[str, SceneDef]
        Stores scene trees.
    settings : dict
        Stores the program's general settings.
    '''
    settings: dict

    def __init__(self) -> None:
        self.num_errors = 0
        self.num_warnings = 0
        self.classes: OrderedDict = OrderedDict()
        self.scripts: OrderedDict = OrderedDict()
        self.scenes: OrderedDict = OrderedDict()

    def config(self, settings: dict):
        '''
        Configures the State object with various settings.

        Parameters
        ----------
        settings : dict
            A dictionary containing the settings to configure. A full
            description of the available key-value pairs is found below.

        Notes
        -----
        This section contains a list of the accepted key-value pairs.
        path : pathlib.Path, default = Path('../project').resolve()
            Path to the Godot project to generate documentation for.
        output_path : pathlib.Path, default = Path('../rst_files').resolve()
            Path to a directory where the .rst files will be dumped.
        '''
        self.settings = settings
        if 'path' not in settings:
            self.settings['path'] = '../project'
        if 'output_path' not in settings:
            self.settings['output_path'] = '../rst_files'
        self.settings['path'] = Path(self.settings['path']).resolve()
        self.settings['output_path'] = Path(self.settings['output_path']).resolve()

    def sort_classes(self) -> None:
        '''
        Sorts all of the classes in `self.classes` in alphabetical
        order by name.
        '''
        self.classes = OrderedDict(sorted(self.classes.items(), key=lambda t: t[0].lower()))
