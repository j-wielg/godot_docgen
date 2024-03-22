'''
Contains a bunch of classes which store data for things like type definitions,
method annotations, property descriptions, etc.
These objects can then generate ReStructured Text which documents them.

The definitions for scenes and classes get their own files, since they need to
parse Godot files to be generated.
'''
import xml.etree.ElementTree as ET
from typing import Optional, OrderedDict
from state import State
import utils
import rst_generation


class TagState:
    def __init__(self, raw: str, name: str, arguments: list[str], closing: bool) -> None:
        self.raw = raw

        self.name = name
        self.arguments = arguments
        self.closing = closing


# TODO: Implement `TypeName` properly
class TypeName:
    '''
    Represents a named Type in Godot. This type is handled differently
    depending on whether it refers to a user-defined type, engine-defined
    type, enum, or bitfield.

    Parameters
    ----------
    type_name : str
        The name of the type
    enum : Optional[str], default=None
        The name of the enum, if it is an enum.
    is_bitfield : bool, default=False
        Whether or not the type represents a bitfield
    '''
    type_name: str
    enum: str
    is_bifield: bool

    def __init__(self, type_name: str, enum: Optional[str] = None, is_bitfield: bool = False) -> None:
        self.type_name = type_name
        self.enum = enum
        self.is_bitfield = is_bitfield

    def to_rst(self, s: State) -> str:
        if self.enum is not None:
            return rst_generation.make_enum(self.enum, self.is_bitfield, s)
        elif self.type_name == "void":
            return "|void|"
        else:
            return rst_generation.make_type(self.type_name, s)

    @classmethod
    def from_element(cls, element: ET.Element) -> "TypeName":
        return cls(element.attrib["type"], element.get("enum"), element.get("is_bitfield") == "true")


class DefinitionBase:
    '''
    Base type which is inherited from by all definitions.

    Parameters
    ----------
    definition_name : str
        The type of definition. This string can be 'method', 'class', etc.
    name : str
        The name of the object.

    Attributes
    ----------
    definition_name : str
    name : str
    deprecated : Optional[str]
        Gives an optional deprecation notice
    experimental : Optional[str]
        Gives an optional experimental notice
    '''
    def __init__(
        self,
        definition_name: str,
        name: str,
    ) -> None:
        self.definition_name = definition_name
        self.name = name
        self.deprecated: Optional[str] = None
        self.experimental: Optional[str] = None


class PropertyDef(DefinitionBase):
    '''
    Stores the data for a class member variable.

    Parameters
    ----------
    property : xml.etree.ElementTree.Element
        A subtree of the XML tree which refers to a single property

    Attributes
    ----------
    name : str
        The name of the property
    type_name : TypeName
        The type of the property
    setter, getter : str
        Name of getter and setter for property, if they exist
    text : str
        Documentation on the property
    default_value : str
        Default value of the property, if one exists
    '''
    name: str
    type_name: TypeName
    setter: str
    getter: str
    text: str
    default_value: str
    overrides: str
    deprecated: str
    experimental: str

    def __init__(self, property: ET.Element) -> None:
        self.name = property.attrib["name"]
        self.type_name = TypeName.from_element(property)
        super().__init__("property", self.name)
        self.setter = property.get("setter") or None
        self.getter = property.get("getter") or None
        self.text = property.text.strip()
        self.default_value = property.get("default") or None
        self.overrides = property.get("overrides") or None
        self.deprecated = property.get("deprecated")
        self.experimental = property.get("experimental")


class ParameterDef(DefinitionBase):
    '''
    Stores data which documents a function parameter

    Parameters
    ----------
    param : xml.etree.ElementTree.Element

    Attributes
    ----------
    type_name : TypeName
        The type of the parameter
    default_value : Optional[str]
        The default value of the paramater, if any
    '''
    type_name: TypeName
    default_value: Optional[str]

    def __init__(self, param: ET.Element) -> None:
        name = param.attrib["name"]
        super().__init__("parameter", name)
        # TODO: Add an error message here
        if not name.strip() or name.startswith("_unnamed_arg"):
            pass
        self.type_name = TypeName.from_element(param)
        self.default_value = param.get("default")


class SignalDef(DefinitionBase):
    '''
    Documents a Godot signal.

    Parameters
    ----------
    signal : xml.etree.ElementTree.Element

    Attributes
    ----------
    parameters : list[ParameterDef]
        The list of parameters taken when emitting the signal
    description : Optional[str]
        The description of the signal
    deprecated : Optional[str]
    experimental : Optional[str]
    '''
    parameters: list[ParameterDef]
    description: Optional[str]
    instantiated: bool = False
    emitters: list
    receivers: list

    def __init__(self, signal: ET.Element):
        signal_name = signal.attrib['name']
        super().__init__('signal', signal_name)
        # Generates a list of parameters
        param_elements = signal.findall("param")
        params = [None] * len(param_elements)
        for param_element in param_elements:
            index = int(param_element.attrib["index"])
            params[index] = ParameterDef(param_element)
        self.parameters = params
        desc = signal.find('description')
        self.description = desc.text.strip() if desc is not None else None
        self.emitters = []
        self.receivers = []
        self.deprecated = signal.get('deprecated')
        self.experimental = signal.get('experimental')


