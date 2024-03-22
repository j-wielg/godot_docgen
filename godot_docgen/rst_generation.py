'''
Contains helper functions which generate rst components.
'''
import utils
from godot_classes import GODOT_NATIVE_CLASSES
import re

MARKUP_ALLOWED_PRECEDENT = " -:/'\"<([{"
MARKUP_ALLOWED_SUBSEQUENT = " -.,:;!?\\/'\")]}>"
GODOT_DOCS_PATTERN = re.compile(r"^\$DOCS_URL/(.*)\.html(#.*)?$")

RESERVED_FORMATTING_TAGS = ["i", "b", "u", "code", "kbd", "center", "url", "br"]
RESERVED_LAYOUT_TAGS = ["codeblocks"]
RESERVED_CODEBLOCK_TAGS = ["codeblock", "gdscript", "csharp"]
RESERVED_CROSSLINK_TAGS = [
    "method",
    "constructor",
    "operator",
    "member",
    "signal",
    "constant",
    "enum",
    "annotation",
    "theme_item",
    "param",
]


class TagState:
    def __init__(self, raw: str, name: str, arguments: list[str], closing: bool) -> None:
        self.raw = raw

        self.name = name
        self.arguments = arguments
        self.closing = closing


def is_in_tagset(tag_text: str, tagset: list[str]) -> bool:
    '''
    Checks if a tag is present in a list of tags.
    '''
    for tag in tagset:
        # Complete match.
        if tag_text == tag:
            return True
        # Tag with arguments.
        if tag_text.startswith(tag + " "):
            return True
        # Tag with arguments, special case for [url].
        if tag_text.startswith(tag + "="):
            return True

    return False


def get_tag_and_args(tag_text: str) -> TagState:
    '''
    Parses a string for a tag's name and arguments
    '''
    tag_name = tag_text
    arguments: list[str] = []

    assign_pos = tag_text.find("=")
    if assign_pos >= 0:
        tag_name = tag_text[:assign_pos]
        arguments = [tag_text[assign_pos + 1 :].strip()]
    else:
        space_pos = tag_text.find(" ")
        if space_pos >= 0:
            tag_name = tag_text[:space_pos]
            arguments = [tag_text[space_pos + 1 :].strip()]

    closing = False
    if tag_name.startswith("/"):
        tag_name = tag_name[1:]
        closing = True

    return TagState(tag_text, tag_name, arguments, closing)


def parse_link_target(link_target: str, state, context_name: str) -> list[str]:
    '''
    Given a BBCode segment of the form 'Class.member', gets the value
    of the targeted class and member. Used to generate crosslinks.

    Parameters
    ----------
    link_target : str
        A BBCode segment of the form 'Class.member'
    state : State
        The state of the program. Used if the class should be inferred from
        the context rather than explicitly stated
    context_name : str
        Not used, will probably delete in a refactor.

    Returns
    -------
    list[str]
        If the argument takes the form "Class.member", returns
        ["Class", "member"]. If of the form "member", returns
        [state.current_class, "member"]
    '''
    if link_target.find(".") != -1:
        return link_target.split(".")
    else:
        return [state.current_class, link_target]


