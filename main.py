from curses import wrapper
from curses.textpad import Textbox

import curses
import enum
import io
import os


class InputStates(enum.Enum):
    EXITING = -1
    COMMAND = 0
    HELP = 1
    TEXT_INPUT = 2


class StringEntryData:
    def __init__(self, data):
        self._data = data

    def string(self):
        return self._data

    def lines(self):
        return self._data.split("\n")

    def write(self, data):
        self._data = data

    def append(self, data):
        self._data += data


class ListEntry:
    def __init__(self, title: str, data: StringEntryData):
        self._title = title.strip()
        self._data = data
        self._link = None

    @property
    def title(self):
        return self._title

    @property
    def data(self):
        return self._data

    def set_title(self, new_title: str):
        self._title = new_title.strip()

    def set_data(self, new_data: str):
        self._data = StringEntryData(new_data)

    def set_link(self, link: str):
        self._link = link

    @classmethod
    def new_entry(cls, title: str, data: str):
        return ListEntry(title, data)


class EntryBuffer:
    def __init__(self):
        self._entries = []

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def append(self, entry: ListEntry):
        self._entries.append(entry)

    def remove(self, index: int):
        if 0 <= index < len(self._entries):
            return self._entries.pop(index)

        raise IndexError("No such entry")

    def entries(self):
        return self._entries


class FilePersistence:
    def __init__(self, path: str):
        self._path = path

    def save(self, output_buffer):
        with open(self._path, "w") as f:
            f.write(output_buffer.getvalue())

    def load(self):
        with open(self._path, "r") as f:
            data = f.readlines()
            return data


class VimdoSerializer:

    TITLE_PREFIX = "### "
    DATA_PREFIX = "      "

    def __init__(self):
        pass

    def serialize(self, entry_buffer):
        output = io.StringIO()

        for entry in entry_buffer.entries():
            title = f"{self.TITLE_PREFIX}{entry.title}"
            data = "\n".join(
                [
                    f"{self.DATA_PREFIX}{line}"
                    for line in entry.data.lines()
                ]
            )

            serialized_entry = f"{title}\n{data}\n\n"
            output.write(serialized_entry)

        return output

    def deserialize(self, serialized, entry_buffer):
        title = None
        data = []
        for line in serialized:
            if line.startswith(self.TITLE_PREFIX):
                if title is not None:  # Should commit previous entry
                    entry_buffer.append(
                        ListEntry(title, StringEntryData("\n".join(data)))
                    )
                    title = None
                    data = []

                title = line[len(self.TITLE_PREFIX):]
            elif line.startswith(self.DATA_PREFIX):
                data_line = line[len(self.DATA_PREFIX):].strip('\n')
                data.append(f"{data_line}")
        entry_buffer.append(
            ListEntry(title, StringEntryData("\n".join(data)))
        )


class Vimdo:
    def __init__(
        self,
        stdscr,
        entry_buffer: EntryBuffer,
        serializer: VimdoSerializer,
        storage: FilePersistence,
    ):
        self._stdscr = stdscr
        self._buffer = entry_buffer
        self._serializer = serializer
        self._storage = storage

        self._command_window = curses.newwin(
            1, curses.COLS - 2, curses.LINES - 3, 1
        )
        self._input_window = curses.newwin(
            1, curses.COLS - 2, curses.LINES - 2, 1
        )
        self._main_window = curses.newwin(
            curses.LINES - 3, curses.COLS - 2, 1, 1
        )

        self._input_state = InputStates.COMMAND
        self._input_number = ""
        self._line_input_textbox = Textbox(
            self._input_window, insert_mode=True
        )
        self._main_input_textbox = Textbox(self._main_window, insert_mode=True)

    def run(self):
        curses.curs_set(False)
        self._stdscr.clear()

        errored = None

        while self._input_state != InputStates.EXITING:
            self._main_window.clear()

            self._show_entries()
            self._refresh_windows()

            if self._input_state == InputStates.COMMAND:
                output = errored if errored is not None else self._input_number
                self._display_command_prompt(f"COMMAND [{output}]")
                key = self._command_window.getkey()

                try:
                    self._parse_and_run_command(key)
                    errored = None
                except Exception as err:
                    errored = err

    def _parse_and_run_command(self, key: str):
        if key.startswith(r"^["):  # ESC key
            self._input_number = ""
        elif key == "q":
            self._input_state = InputStates.EXITING
        elif key == "h":
            self._show_help()
        elif key == "n":
            self._display_command_prompt("Enter note title:")
            title = self._get_single_line_input()
            entry = ListEntry.new_entry(
                title,
                StringEntryData("Testing data line!\nThis is another line"),
            )
            self._buffer.append(entry)

        elif key in "0123456789":  # TODO: potentially optimizable
            if key == "0" and self._input_number == "":
                return
            self._input_number += key

        elif key == "d":
            index = self._parse_and_reset_index()
            if len(self._buffer) > 0:
                self._buffer.remove(index)
            else:
                raise Exception("No entries to delete!")

        elif key == "e":
            index = self._parse_and_reset_index()
            entry = self._buffer[index]

            self._display_command_prompt(f"Editing entry number {index + 1}")

            new_title = self._get_single_line_input(entry.title.strip())
            entry.set_title(new_title)
        elif key == "s":
            self._persist_entries()
            self._display_command_prompt("List saved!")
        elif key == "l":
            self._load_entries()
        elif key in (curses.KEY_ENTER, "\n", "\r"):
            index = self._parse_and_reset_index()
            entry = self._buffer[index]

            self._display_command_prompt(
                f"Editing data for entry {index + 1}..."
            )
            data = self._get_multi_line_input(entry.data.string())
            entry.set_data(data)
        else:
            self._input_number = ""
            raise NotImplementedError(
                f"Unknown command: {key} - Try 'h' for help"
            )

    def _refresh_windows(self):
        self._main_window.refresh()
        self._command_window.refresh()
        self._input_window.refresh()

    def _show_entries(self):
        for i, entry in enumerate(self._buffer):
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
            if index - 1 > len(self._buffer) > 0:
                raise IndexError(f"Invalid index! ({index})")
            return index - 1
        except ValueError:
            raise ValueError("Please specify entry index first!")

    def _get_multi_line_input(self, placeholder=None):
        curses.curs_set(True)

        self._main_window.clear()
        if placeholder is not None:
            self._main_window.addstr(placeholder)

        self._main_input_textbox.edit()
        output = self._main_input_textbox.gather()
        self._input_state = InputStates.COMMAND

        curses.curs_set(False)
        self._main_window.clear()
        self._command_window.clear()

        return output

    def _get_single_line_input(self, placeholder=None):
        curses.curs_set(True)
        # curses.echo(True)

        self._input_window.clear()
        if placeholder is not None:
            self._input_window.addstr(placeholder)

        self._line_input_textbox.edit()
        single_line_input = self._line_input_textbox.gather()
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

    def _persist_entries(self):
        serialized = self._serializer.serialize(self._buffer)
        self._storage.save(serialized)

    def _load_entries(self):
        self._buffer = EntryBuffer()
        serialized = self._storage.load()
        self._serializer.deserialize(serialized, self._buffer)


def main(stdscr):
    entry_buffer = EntryBuffer()
    serializer = VimdoSerializer()
    file_storage = FilePersistence(os.path.join(os.path.curdir, "todo.vimdo"))

    vimdo = Vimdo(stdscr, entry_buffer, serializer, file_storage)
    vimdo.run()

    return


if __name__ == "__main__":
    wrapper(main)
