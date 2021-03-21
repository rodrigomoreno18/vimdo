from curses import wrapper
from curses.textpad import Textbox

import curses
import enum


class InputStates(enum.Enum):
    EXITING = -1
    COMMAND = 0
    HELP = 1
    TEXT_INPUT = 2


class ListEntry:
    def __init__(self, title: str, data: str):
        self._title = title
        self._data = data

    @property
    def title(self):
        return self._title

    @property
    def data(self):
        return self._data

    def set_title(self, new_title: str):
        self._title = new_title

    def set_data(self, new_data: str):
        self._data = new_data

    @classmethod
    def new_entry(cls, title: str, data: str):
        return ListEntry(title, data)


class Vimdo:
    def __init__(self, stdscr):
        self._stdscr = stdscr
        self._command_window = curses.newwin(
            1, curses.COLS - 2, curses.LINES - 3, 1
        )
        self._input_window = curses.newwin(
            1, curses.COLS - 2, curses.LINES - 2, 1
        )
        self._main_window = curses.newwin(
            curses.LINES - 3, curses.COLS - 2, 1, 1
        )

        self._incomplete_entries = []

        self._input_state = InputStates.COMMAND
        self._input_number = ""
        self._input_textbox = Textbox(self._input_window, insert_mode=True)

    def run(self):
        curses.curs_set(False)
        self._stdscr.clear()

        errored = None

        while self._input_state != InputStates.EXITING:
            self._main_window.clear()

            self._show_entries()
            self._refresh_windows()

            if self._input_state == InputStates.COMMAND:
                self._display_command_prompt(
                    f"COMMAND [{self._input_number if errored is None else errored}]"
                )
                key = self._command_window.getkey()

                try:
                    self._parse_and_run_command(key)
                    errored = None
                except Exception as err:
                    errored = err

    def _parse_and_run_command(self, key: str):
        if key == "q":
            self._input_state = InputStates.EXITING
        elif key == "h":
            self._show_help()
        elif key == "n":
            self._display_command_prompt("Enter note title:")
            # self._input_state = InputStates.SINGLE_INPUT
            title = self._get_single_line_input()
            entry = ListEntry.new_entry(title, "")
            self._incomplete_entries.append(entry)

        elif key in "0123456789":  # TODO: potentially optimizable
            self._input_number += key

        elif key == "d":
            index = self._parse_and_reset_index()
            self._incomplete_entries.pop(index)

        elif key == "e":
            index = self._parse_and_reset_index()
            entry = self._incomplete_entries[index]

            self._display_command_prompt(f"Editing entry number {index + 1}")

            self._input_window.addstr(0, 0, entry.title)
            new_title = self._get_single_line_input()
            entry.set_title(new_title)
        else:
            pass

    def _refresh_windows(self):
        self._main_window.refresh()
        self._command_window.refresh()
        self._input_window.refresh()

    def _show_entries(self):
        for i, entry in enumerate(self._incomplete_entries):
            self._main_window.addstr(i, 1, f"{i+1:3} - {entry.title}")

    def _show_help(self):
        self._main_window.clear()
        self._main_window.addstr(0, 0, "This is the help menu!")
        self._main_window.refresh()
        self._display_command_prompt("Help Menu - Press any key to exit...")
        self._command_window.getkey()

    def _parse_and_reset_index(self):
        try:
            index = int(self._input_number)
            self._input_number = ""
            if index - 1 > len(self._incomplete_entries):
                raise IndexError(f"Invalid index! ({index})")
            return index - 1
        except ValueError:
            raise ValueError("Please specify entry index first!")

    def _get_single_line_input(self):
        curses.curs_set(True)
        # curses.echo(True)

        self._input_textbox.edit()
        single_line_input = self._input_textbox.gather()
        self._input_state = InputStates.COMMAND

        # curses.echo(False)
        curses.curs_set(False)
        self._input_window.clear()
        self._command_window.clear()

        return single_line_input

    def _display_command_prompt(self, prompt: str):
        self._command_window.clear()
        self._command_window.addstr(0, 0, prompt)
        self._command_window.refresh()

    def _set_state(self, new_state: InputStates):
        self._input_state = new_state


def main(stdscr):
    # curses.curs_set(False)
    # stdscr.clear()

    vimdo = Vimdo(stdscr)
    vimdo.run()

    return
    # command_window = curses.newwin(
    #     1, curses.COLS - 1, curses.LINES - 3, 0
    # )
    # input_window = curses.newwin(
    #     1, curses.COLS - 1, curses.LINES - 2, 1
    # )
    # main_window = curses.newwin(
    #     curses.LINES - 3, curses.COLS - 1, 0, 0
    # )

    # incomplete_entries = []

    # input_state = InputStates.COMMAND
    # input_textbox = Textbox(input_window, insert_mode=True)
    # input_number = ""
    # while input_state != InputStates.EXITING:
    #     main_window.clear()

    #     for i, entry in enumerate(incomplete_entries):
    #         main_window.addstr(i + 1, 1, f"{i+1:3} - {entry.title}")

    #     main_window.refresh()
    #     command_window.refresh()
    #     input_window.refresh()

    #     if input_state == InputStates.COMMAND:
    #         key = stdscr.getkey()

    #         if key == curses.KEY_EXIT:
    #             input_number = ""
    #             input_state = InputStates.COMMAND
    #         if key == "q":
    #             input_state = InputStates.EXITING
    #         elif key == "n":
    #             command_window.addstr(
    #                 0, 1, "Enter note title: (Ctrl-G to confirm)"
    #             )
    #             input_state = InputStates.SINGLE_INPUT
    #         elif key in "0123456789":  # TODO: potentially optimizable
    #             input_number += key
    #         elif key == "d":
    #             try:
    #                 index = int(input_number)
    #                 input_number = ""
    #                 incomplete_entries.pop(index - 1)
    #             except ValueError:
    #                 command_window.addstr(
    #                     0,
    #                     1,
    #                     "Please specify entry index first! e.g '5d', '12d'",
    #                 )
    #             except IndexError:
    #                 command_window.addstr(0, 1, f"Invalid index! ({index})")
    #         elif key == "e":
    #             try:
    #                 index = int(input_number)
    #                 input_number = ""
    #                 entry = incomplete_entries[index]
    #             except ValueError:
    #                 command_window.addstr(
    #                     0,
    #                     1,
    #                     "Please specify entry index first! e.g '5d', '12d'",
    #                 )
    #             except IndexError:
    #                 command_window.addstr(0, 1, f"Invalid index! ({index})")

    #             input_window.addstr(0, 0, entry.title)
    #             input_state = InputStates.SINGLE_INPUT

    #     elif input_state == InputStates.SINGLE_INPUT:
    #         curses.curs_set(True)
    #         # curses.echo(True)
    #         input_window.clear()

    #         input_textbox.edit()
    #         single_input = input_textbox.gather()
    #         entry = ListEntry.new_entry(single_input, "")
    #         incomplete_entries.append(entry)
    #         input_state = InputStates.COMMAND

    #         # curses.echo(False)
    #         curses.curs_set(False)
    #         input_window.clear()
    #         command_window.clear()


if __name__ == "__main__":
    wrapper(main)