def format_text_block(text: str, context, state) -> str:
    # Linebreak + tabs in the XML should become two line breaks unless in a "codeblock"
    pos = 0
    while True:
        pos = text.find("\n", pos)
        if pos == -1:
            break

        pre_text = text[:pos]
        indent_level = 0
        while pos + 1 < len(text) and text[pos + 1] == "\t":
            pos += 1
            indent_level += 1
        post_text = text[pos + 1 :]

        # Handle codeblocks
        if (
            post_text.startswith("[codeblock]")
            or post_text.startswith("[codeblock ")
            or post_text.startswith("[gdscript]")
            or post_text.startswith("[gdscript ")
            or post_text.startswith("[csharp]")
            or post_text.startswith("[csharp ")
        ):
            tag_text = post_text[1:].split("]", 1)[0]
            tag_state = get_tag_and_args(tag_text)
            result = format_codeblock(tag_state, post_text, indent_level, state)
            if result is None:
                return ""
            text = f"{pre_text}{result[0]}"
            pos += result[1] - indent_level

        # Handle normal text
        else:
            text = f"{pre_text}\n\n{post_text}"
            pos += 2 - indent_level

    next_brac_pos = text.find("[")
    text = escape_rst(text, next_brac_pos)

    context_name = format_context_name(context)

    # Handle [tags]
    inside_code = False
    inside_code_tag = ""
    inside_code_tabs = False
    ignore_code_warnings = False
    code_warning_if_intended_string = "If this is intended, use [code skip-lint]...[/code]."

    has_codeblocks_gdscript = False
    has_codeblocks_csharp = False

    pos = 0
    tag_depth = 0
    while True:
        pos = text.find("[", pos)
        if pos == -1:
            break

        endq_pos = text.find("]", pos + 1)
        if endq_pos == -1:
            break

        pre_text = text[:pos]
        post_text = text[endq_pos + 1 :]
        tag_text = text[pos + 1 : endq_pos]

        escape_pre = False
        escape_post = False

        # Tag is a reference to a class.
        if tag_text in state.classes and not inside_code:
            if tag_text == state.current_class:
                # Don't create a link to the same class, format it as strong emphasis.
                tag_text = f"**{tag_text}**"
            else:
                tag_text = make_type(tag_text, state)
            escape_pre = True
            escape_post = True

        # Tag is a cross-reference or a formatting directive.
        else:
            tag_state = get_tag_and_args(tag_text)

            # Anything identified as a tag inside of a code block is valid,
            # unless it's a matching closing tag.
            if inside_code:
                # Exiting codeblocks and inline code tags.

                if tag_state.closing and tag_state.name == inside_code_tag:
                    if is_in_tagset(tag_state.name, RESERVED_CODEBLOCK_TAGS):
                        tag_text = ""
                        tag_depth -= 1
                        inside_code = False
                        ignore_code_warnings = False
                        # Strip newline if the tag was alone on one
                        if pre_text[-1] == "\n":
                            pre_text = pre_text[:-1]

                    elif is_in_tagset(tag_state.name, ["code"]):
                        tag_text = "``"
                        tag_depth -= 1
                        inside_code = False
                        ignore_code_warnings = False
                        escape_post = True

                else:
                    if not ignore_code_warnings and tag_state.closing:
                        utils.print_warning(
                            f'{state.current_class}.xml: Found a code string that looks like a closing tag "[{tag_state.raw}]" in {context_name}. {code_warning_if_intended_string}',
                            state,
                        )

                    tag_text = f"[{tag_text}]"

            # Entering codeblocks and inline code tags.

            elif tag_state.name == "codeblocks":
                if tag_state.closing:
                    if not has_codeblocks_gdscript or not has_codeblocks_csharp:
                        state.script_language_parity_check.add_hit(
                            state.current_class,
                            context,
                            "Only one script language sample found in [codeblocks]",
                            state,
                        )

                    has_codeblocks_gdscript = False
                    has_codeblocks_csharp = False

                    tag_depth -= 1
                    tag_text = ""
                    inside_code_tabs = False
                else:
                    tag_depth += 1
                    tag_text = "\n.. tabs::"
                    inside_code_tabs = True

            elif is_in_tagset(tag_state.name, RESERVED_CODEBLOCK_TAGS):
                tag_depth += 1

                if tag_state.name == "gdscript":
                    if not inside_code_tabs:
                        utils.print_error(
                            f"{state.current_class}.xml: GDScript code block is used outside of [codeblocks] in {context_name}.",
                            state,
                        )
                    else:
                        has_codeblocks_gdscript = True
                    tag_text = "\n .. code-tab:: gdscript\n"
                elif tag_state.name == "csharp":
                    if not inside_code_tabs:
                        utils.print_error(
                            f"{state.current_class}.xml: C# code block is used outside of [codeblocks] in {context_name}.",
                            state,
                        )
                    else:
                        has_codeblocks_csharp = True
                    tag_text = "\n .. code-tab:: csharp\n"
                else:
                    state.script_language_parity_check.add_hit(
                        state.current_class,
                        context,
                        "Code sample is formatted with [codeblock] where [codeblocks] should be used",
                        state,
                    )

                    tag_text = "\n::\n"

                inside_code = True
                inside_code_tag = tag_state.name
                ignore_code_warnings = "skip-lint" in tag_state.arguments

            elif is_in_tagset(tag_state.name, ["code"]):
                tag_text = "``"
                tag_depth += 1

                inside_code = True
                inside_code_tag = "code"
                ignore_code_warnings = "skip-lint" in tag_state.arguments
                escape_pre = True

            # Cross-references to items in this or other class documentation pages.
            elif is_in_tagset(tag_state.name, RESERVED_CROSSLINK_TAGS):
                link_target: str = tag_state.arguments[0] if len(tag_state.arguments) > 0 else ""

                if link_target == "":
                    utils.print_error(
                        f'{state.current_class}.xml: Empty cross-reference link "[{tag_state.raw}]" in {context_name}.',
                        state,
                    )
                    tag_text = ""
                else:
                    if (
                        tag_state.name == "method"
                        or tag_state.name == "constructor"
                        or tag_state.name == "operator"
                        or tag_state.name == "member"
                        or tag_state.name == "signal"
                        or tag_state.name == "annotation"
                        or tag_state.name == "theme_item"
                        or tag_state.name == "constant"
                    ):
                        target_class_name, target_name, *rest = parse_link_target(link_target, state, context_name)
                        if len(rest) > 0:
                            utils.print_error(
                                f'{state.current_class}.xml: Bad reference "{link_target}" in {context_name}.',
                                state,
                            )

                        # Default to the tag command name. This works by default for most tags,
                        # but method, member, and theme_item have special cases.
                        ref_type = "_{}".format(tag_state.name)

                        if target_class_name in state.classes:
                            class_def = state.classes[target_class_name]

                            if tag_state.name == "method":
                                if target_name.startswith("_"):
                                    ref_type = "_private_method"

                                if target_name not in class_def.methods:
                                    utils.print_error(
                                        f'{state.current_class}.xml: Unresolved method reference "{link_target}" in {context_name}.',
                                        state,
                                    )

                            elif tag_state.name == "constructor" and target_name not in class_def.constructors:
                                utils.print_error(
                                    f'{state.current_class}.xml: Unresolved constructor reference "{link_target}" in {context_name}.',
                                    state,
                                )

                            elif tag_state.name == "operator" and target_name not in class_def.operators:
                                utils.print_error(
                                    f'{state.current_class}.xml: Unresolved operator reference "{link_target}" in {context_name}.',
                                    state,
                                )

                            elif tag_state.name == "member":
                                ref_type = "_property"

                                if target_name not in class_def.properties:
                                    utils.print_error(
                                        f'{state.current_class}.xml: Unresolved member reference "{link_target}" in {context_name}.',
                                        state,
                                    )

                            elif tag_state.name == "signal" and target_name not in class_def.signals:
                                utils.print_error(
                                    f'{state.current_class}.xml: Unresolved signal reference "{link_target}" in {context_name}.',
                                    state,
                                )

                            elif tag_state.name == "annotation" and target_name not in class_def.annotations:
                                utils.print_error(
                                    f'{state.current_class}.xml: Unresolved annotation reference "{link_target}" in {context_name}.',
                                    state,
                                )

                            elif tag_state.name == "theme_item":
                                if target_name not in class_def.theme_items:
                                    utils.print_error(
                                        f'{state.current_class}.xml: Unresolved theme property reference "{link_target}" in {context_name}.',
                                        state,
                                    )
                                else:
                                    # Needs theme data type to be properly linked, which we cannot get without a class.
                                    name = class_def.theme_items[target_name].data_name
                                    ref_type = f"_theme_{name}"

                            elif tag_state.name == "constant":
                                found = False

                                # Search in the current class
                                search_class_defs = [class_def]

                                if link_target.find(".") == -1:
                                    # Also search in @GlobalScope as a last resort if no class was specified
                                    search_class_defs.append(state.classes["@GlobalScope"])

                                for search_class_def in search_class_defs:
                                    if target_name in search_class_def.constants:
                                        target_class_name = search_class_def.name
                                        found = True

                                    else:
                                        for enum in search_class_def.enums.values():
                                            if target_name in enum.values:
                                                target_class_name = search_class_def.name
                                                found = True
                                                break

                                if not found:
                                    utils.print_error(
                                        f'{state.current_class}.xml: Unresolved constant reference "{link_target}" in {context_name}.',
                                        state,
                                    )

                        else:
                            utils.print_error(
                                f'{state.current_class}.xml: Unresolved type reference "{target_class_name}" in method reference "{link_target}" in {context_name}.',
                                state,
                            )

                        repl_text = target_name
                        if target_class_name != state.current_class:
                            repl_text = f"{target_class_name}.{target_name}"
                        tag_text = f":ref:`{repl_text}<class_{target_class_name}{ref_type}_{target_name}>`"
                        escape_pre = True
                        escape_post = True

                    elif tag_state.name == "enum":
                        tag_text = make_enum(link_target, False, state)
                        escape_pre = True
                        escape_post = True

                    elif tag_state.name == "param":
                        tag_text = f"``{link_target}``"
                        escape_pre = True
                        escape_post = True

            # Formatting directives.

            elif is_in_tagset(tag_state.name, ["url"]):
                url_target = tag_state.arguments[0] if len(tag_state.arguments) > 0 else ""

                if url_target == "":
                    utils.print_error(
                        f'{state.current_class}.xml: Misformatted [url] tag "[{tag_state.raw}]" in {context_name}.',
                        state,
                    )
                else:
                    # Unlike other tags, URLs are handled in full here, as we need to extract
                    # the optional link title to use `make_link`.
                    endurl_pos = text.find("[/url]", endq_pos + 1)
                    if endurl_pos == -1:
                        utils.print_error(
                            f"{state.current_class}.xml: Tag depth mismatch for [url]: no closing [/url] in {context_name}.",
                            state,
                        )
                        break
                    link_title = text[endq_pos + 1 : endurl_pos]
                    tag_text = make_link(url_target, link_title)

                    pre_text = text[:pos]
                    post_text = text[endurl_pos + 6 :]

                    if pre_text and pre_text[-1] not in MARKUP_ALLOWED_PRECEDENT:
                        pre_text += "\\ "
                    if post_text and post_text[0] not in MARKUP_ALLOWED_SUBSEQUENT:
                        post_text = "\\ " + post_text

                    text = pre_text + tag_text + post_text
                    pos = len(pre_text) + len(tag_text)
                    continue

            elif tag_state.name == "br":
                # Make a new paragraph instead of a linebreak, rst is not so linebreak friendly
                tag_text = "\n\n"
                # Strip potential leading spaces
                while post_text[0] == " ":
                    post_text = post_text[1:]

            elif tag_state.name == "center":
                if tag_state.closing:
                    tag_depth -= 1
                else:
                    tag_depth += 1
                tag_text = ""

            elif tag_state.name == "i":
                if tag_state.closing:
                    tag_depth -= 1
                    escape_post = True
                else:
                    tag_depth += 1
                    escape_pre = True
                tag_text = "*"

            elif tag_state.name == "b":
                if tag_state.closing:
                    tag_depth -= 1
                    escape_post = True
                else:
                    tag_depth += 1
                    escape_pre = True
                tag_text = "**"

            elif tag_state.name == "u":
                if tag_state.closing:
                    tag_depth -= 1
                    escape_post = True
                else:
                    tag_depth += 1
                    escape_pre = True
                tag_text = ""

            elif tag_state.name == "kbd":
                tag_text = "`"
                if tag_state.closing:
                    tag_depth -= 1
                    escape_post = True
                else:
                    tag_text = ":kbd:" + tag_text
                    tag_depth += 1
                    escape_pre = True

            # Invalid syntax.
            else:
                if tag_state.closing:
                    utils.print_error(
                        f'{state.current_class}.xml: Unrecognized closing tag "[{tag_state.raw}]" in {context_name}.',
                        state,
                    )

                    tag_text = f"[{tag_text}]"
                else:
                    utils.print_error(
                        f'{state.current_class}.xml: Unrecognized opening tag "[{tag_state.raw}]" in {context_name}.',
                        state,
                    )

                    tag_text = f"``{tag_text}``"
                    escape_pre = True
                    escape_post = True

        # Properly escape things like `[Node]s`
        if escape_pre and pre_text and pre_text[-1] not in MARKUP_ALLOWED_PRECEDENT:
            pre_text += "\\ "
        if escape_post and post_text and post_text[0] not in MARKUP_ALLOWED_SUBSEQUENT:
            post_text = "\\ " + post_text

        next_brac_pos = post_text.find("[", 0)
        iter_pos = 0
        while not inside_code:
            iter_pos = post_text.find("*", iter_pos, next_brac_pos)
            if iter_pos == -1:
                break
            post_text = f"{post_text[:iter_pos]}\\*{post_text[iter_pos + 1 :]}"
            iter_pos += 2

        iter_pos = 0
        while not inside_code:
            iter_pos = post_text.find("_", iter_pos, next_brac_pos)
            if iter_pos == -1:
                break
            if not post_text[iter_pos + 1].isalnum():  # don't escape within a snake_case word
                post_text = f"{post_text[:iter_pos]}\\_{post_text[iter_pos + 1 :]}"
                iter_pos += 2
            else:
                iter_pos += 1

        text = pre_text + tag_text + post_text
        pos = len(pre_text) + len(tag_text)

    if tag_depth > 0:
        utils.print_error(
            f"{state.current_class}.xml: Tag depth mismatch: too many (or too few) open/close tags in {context_name}.",
            state,
        )

    return text


