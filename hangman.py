"""Base Hangman playing class"""

import urllib.request
import time
import json
import functools

from typing import Callable, Sequence, Optional, Set, List, NamedTuple


GuessMethod = Callable[['Hangman', str], int]

class Guess(NamedTuple):
	"""User guess"""
	when: float
	guess: str
	revealed: int

class GameState(NamedTuple):
	"""State of a single game"""
	started: float
	ended: Optional[float]
	word: str
	guesses: List[Guess]

class HangmanOver(Exception):
	"""Raised when an action is attempted when the game is over"""


def gameover_protection(func: GuessMethod) -> GuessMethod:
	"""Prevent actions when game is over"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		if self.ended:
			raise HangmanOver()

		return func(self, guess)
	return wrapper

def record_guess(func: GuessMethod) -> GuessMethod:
	"""Record the guess"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		ret_val = func(self, guess)
		self.guesses.append(Guess(time.time(), guess, int(ret_val)))
		return ret_val
	return wrapper

def record_visible_letters(func: GuessMethod) -> GuessMethod:
	"""Update the visible letters"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		ret_val = func(self, guess)
		if not ret_val:
			return ret_val

		already_visible = self.visible_letters.copy()
		self.visible_letters.update(set(guess))

		new_letters = set(guess) & self.visible_letters
		## pylint: disable=line-too-long
		return sum(1 for char in self.visible_word if char in new_letters and char not in already_visible)
	return wrapper

def record_win(func: GuessMethod) -> GuessMethod:
	"""Record when the user wins"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		ret_val = func(self, guess)
		if not ret_val:
			return ret_val

		if self.visible_word == self.word:
			self.ended = time.time()

		return ret_val
	return wrapper

# pylint: disable=too-many-instance-attributes
class Hangman:
	"""Bare Hangman game"""
	ALWAYS_VISIBLE = set(' ')

	def __init__(self, wordlist: Optional[Sequence[str]] = None, wordlocation: Optional[str] = None):
		self.wordbank: Set[str] = set()

		if wordlist:
			self.wordbank.update(set(wordlist))
		if wordlocation:
			if wordlocation.startswith('http'):
				with urllib.request.urlopen(wordlocation) as response:
					content_type = response.headers.get('Content-Type').split(';')[0]

					if content_type.startswith('text'):
						self.wordbank.update(
							set(filter(lambda word: word, response.read().decode().strip().split('\n')))
						)

					elif content_type == 'application/json':
						data = json.loads(response.read().decode())

						if not isinstance(data, Sequence):
							raise Exception('JSON data was not a list a words')

						self.wordbank.update(set(data))

		if not self.wordbank:
			raise Exception('No words loaded')

		self.rounds: List[GameState] = []

		self.started = 0.0
		self.ended: Optional[float] = None

		self.word: str = ''
		self.used_words: Set[str] = set()

		self.guesses: List[Guess] = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

		self.restart(False)

	@property
	def duration(self) -> float:
		"""Duration of game - either ended or current"""
		return (self.ended or time.time()) - self.started

	@property
	def won(self) -> bool:
		"""If the game has been won"""
		return self.ended is not None

	@property
	def guess_count(self) -> int:
		"""Number of guessed made"""
		return len(self.guesses)

	@property
	def visible_word(self) -> str:
		"""Currently visible word"""
		visible_word = ''
		for char in self.word:
			visible_word += char if char in self.visible_letters or char in self.ALWAYS_VISIBLE else '_'
		return visible_word

	def restart(self, save: bool = True) -> GameState:
		"""Restart the game, picking a new unique word"""
		if len(self.wordbank) == len(self.used_words):
			self.used_words = set()

		state = GameState(self.started, self.ended, self.word, self.guesses)
		if save:
			self.rounds.append(state)

		self.word = next(word for word in self.wordbank if word not in self.used_words)
		self.used_words.add(self.word)
		self.started = time.time()
		self.ended = None

		self.guesses = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

		return state

	@record_win
	@record_guess
	@record_visible_letters
	@gameover_protection
	def guess_letter(self, letter: str) -> int:
		"""Guess a letter"""
		return letter in self.word

	@record_win
	@record_guess
	@record_visible_letters
	@gameover_protection
	def guess_word(self, word: str) -> int:
		"""Guess the entire word"""
		return word == self.word
