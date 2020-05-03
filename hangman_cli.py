"""CLI version of Hangman"""

import subprocess
import textwrap
import os

from typing import Dict, Callable, Tuple, Union, NamedTuple, Optional

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
		response = input('> ').upper()
		if not response.isnumeric():
			if not response.isalpha():
				print('Input must be a number')
				continue
			response = str(ord(response) - 64)

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
	def __init__(self, wordfile: str) -> None:
		super().__init__(
			lives=6,
			wordlocation=wordfile if os.path.exists(wordfile) else None,
			allow_empty=True
		)
		self.wordfile = wordfile
		self._next_word: Optional[str] = None


		self.current_menu_slug: Optional[str] = None
		self.menus = {
			'main': Menu(None, {
				'Exit': (lambda: print('Thanks for playing!'), None),
				'Play Computer': 'play',
				'Play Other': 'play-other',
				'Manage Words': 'manage-words',
			}),
			# pylint: disable=line-too-long
			'manage-words': Menu(lambda: f'Here you can modify the wordbank used by the program, in which there are currently {len(self.wordbank)} words', {
				'Back': 'main',
				'Add': 'add-words',
				'View': self.view_words,
				'Clear': self.clear_words,
				'Remove': self.remove_word
			}),
			'add-words': Menu('Add words or word sources to the wordbank', {
				'Back': 'manage-words',
				'Add Word': self.add_word,
				'Add Wordlist': self.add_wordlist,
			}),
			'play': Menu(None, self.gameplay),
			'play-other': Menu(None, self.play_other)
		}

	@property
	def next_word(self) -> Optional[str]:
		"""Get - and clear - the next word"""
		word = self._next_word
		self._next_word = None
		return word

	@next_word.setter
	def next_word(self, value: str) -> None:
		"""Set the next word"""
		self._next_word = value

	def save_wordfile(self) -> None:
		"""Save content of wordbank to wordfile"""
		with open(self.wordfile, 'w') as wordfile:
			wordfile.write('\n'.join(self.wordbank))

	def view_words(self) -> None:
		"""View words in wordfile"""
		clear_screen()
		print(', '.join(sorted(self.wordbank)))
		print(f'{len(self.wordbank)} words loaded')

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
			self.save_wordfile()

	def add_word(self) -> None:
		"""Ask the user for a word to add to the wordbank"""
		clear_screen()
		word = input('Enter word to add: ').upper()

		print(
			'Word already in word bank'
			if word in self.wordbank else
			'Word added'
		)

		self.wordbank.add(word)
		self.save_wordfile()

	def add_wordlist(self) -> None:
		"""Add a wordlist to the wordbank"""
		clear_screen()
		location = input('Enter location of wordlist: ')
		try:
			before = len(self.wordbank)
			self.wordbank.update(WordReader.fetch_wordlist(location))
			print(f'{len(self.wordbank) - before} words added from "{location}"')
			self.save_wordfile()
		except (ValueError, NotImplementedError) as ex:
			print(f'Exception occured fetching wordlist from {location}: {ex}')

	def play_other(self) -> MenuResponse:
		"""Ask user for word to guess"""
		while True:
			word = input('Enter word for other player to guess: ').upper()
			if word:
				break

			print('Word required')

		self.next_word = word
		return 'play'

	def gameplay(self) -> MenuResponse:
		"""Have the user play an entire round of the game"""
		clear_screen()
		if self.inactive:
			if not self.wordbank and not self.next_word:
				print('No words in wordbank')
				return 'main'

			self.start(self.next_word or None)


		print(FRAMES[len(FRAMES) - 1 - self.lives].join(IMAGE))
		print(f'Word: {self.visible_word}')
		char_guesses = [guess.guess for guess in self.guesses]
		print(f'Guesses: {", ".join(char_guesses)}')
		if self.active:
			while True:
				guess = input('Enter Guess: ').upper()

				# pylint: disable=line-too-long
				msg = 'Guess required' if not guess else 'Already guessed that' if guess in char_guesses else None
				if not msg:
					break

				print(msg)

			revealed = getattr(self, 'guess_' + ('word' if len(guess) > 1 else 'letter'))(guess)
			print(
				f'You revealed {revealed} characters'
				if revealed else
				'Invalid guess'
			)

			return 'play'

		print(
			textwrap.dedent(f'''
			You won!

			It took you {self.duration:.1f} seconds - about {self.duration / self.guess_count:.1f} seconds per guess, of which you took {self.guess_count} - to guess "{self.word}"!
			''')
			if self.won else
			textwrap.dedent(f'''
			You Lost!

			You couldn't guess "{self.word}" in {self.duration:.1f} seconds, at a rate of {self.duration / self.guess_count:.1f} seconds per guess, of which you took {self.guess_count}...
			''')
		)
		self.stop()
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


IMAGE = ['  +---+\n  |   |\n', '      |\n=========']
FRAMES = [
	'      |\n      |\n      |\n',
	'  O   |\n      |\n      |\n',
	'  O   |\n  |   |\n      |\n',
	'  O   |\n /|   |\n      |\n',
	'  O   |\n /|\\  |\n      |\n',
	'  O   |\n /|\\  |\n /    |\n',
	'  O   |\n /|\\  |\n / \\  |\n'
]

if __name__ == '__main__':
	HangmanCLI(wordfile='wordlist.txt').run()