def format_context_name(context) -> str:
    context_name: str = "unknown context"
    if context is not None:
        context_name = f'{context.definition_name} "{context.name}" description'

    return context_name


def escape_rst(text: str, until_pos: int = -1) -> str:
    # Escape \ character, otherwise it ends up as an escape character in rst
    pos = 0
    while True:
        pos = text.find("\\", pos, until_pos)
        if pos == -1:
            break
        text = f"{text[:pos]}\\\\{text[pos + 1 :]}"
        pos += 2

    # Escape * character to avoid interpreting it as emphasis
    pos = 0
    while True:
        pos = text.find("*", pos, until_pos)
        if pos == -1:
            break
        text = f"{text[:pos]}\\*{text[pos + 1 :]}"
        pos += 2

    # Escape _ character at the end of a word to avoid interpreting it as an inline hyperlink
    pos = 0
    while True:
        pos = text.find("_", pos, until_pos)
        if pos == -1:
            break
        if not text[pos + 1].isalnum():  # don't escape within a snake_case word
            text = f"{text[:pos]}\\_{text[pos + 1 :]}"
            pos += 2
        else:
            pos += 1

    return text


def format_codeblock(tag_state: TagState, post_text: str, indent_level: int, state):
    end_pos = post_text.find("[/" + tag_state.name + "]")
    if end_pos == -1:
        utils.print_error(
            f"{state.current_class}.xml: Tag depth mismatch for [{tag_state.name}]: no closing [/{tag_state.name}].",
            state,
        )
        return None

    opening_formatted = tag_state.name
    if len(tag_state.arguments) > 0:
        opening_formatted += " " + " ".join(tag_state.arguments)

    code_text = post_text[len(f"[{opening_formatted}]") : end_pos]
    post_text = post_text[end_pos:]

    # Remove extraneous tabs
    code_pos = 0
    while True:
        code_pos = code_text.find("\n", code_pos)
        if code_pos == -1:
            break

        to_skip = 0
        while code_pos + to_skip + 1 < len(code_text) and code_text[code_pos + to_skip + 1] == "\t":
            to_skip += 1

        if to_skip > indent_level:
            utils.print_error(
                f"{state.current_class}.xml: Four spaces should be used for indentation within [{tag_state.name}].",
                state,
            )

        if len(code_text[code_pos + to_skip + 1 :]) == 0:
            code_text = f"{code_text[:code_pos]}\n"
            code_pos += 1
        else:
            code_text = f"{code_text[:code_pos]}\n    {code_text[code_pos + to_skip + 1 :]}"
            code_pos += 5 - to_skip
    return (f"\n[{opening_formatted}]{code_text}{post_text}", len(f"\n[{opening_formatted}]{code_text}"))


