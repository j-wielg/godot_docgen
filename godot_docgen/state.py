from typing import OrderedDict
from pathlib import Path
import re
import utils


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
    path : pathlib.Path
        Path to the project to document.
    output_path : pathlib.Path
        Where to generate the reStructuredText files.
    do_not_parse : dict[str, list]
        Specifies which files, and which nodes within a scene file, should
        not be parsed.
    class_index : list[re.Pattern]
        Determines what classes should be added to the class_index.rst
    scene_index : list[re.Pattern]
        Determines what scenes should be added to the scene_index.rst
    '''
    settings: dict

    def __init__(self) -> None:
        self.num_errors = 0
        self.should_color = True
        self.num_warnings = 0
        self.classes: OrderedDict = OrderedDict()
        self.scripts: OrderedDict = OrderedDict()
        self.scenes: OrderedDict = OrderedDict()
        self.current_class = None
        self.path: Path = Path('../project').resolve()
        self.output_path: Path = Path('../rst_files').resolve()
        self.do_not_parse: dict[str, list[re.Pattern]] = {}
        self.class_index: dict[str, ...] = {"Classes": [re.compile('.*')]}
        self.scene_index: dict[str, ...] = {"Scenes": [re.compile('.*')]}

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
        do_not_parse : dict[str, list[str]]
            Which files in the project should not be parsed. If the key is
            a .tscn file, the value should be a list of patterns which
            match node names. Otherwise, an empty list means ignore everything.
        class_index : dict[str, list[str]]
            How to organize the class index file. Each key corresponds to a
            title in the class index, and the value to a list of regular
            expressions that determine what classes go under that title.
        scene_index : dict[str, list[str]]
            Works the same way as class_index but for scenes.
        '''
        if 'path' in settings:
            self.path = Path(settings['path']).resolve()
            if not self.path.is_dir():
                utils.print_error(
                    f"Invalid settings: The path {str(self.path)} is not a directory",
                    self)
                raise ValueError
        if 'output_path' in settings:
            self.output_path = Path(settings['output_path']).resolve()
            if not self.output_path.is_dir():
                utils.print_error(
                    f"Invalid settings: The path {str(self.output_path)} is not a directory",
                    self)
                raise ValueError
        # Parses the 'do_not_parse' setting
        if 'do_not_parse' in settings:
            dont_parse: dict[str, list[str]] = settings['do_not_parse']
            if not isinstance(dont_parse, dict):
                utils.print_error(
                    "Invalid settings: settings['do_not_parse'] should be a dictionary",
                    self)
                raise ValueError
            for path, value in dont_parse.items():
                self.do_not_parse[path] = []
                if not path.endswith('.tscn'):
                    self.do_not_parse[path] = []
                    continue
                if not isinstance(value, list):
                    utils.print_error(
                        f"Invalid settings: settings['do_not_parse']['{path}'] should be a list of strings",
                        self)
                    raise ValueError
                for ignore in value:
                    if not isinstance(ignore, str):
                        utils.print_error(
                            f"Invalid settings: settings['do_not_parse']['{path}'] should be a list of strings",
                            self)
                        raise ValueError
                    self.do_not_parse[path].append(re.compile(ignore))
        # Parses the class_index setting
        if 'class_index' in settings:
            class_index = settings['class_index']
            self.class_index = {}
            if not isinstance(class_index, dict):
                utils.print_error(
                    f"Invalid settings: settings['class_index'] should be a dictionary",
                    self)
                raise ValueError
            for title, patterns in class_index.items():
                # Gets the key-value pairs in class_index
                if not isinstance(patterns, list):
                    utils.print_error(
                        f"Invalid settings: settings['class_index'] should be a dictionary with lists of strings as values",
                        self)
                    raise ValueError
                self.class_index[title] = []
                for pattern in patterns:
                    if not isinstance(pattern, str):
                        utils.print_error(
                            f"Invalid settings: settings['class_index'] should be a dictionary with lists of strings as values",
                            self)
                        raise ValueError
                    self.class_index[title].append(re.compile(pattern))
        # Parses the scene_index setting
        if 'scene_index' in settings:
            scene_index = settings['scene_index']
            self.scene_index = {}
            if not isinstance(scene_index, dict):
                utils.print_error(
                    f"Invalid settings: settings['scene_index'] should be a dictionary",
                    self)
                raise ValueError
            for title, patterns in scene_index.items():
                # Gets the key-value pairs in class_index
                if not isinstance(patterns, list):
                    utils.print_error(
                        f"Invalid settings: settings['scene_index'] should be a dictionary with lists of strings as values",
                        self)
                    raise ValueError
                self.scene_index[title] = []
                for pattern in patterns:
                    if not isinstance(pattern, str):
                        utils.print_error(
                            f"Invalid settings: settings['scene_index'] should be a dictionary with lists of strings as values",
                            self)
                        raise ValueError
                    self.scene_index[title].append(re.compile(pattern))

    def sort_classes(self) -> None:
        '''
        Sorts all of the classes in `self.classes` in alphabetical
        order by name.
        '''
        self.classes = OrderedDict(sorted(self.classes.items(), key=lambda t: t[0].lower()))