class AnnotationDef(DefinitionBase):
    '''
    Used to document an annotation.
    '''
    def __init__(
        self,
        name: str,
        parameters: list[ParameterDef],
        description: Optional[str],
        qualifiers: Optional[str],
    ) -> None:
        super().__init__("annotation", name)

        self.parameters = parameters
        self.description = description
        self.qualifiers = qualifiers


class MethodDef(DefinitionBase):
    '''
    Describes a method in a GDScript script.

    Parameters
    ----------
    method : xml.etree.ElementTree.Element
        A subset of the XML tree which documents a method

    Attributes
    ----------
    return_type : TypeName
    parameters : list[ParameterDef]
        A list of parameters taken by the method
    description : str
        Documentation explaining the method
    qualifiers : str
        Stuff like 'const', 'virtual', 'vararg', etc.
    definition_name : str
        The type of method it is (constructor, method, etc.)
    '''
    return_type: TypeName
    parameters: list[ParameterDef]
    description: Optional[str]
    qualifiers: Optional[str]

    def __init__(self, method: ET.Element, definition_name: str) -> None:
        # Gets the name of the method
        name = method.attrib["name"]
        super().__init__(definition_name, name)
        # Finds qualifiers and return type
        self.qualifiers = method.get("qualifiers")
        return_element = method.find("return")
        if return_element is not None:
            return_type = TypeName.from_element(return_element)
        else:
            return_type = TypeName("void")
        self.return_type = return_type
        # Generates a list of parameters
        param_elements = method.findall("param")
        params = [None] * len(param_elements)
        for param_element in param_elements:
            index = int(param_element.attrib["index"])
            params[index] = ParameterDef(param_element)
        self.parameters = params
        # Gets the method description
        desc_element = method.find("description")
        self.description = None
        if desc_element is not None:
            self.description = desc_element.text.strip()
        # Other things
        self.deprecated = method.get("deprecated")
        self.experimental = method.get("experimental")

    def to_rst(self, class_def: DefinitionBase, ref_type: str, s: State) -> tuple(str, str):
        '''
        Takes the method description, and generates ReStructured Text
        to document it.

        Parameters
        ----------
        class_def : DefinitionBase
            The definition object which contains this method.
        ref_type : str
            The type of object being documented (method or constructor)
        s : State
            The state of the program

        Returns
        -------
        tuple[str, str]
            A tuple containing the documented return type and method signature,
            in that order.
        '''
        # ml.append(rst_generation.make_method_signature(self, m, "constructor", self.state))
        ret_type = self.return_type.to_rst(s)

        out = ""
        if ref_type != "":
            if ref_type == "method":
                ref_type_qualifier = ""
                if self.name.startswith("_"):
                    ref_type_qualifier = "private_"
                out += f":ref:`{self.name}<class_{class_def.name}_{ref_type_qualifier}{ref_type}_{self.name}>`"
            else:
                out += f":ref:`{self.name}<class_{class_def.name}_{ref_type}_{self.name}>`"
        else:
            out += f"**{self.name}**"

        out += "\\ ("
        for i, arg in enumerate(self.parameters):
            if i > 0:
                out += ", "
            else:
                out += "\\ "
            out += f"{arg.name}\\: {arg.type_name.to_rst(s)}"
            if arg.default_value is not None:
                out += f" = {arg.default_value}"
        if self.qualifiers is not None and "vararg" in self.qualifiers:
            if len(self.parameters) > 0:
                out += ", ..."
            else:
                out += "\\ ..."

        out += "\\ )"
        if self.qualifiers is not None:
            # Use substitutions for abbreviations.
            # This is used to display tooltips on hover.
            # See `make_footer()` for descriptions.
            for qualifier in self.qualifiers.split():
                out += f" |{qualifier}|"
        return ret_type, out


class ConstantDef(DefinitionBase):
    '''
    Stores data which documents a constant in a class.

    Parameters
    ----------
    constant : xml.etree.ElementTree.Element

    Attributes
    ----------
    name : str
    value : str
    text : Optional[str]
    bitfield : bool
    '''
    value: str
    text: Optional[str]
    bitfield: bool

    def __init__(self, constant: ET.Element):
        name = constant.attrib["name"]
        self.value = constant.attrib["value"]
        self.bitfield = constant.get("is_bitfield") == 'true'
        self.text = constant.text.strip()
        super().__init__("constant", name)


class EnumDef(DefinitionBase):
    '''
    Contains data to document an enum

    Parameters
    ----------
    name : str
        The name of the enum
    is_bitfield : bool
        Whether or not it is a bitfield

    Attributes
    ----------
    type_name : TypeName
        The type of the enum. Will always be int.
    values : OrderedDict[str, ConstantDef]
        The values of the enum
    is_bitfield : bool
        Whether or not the enum is a bitfield
    '''

    def __init__(self, name: str, bitfield: bool):
        super().__init__("enum", name)

        self.type_name = TypeName("int", name)
        self.values: OrderedDict[str, ConstantDef] = OrderedDict()
        self.is_bitfield = bitfield


class ThemeItemDef(DefinitionBase):
    def __init__(
        self, name: str, type_name: TypeName, data_name: str, text: Optional[str], default_value: Optional[str]
    ) -> None:
        super().__init__("theme property", name)

        self.type_name = type_name
        self.data_name = data_name
        self.text = text
        self.default_value = default_value