def format_table(f, data, remove_empty_columns: bool = False) -> None:
    if len(data) == 0:
        return

    f.write(".. table::\n")
    f.write("   :widths: auto\n\n")

    # Calculate the width of each column first, we will use this information
    # to properly format RST-style tables.
    column_sizes = [0] * len(data[0])
    for row in data:
        for i, text in enumerate(row):
            text_length = len(text or "")
            if text_length > column_sizes[i]:
                column_sizes[i] = text_length

    # Each table row is wrapped in two separators, consecutive rows share the same separator.
    # All separators, or rather borders, have the same shape and content. We compose it once,
    # then reuse it.

    sep = ""
    for size in column_sizes:
        if size == 0 and remove_empty_columns:
            continue
        sep += "+" + "-" * (size + 2)  # Content of each cell is padded by 1 on each side.
    sep += "+\n"

    # Draw the first separator.
    f.write(f"   {sep}")

    # Draw each row and close it with a separator.
    for row in data:
        row_text = "|"
        for i, text in enumerate(row):
            if column_sizes[i] == 0 and remove_empty_columns:
                continue
            row_text += f' {(text or "").ljust(column_sizes[i])} |'
        row_text += "\n"

        f.write(f"   {row_text}")
        f.write(f"   {sep}")

    f.write("\n")


