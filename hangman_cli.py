"""CLI version of Hangman"""

import subprocess
import textwrap
import time

from typing import Dict, Callable, Tuple, Union, NamedTuple, Optional, Any

from hangman import Hangman, WordReader


# The optional slug of the next menu
# A method that returns nothing, causing the menu not to change
# A tuple of a method that returns nothing and the next menu slug.
MenuResponse = Optional[Union[
	str,
	Callable[[], None],
	Tuple[Callable[[], None], Optional[str]]
]]

class Menu(NamedTuple):
	"""Menu structure containing other menus and responses"""
	# Text to be display when menu is entered, if
	# included can be a string or a method that is called to return a strig
	prompt: Optional[Union[str, Callable[[], str]]]

	# A dict of options with menu response values or a method called which returns a menu response
	options: Union[Dict[str, MenuResponse], Callable[[], MenuResponse]]

def get_choice(*options: str) -> str:
	"""Get the choice of a user"""
	for i, option in enumerate(options):
		print(f'{i + 1:02d}. {option}')

	while True:
		response = input('> ')
		if not response.isnumeric():
			print('Input must be a number')
			continue

		number = int(response)
		if number <= 0 or number > len(options):
			print(f'Choice must be between 1 and {len(options)}')
			continue

		return options[number - 1]


def clear_screen() -> None:
	"""Attempt to clear the screen"""
	subprocess.call('cls || clear', shell=True, stderr=subprocess.PIPE)

class HangmanCLI(Hangman):
	"""CLI variation of Hangman"""
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)

		self.current_menu_slug: Optional[str] = None
		self.menus = {
			'main': Menu(None, {
				'Exit': (lambda: print('Thanks for playing!'), None),
				'Play Single': 'play',
				'Edit Words': 'edit-words',
			}),
			# pylint: disable=line-too-long
			'edit-words': Menu(lambda: f'Here you can modify the wordbank used by the program, in which there are currently {len(self.wordbank)} words', {
				'Back': 'main',
				'Add Words': 'add-words',
				'Clear Words': self.clear_words,
				'Remove Word': self.remove_word
			}),
			'add-words': Menu('Add words or word sources to the wordbank', {
				'Back': 'edit-words',
				'Add Word': self.add_word,
				'Add Wordlist': self.add_wordlist,
			}),
			'play': Menu(None, self.gameplay)
		}

	def clear_words(self) -> None:
		"""Clear the wordbank"""
		clear_screen()
		print(f'{len(self.wordbank)} words cleared')
		self.wordbank = set()

	def remove_word(self) -> None:
		"""Ask the user for a word to remove from the wordbank"""
		clear_screen()
		word = input('Enter the word you wish to remove: ').upper()
		if word not in self.wordbank:
			print('Word not found')
		else:
			print('Word removed')
			self.wordbank.remove(word)

	def add_word(self) -> None:
		"""Ask the user for a word to add to the wordbank"""
		clear_screen()
		word = input('Enter word to add: ').upper()

		if word in self.wordbank:
			print('Word already in word bank')
		else:
			print('Word added')

		self.wordbank.add(word)

	def add_wordlist(self) -> None:
		"""Add a wordlist to the wordbank"""
		clear_screen()
		location = input('Enter location of wordlist: ')
		try:
			self.wordbank.update(WordReader.fetch_wordlist(location))
		except (ValueError, NotImplementedError) as ex:
			print(f'Exception occured: {ex}')

	def gameplay(self) -> MenuResponse:
		"""Have the user play an entire round of the game"""
		clear_screen()
		if not self.wordbank:
			print('No words in wordbank')
			return 'main'

		if not self.guess_count:
			self.started = time.time()

		print(f'Word: {self.visible_word}')
		char_guesses = [guess.guess for guess in self.guesses]
		print(f'Guesses: {", ".join(char_guesses)}')
		while True:
			guess = input('Enter Guess: ').upper()

			if not guess:
				print('Guess required')
				continue
			if guess in char_guesses:
				print('Already guessed that')
				continue

			break

		revealed = getattr(self, 'guess_' + ('word' if len(guess) > 1 else 'letter'))(guess)
		print(
			f'You revealed {revealed} characters'
			if revealed else
			'Invalid guess'
		)

		if not self.won:
			return 'play'

		# pylint: disable=line-too-long
		print(textwrap.dedent(f'''
		You won!

		It took you {self.duration:.0f} seconds - about {self.duration / self.guess_count:.1f} seconds per guess, of which you took {self.guess_count} - to guess "{self.word}"!
		'''))

		self.restart()
		return 'main'


	def run(self) -> None:
		"""Start the CLI"""
		clear_screen()
		print(textwrap.dedent('''
		Welcome to Hangman!
		You can jump straight into a game, or edit the wordbank.
		What will it be?
		'''))

		self.current_menu_slug = 'main'
		while self.current_menu_slug:
			menu = self.menus[self.current_menu_slug]

			# Display str/method prompt - if exists
			if menu.prompt:
				print(menu.prompt if isinstance(menu.prompt, str) else menu.prompt())

			# Get choice from user if dict else get response from dynamic method
			value = (
				menu.options[get_choice(*menu.options.keys())]
				if isinstance(menu.options, dict)
				else menu.options()
			)

			# If a method, call and maintain current menu
			if callable(value):
				value()
				continue

			# Otherwise if tuple, call the method and expose next slug
			if isinstance(value, tuple):
				value[0]()
				value = value[1]

			# If there
			self.current_menu_slug = value

if __name__ == '__main__':
	HangmanCLI(wordlocation='wordlist.txt').run()
