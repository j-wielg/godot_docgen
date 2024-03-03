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
    '''
    def __init__(self) -> None:
        self.num_errors = 0
        self.num_warnings = 0
        self.classes: OrderedDict = OrderedDict()
        self.scripts: OrderedDict = OrderedDict()
        self.scenes: OrderedDict = OrderedDict()

    def sort_classes(self) -> None:
        '''
        Sorts all of the classes in `self.classes` in alphabetical
        order by name.
        '''
        self.classes = OrderedDict(sorted(self.classes.items(), key=lambda t: t[0].lower()))
