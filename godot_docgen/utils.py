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
    '''
    if state.should_color:
        print(f'{STYLES["red"]}{STYLES["bold"]}ERROR:{STYLES["regular"]} {error}{STYLES["reset"]}', file=sys.stderr)
    else:
        print(f'ERROR: {error}')
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
    '''
    if state.should_color:
        print(f'{STYLES["yellow"]}{STYLES["bold"]}WARNING:{STYLES["regular"]} {warning}{STYLES["reset"]}', file=sys.stderr)
    else:
        print(f'WARNING: {warning}')
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
    '''
    print(message)


def make_heading(title: str, underline: str, l10n: bool = True) -> str:
    if l10n:
        new_title = translate(title)
        if new_title != title:
            title = new_title
            underline *= 2  # Double length to handle wide chars.
    return f"{title}\n{(underline * len(title))}\n\n"


def translate(line: str):
    return line
