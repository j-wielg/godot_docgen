'''
Contains utility functions
'''

STYLES = {
    "red": "\x1b[91m",  # ]
    "green": "\x1b[92m",  # ]
    "yellow": "\x1b[93m",  # ]
    "bold": "\x1b[1m",  # ]
    "regular": "\x1b[22m",  # ]
    "reset": "\x1b[0m"  # ]
}


def print_error(error: str, state) -> None:
    if state.should_color:
        print(f'{STYLES["red"]}{STYLES["bold"]}ERROR:{STYLES["regular"]} {error}{STYLES["reset"]}')
    else:
        print(f'ERROR: {error}')
    state.num_errors += 1