def sanitize_operator_name(dirty_name: str, state) -> str:
    clear_name = dirty_name.replace("operator ", "")

    if clear_name == "!=":
        clear_name = "neq"
    elif clear_name == "==":
        clear_name = "eq"

    elif clear_name == "<":
        clear_name = "lt"
    elif clear_name == "<=":
        clear_name = "lte"
    elif clear_name == ">":
        clear_name = "gt"
    elif clear_name == ">=":
        clear_name = "gte"

    elif clear_name == "+":
        clear_name = "sum"
    elif clear_name == "-":
        clear_name = "dif"
    elif clear_name == "*":
        clear_name = "mul"
    elif clear_name == "/":
        clear_name = "div"
    elif clear_name == "%":
        clear_name = "mod"
    elif clear_name == "**":
        clear_name = "pow"

    elif clear_name == "unary+":
        clear_name = "unplus"
    elif clear_name == "unary-":
        clear_name = "unminus"

    elif clear_name == "<<":
        clear_name = "bwsl"
    elif clear_name == ">>":
        clear_name = "bwsr"
    elif clear_name == "&":
        clear_name = "bwand"
    elif clear_name == "|":
        clear_name = "bwor"
    elif clear_name == "^":
        clear_name = "bwxor"
    elif clear_name == "~":
        clear_name = "bwnot"

    elif clear_name == "[]":
        clear_name = "idx"

    else:
        clear_name = "xxx"
        utils.print_error(f'Unsupported operator type "{dirty_name}", please add the missing rule.', state)

    return clear_name


