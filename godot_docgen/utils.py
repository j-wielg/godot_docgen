'''
Contains utility functions
'''
import sys


STYLES = {
    "red": "\x1b[91m",  # ]
    "green": "\x1b[92m",  # ]
    "yellow": "\x1b[93m",  # ]
    "bold": "\x1b[1m",  # ]
    "regular": "\x1b[22m",  # ]
    "reset": "\x1b[0m"  # ]
}

INDENT = '    '

def print_error(error: str, state) -> None:
    '''
    Takes an error message, prints a formatted error, and
    increments the error count in the state.

    Parameters
    ----------
    error : str
        The error message to print
    state : State
        The global state of the program.

    Notes
    -----
    This function uses the state object to decide how to format the
    message. See the state object's documentation for more info.
    '''
    if state.error is None:
        return
    indent = ''
    if state.debug is not None:
        indent = INDENT * state.indent_level
    if state.should_color and state.error in [sys.stdout, sys.stderr]:
        print(f'{indent}{STYLES["red"]}{STYLES["bold"]}ERROR:{STYLES["regular"]} {error}{STYLES["reset"]}', file=state.error)
    else:
        print(f'{indent}ERROR: {error}', file=state.error)
    state.num_errors += 1


def print_warning(warning: str, state) -> None:
    '''
    Takes a warning message, prints a formatted warning, and
    increments the warning count in the state.

    Parameters
    ----------
    warning : str
        The warning message to print
    state : State
        The global state of the program.

    Notes
    -----
    This function uses the state object to decide how to format the
    message. See the state object's documentation for more info.
    '''
    if state.warning is None:
        return
    indent = ''
    if state.debug is not None:
        indent = INDENT * state.indent_level
    if state.should_color and state.warning in [sys.stdout, sys.stderr]:
        print(f'{indent}{STYLES["yellow"]}{STYLES["bold"]}WARNING:{STYLES["regular"]} {warning}{STYLES["reset"]}', file=state.warning)
    else:
        print(f'{indent}WARNING: {warning}', file=state.warning)
    state.num_warnings += 1


def print_log(message: str, state) -> None:
    '''
    Prints a log message.

    Parameters
    ----------
    message : str
        The message to display
    state : State
        The state of the program

    Notes
    -----
    This function uses the state object to decide how to format the
    message. See the state object's documentation for more info.
    '''
    if state.info is None:
        return
    indent = ''
    if state.debug is not None:
        indent = INDENT * state.indent_level
    if state.info in [sys.stdout, sys.stderr]:
        print(indent + message, file=state.info)
    else:
        print(f'{indent}INFO: {message}', file=state.info)


def print_debug(message: str, state) -> None:
    '''
    Prints debug messages.

    Parameters
    ----------
    message : str
        The message to print.
    state : State
        The state of the program.

    Notes
    -----
    This function uses the state object to decide how to format the
    message. See the state object's documentation for more info.
    '''
    if state.debug is None:
        return
    indent = INDENT * state.indent_level
    if state.debug in [sys.stdout, sys.stderr]:
        print(f'{indent}DEBUG: {message}', file=state.debug)
    else:
        print(f'{indent}DEBUG: {message}', file=state.debug)


def make_heading(title: str, underline: str, l10n: bool = True) -> str:
    if l10n:
        new_title = translate(title)
        if new_title != title:
            title = new_title
            underline *= 2  # Double length to handle wide chars.
    return f"{title}\n{(underline * len(title))}\n\n"


def translate(line: str):
    return line
