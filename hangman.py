"""Base Hangman playing class"""

import urllib.request
import time
import json
import functools

from typing import Callable, Sequence, Optional, Tuple, Set, List
GuessMethod = Callable[['Hangman', str], int]
Guess = Tuple[float, str, int]

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
		self.guesses.append((time.time(), guess, ret_val))
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

class Hangman:
	"""Bare Hangman game"""
	ALWAYS_VISIBLE = set(' ')

	def __init__(self, wordlist: Optional[Sequence[str]] = None, wordlocation: Optional[str] = None):
		if wordlist:
			self.wordbank = set(wordlist)
		elif wordlocation:
			if wordlocation.startswith('http'):
				with urllib.request.urlopen(wordlocation) as response:
					content_type = response.headers.get('Content-Type').split(';')[0]
					if content_type == 'text/plain':
						self.wordbank = set(filter(lambda word: word, response.read().decode().strip().split('\n')))
					elif content_type == 'application/json':
						self.wordbank = json.loads(response.read().decode())

		self.used_words: Set[str] = set()
		self.guesses: List[Guess] = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()
		self.started = 0.0
		self.ended: Optional[float] = None
		self.restart()

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

	def restart(self) -> None:
		"""Restart the game, picking a new unique word"""
		if len(self.wordbank) == len(self.used_words):
			self.used_words = set()

		self.word = next(word for word in self.wordbank if word not in self.used_words)
		self.used_words.add(self.word)
		self.started = time.time()
		self.ended = None

		self.guesses = []
		self.visible_letters = self.ALWAYS_VISIBLE.copy()

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