def make_type(klass: str, state) -> str:
    if klass.find("*") != -1:  # Pointer, ignore
        return f"``{klass}``"

    link_type = klass
    is_array = False

    if link_type.endswith("[]"):  # Typed array, strip [] to link to contained type.
        link_type = link_type[:-2]
        is_array = True

    if link_type in state.classes:
        type_rst = f":ref:`{link_type}<class_{link_type}>`"
        if is_array:
            type_rst = f":ref:`Array<class_Array>`\\[{type_rst}\\]"
        return type_rst
    elif link_type in GODOT_NATIVE_CLASSES:
        type_rst = f"`{link_type} <https://docs.godotengine.org/en/stable/classes/class_{link_type.lower()}.html>`_"
        if is_array:
            type_rst = f"`Array <https://docs.godotengine.org/en/stable/classes/class_array.html>`_\\[{type_rst}\\]"
        return type_rst

    utils.print_error(f'{state.current_class}.xml: Unresolved type "{link_type}".', state)
    type_rst = f"``{link_type}``"
    if is_array:
        type_rst = f":ref:`Array<class_Array>`\\[{type_rst}\\]"
    return type_rst


def make_enum(t: str, is_bitfield: bool, state) -> str:
    p = t.find(".")
    if p >= 0:
        c = t[0:p]
        e = t[p + 1 :]
        # Variant enums live in GlobalScope but still use periods.
        if c == "Variant":
            c = "@GlobalScope"
            e = "Variant." + e
    else:
        c = state.current_class
        e = t
        if c in state.classes and e not in state.classes[c].enums:
            c = "@GlobalScope"

    if c in state.classes and e in state.classes[c].enums:
        if is_bitfield:
            if not state.classes[c].enums[e].is_bitfield:
                utils.print_error(f'{state.current_class}.xml: Enum "{t}" is not bitfield.', state)
            return f"|bitfield|\\[:ref:`{e}<enum_{c}_{e}>`\\]"
        else:
            return f":ref:`{e}<enum_{c}_{e}>`"

    # Don't fail for `Vector3.Axis`, as this enum is a special case which is expected not to be resolved.
    if f"{c}.{e}" != "Vector3.Axis":
        utils.print_error(f'{state.current_class}.xml: Unresolved enum "{t}".', state)

    return t


