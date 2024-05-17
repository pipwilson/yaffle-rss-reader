Yaffle is a toy cross-platform desktop RSS reader that delegates all the actually hard work off to https://github.com/nkanaev/yarr, which is a very good single-binary self-hosted RSS reader that presents a nice API for us to use.

Yaffle uses wxPython as the UI layer.

## Notes

Application dependencies are managed with [Poetry](https://python-poetry.org/).

The Python versions supported mirror the versions supported by PyInstaller, which is used to build the exe for Windows.

Install Poetry and run `poetry install` followed by `poetry run python yaffle.py`.

To build the binary:

`poetry run python -m PyInstaller yaffle.spec`

https://pyinstaller.org/en/stable/spec-files.html

Ran SVGs from https://feathericons.com/ through https://svgtopng.com/

[Woodpecker icons created by Icongeek26 - Flaticon](https://www.flaticon.com/free-icons/woodpecker)