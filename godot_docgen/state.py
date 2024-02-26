from typing import OrderedDict


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
    classes : OrderedDict[str, ClassDef]
        Stores the Godot project's classes. The keys are the name of the class,
        and the values are `ClassDef` objects
    scenes : OrderedDict[str, SceneDef]
        Stores all of the scenes. The keys are the name of the scene, and
        the values are `SceneDef` objects
    scripts : dict[str, xml.etree.ElementTree]
        Stores all of the scripts in the projects which do not define a class.
        The keys are the path to the script from res://, and the values are
        parsed XML trees.
    '''
    def __init__(self) -> None:
        self.num_errors = 0
        self.num_warnings = 0
        self.classes: OrderedDict = OrderedDict()
        self.scripts: OrderedDict = OrderedDict()
        self.scenes: OrderedDict = OrderedDict()
        self.current_class: str = ""

        # Additional content and structure checks and validators.
        # self.script_language_parity_check: ScriptLanguageParityCheck = ScriptLanguageParityCheck()

    def sort_classes(self) -> None:
        '''
        Sorts all of the classes in `self.classes` in alphabetical
        order by name.
        '''
        self.classes = OrderedDict(sorted(self.classes.items(), key=lambda t: t[0].lower()))