def make_deprecated_experimental(item, state) -> str:
    '''
    Takes an item, and generates rst text which documents the experimental
    and deprecated messages.

    Parameters
    ----------
    item : DefinitionBase
        The item to generate deprecated and experimental messages for.
    state : State
        The state of the program

    Returns
    -------
    str
        A string containing ReStructured Text.
    '''
    result = ""

    if item.deprecated is not None:
        deprecated_prefix = utils.translate("Deprecated:")
        if item.deprecated.strip() == "":
            default_message = utils.translate(f"This {item.definition_name} may be changed or removed in future versions.")
            result += f"**{deprecated_prefix}** {default_message}\n\n"
        else:
            result += f"**{deprecated_prefix}** {format_text_block(item.deprecated.strip(), item, state)}\n\n"

    if item.experimental is not None:
        experimental_prefix = utils.translate("Experimental:")
        if item.experimental.strip() == "":
            default_message = utils.translate(f"This {item.definition_name} may be changed or removed in future versions.")
            result += f"**{experimental_prefix}** {default_message}\n\n"
        else:
            result += f"**{experimental_prefix}** {format_text_block(item.experimental.strip(), item, state)}\n\n"

    return result


def make_link(url: str, title: str) -> str:
    match = GODOT_DOCS_PATTERN.search(url)
    if match:
        groups = match.groups()
        if match.lastindex == 2:
            # Doc reference with fragment identifier: emit direct link to section with reference to page, for example:
            # `#calling-javascript-from-script in Exporting For Web`
            # Or use the title if provided.
            if title != "":
                return f"`{title} <../{groups[0]}.html{groups[1]}>`__"
            return f"`{groups[1]} <../{groups[0]}.html{groups[1]}>`__ in :doc:`../{groups[0]}`"
        elif match.lastindex == 1:
            # Doc reference, for example:
            # `Math`
            if title != "":
                return f":doc:`{title} <../{groups[0]}>`"
            return f":doc:`../{groups[0]}`"

    # External link, for example:
    # `http://enet.bespin.org/usergroup0.html`
    if title != "":
        return f"`{title} <{url}>`__"
    return f"`{url} <{url}>`__"
