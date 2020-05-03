"""Base Hangman playing class"""

import urllib.request
import time
import json
import functools
import os
import enum

from typing import Callable, Sequence, Optional, Set, List, NamedTuple, Union, Dict, Any

class GameStatus(enum.Enum):
	"""Status of a game"""
	INACTIVE = enum.auto()
	ACTIVE = enum.auto()
	LOST = enum.auto()
	WON = enum.auto()

	def __str__(self) -> str:
		return self.name

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
	status: GameStatus
	word: str
	guesses: List[Guess]

	max_lives: int

class HangmanOver(Exception):
	"""Raised when an action is attempted when the game is over"""


def gameover_protection(func: GuessMethod) -> GuessMethod:
	"""Prevent actions when game is over"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		if not self.active:
			raise HangmanOver(f'The game is {str(self.status)}')

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
			self.status = GameStatus.WON

		return ret_val
	return wrapper

def update_lives(func: GuessMethod) -> GuessMethod:
	"""Update remaining lives"""
	@functools.wraps(func)
	def wrapper(self: 'Hangman', guess: str) -> int:
		ret_val = func(self, guess)
		if not ret_val:
			self.lives -= 1

		if not self.lives:
			self.ended = time.time()
			self.status = GameStatus.LOST

		return ret_val
	return wrapper

class WordReader:
	"""Collection of methods to read word lists from various sources"""

	@staticmethod
	def parse_data(data: Union[Dict[Any, Any], List[str]]) -> Set[str]:
		"""Parse word data from object"""
		if not isinstance(data, Sequence):
			raise ValueError('data was not a sequence a words')

		return {word.upper() for word in data}

	@staticmethod
	def parse_text(text: str) -> Set[str]:
		"""Parse word data from text - seperated either by newline or commas"""
		delims = ['\n', ',']
		words: List[str] = []
		while delims and len(words) <= 1:
			words = [word for word in [word.strip() for word in text.split(delims.pop(0))] if word]

		return {word.upper() for word in words}

	@staticmethod
	def fetch_wordlist(location: str) -> Set[str]:
		"""Fetch wordlist from file or URL"""
		if location.startswith('http'):
			with urllib.request.urlopen(location) as response:
				content_type = response.headers.get('Content-Type').split(';')[0]

				if content_type == 'text/plain':
					return WordReader.parse_text(response.read().decode().strip())
				if content_type == 'application/json':
					return WordReader.parse_data(json.loads(response.read().decode()))

				raise NotImplementedError(f'Content type of {content_type} is unsupported')

		elif os.path.exists(location):
			with open(location) as word_file:
				content = word_file.read()

				try:
					return WordReader.parse_data(json.loads(content))
				except json.JSONDecodeError:
					return WordReader.parse_text(content)

		else:
			raise NotImplementedError('Handling for given location protocol is unsupported')


# pylint: disable=too-many-instance-attributes
class Hangman:
	"""Bare Hangman game"""
	ALWAYS_VISIBLE = set(' ')

	# pylint: disable=line-too-long
	def __init__(self, lives: int = 6, wordlist: Optional[Sequence[str]] = None, wordlocation: Optional[str] = None, allow_empty: bool = False):
		self.max_lives = lives
		self.wordbank: Set[str] = set()

		if wordlist:
			self.wordbank.update({word.upper() for word in wordlist})
		if wordlocation:
			self.wordbank.update(WordReader.fetch_wordlist(wordlocation))

		if not self.wordbank and not allow_empty:
			raise ValueError('No words loaded')

		self.rounds: List[GameState] = []

		self.started = 0.0
		self.ended: Optional[float] = None
		self.status = GameStatus.INACTIVE
		self.lives = lives

		self.word: str = ''
		self.used_words: Set[str] = set()

		self.guesses: List[Guess] = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

	@property
	def duration(self) -> float:
		"""Duration of game - either ended or current"""
		return (self.ended or time.time()) - self.started

	@property
	def won(self) -> bool:
		"""If the game has been won"""
		return self.status == GameStatus.WON

	@property
	def lost(self) -> bool:
		"""If the game has been lost"""
		return self.status == GameStatus.LOST

	@property
	def active(self) -> bool:
		"""If the game is active"""
		return self.status == GameStatus.ACTIVE

	@property
	def inactive(self) -> bool:
		"""If the game is inactive"""
		return self.status == GameStatus.INACTIVE

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

	@property
	def state(self) -> GameState:
		"""Get current state of the game"""
		return GameState(self.started, self.ended, self.status, self.word, self.guesses, self.max_lives)

	def start(self, word: Optional[str] = None) -> 'Hangman':
		"""Start the game"""
		if len(self.wordbank) == len(self.used_words):
			self.used_words = set()

		if self.status != GameStatus.INACTIVE:
			self.rounds.append(self.state)

		if word:
			self.word = word
		elif self.wordbank:
			self.word = next(word for word in self.wordbank if word not in self.used_words)
			self.used_words.add(self.word)
		else:
			self.word = ''

		self.started = time.time()
		self.ended = None
		self.lives = self.max_lives
		self.status = GameStatus.ACTIVE if self.word else GameStatus.INACTIVE

		self.guesses = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

		return self

	def stop(self) -> 'Hangman':
		"""Stop any current game, saving if active"""
		if not self.ended:
			self.ended = time.time()

		if self.status != GameStatus.INACTIVE:
			self.rounds.append(self.state)

		self.word = ''
		self.started = time.time()
		self.ended = None
		self.lives = self.max_lives
		self.status = GameStatus.INACTIVE

		self.guesses = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

		return self


	@record_win
	@update_lives
	@record_guess
	@record_visible_letters
	@gameover_protection
	def guess_letter(self, letter: str) -> int:
		"""Guess a letter"""
		return letter in self.word

	@record_win
	@update_lives
	@record_guess
	@record_visible_letters
	@gameover_protection
	def guess_word(self, word: str) -> int:
		"""Guess the entire word"""
		return word == self.word
