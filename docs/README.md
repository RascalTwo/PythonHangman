# Python Hangman

[![Python Workflow](https://github.com/RascalTwo/PythonHangman/workflows/.github/workflows/python.yml/badge.svg)](/../../actions)
[![Run on Repl.it](https://repl.it/badge/github/RascalTwo/PythonHangman)](https://repl.it/github/RascalTwo/PythonHangman)

|   |   |   |
| - | - | - |
| ![CLI](/../../blob/assets/cli.svg?raw=true "CLI") | [![GUI](/../../blob/assets/gui.gif?raw=true "GUI")](/../../blob/assets/gui.webm?raw=true) | [![Discord](/../../blob/assets/discord.gif?raw=true "Discord")](/../../blob/assets/discord.webm?raw=true) |

Hangman written with three interfaces: CLI, `tkinter`, and `discord.py`.

## How It's Made

**Tech used:** Python, `tkinter`, `discord.py`

The core of the game is written in Python, with the CLI, Discord, and `tkinter` GUI variants extending it.

Most dependencies are only required for development, so while there is a
`requirements.txt` and `pyproject.toml`, no installation is actually
required if you only wish to explore the `tkinter` and CLI varients.

If you wish to use the `discord.py` varient though, `discord.py` must be
installed.

> If you do encounter any errors executing `poetry install`, simply
> delete the `poetry.lock` file and try again.

## Optimizations

While there aren't too many optimizations to be made to the existing code, there can always be new interfaces added.

## Lessons Learned

It was a great practice in writing a single core game and extending it to various interfaces, learning about not only the differences between the interfaces, but additionally coverage tests and different ways to manage Python dependencies.

## Usage

The playable variations are within `hangman_cli.py`, `hangman_gui.py`,
and `hangman_discord.py`, so you can simply run these files or use the
`gui`/`cli`/`discord DISCORD_BOT_TOKEN` `invoke` tasks:

```sh
python3 hangman_cli.py
poetry run invoke cli

python3 hangman_gui.py
poetry run invoke gui

python3 hangman_discord.py DISCORD_BOT_TOKEN
poetry run invoke discord DISCORD_BOT_TOKEN
```

> Replace `DISCORD_BOT_TOKEN` with your [Discord Bot
> Token](https://discordapp.com/developers/applications).

### Repl&#46;it

If you wish to switch between UIs, you **Must** choose `Tkinter` when
told to `select language`, otherwise the `tkinter` varient will not be
usable.

## Walkthrough

The game and wordlist logic itself has been kept within `hangman.py`,
which is also the only file that has 100% test coverage.

Decided to do it this way as it would make porting to other UIs
relatively seamless, although I had enough time to create two.

***

The tests - powered by `unittest` - also have coverage tracking - with
optional single-file HTML output - available via the invoke `test` task.

I’ve also included `mypy` for type checking, and `pylint` for linting -
also with single-file HTML output.

Aimed for single-file HTML outputs to allow for easy asset uploading.

***

Included is a GitHub workflow that:

- Checks out the code
- Obtains Python
- Installs poetry and dependancies
- Runs mypy, pylint, and tests
- Uploads the pylint and test HTML atrifacts - if availale
- Outputs the results of mypy, pylint, and tests

***

There are more interfaces I thought of adapting it to, and may do so in
the future.
