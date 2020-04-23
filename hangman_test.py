"""Test base Hangman class"""
import os

import unittest
import unittest.mock
import tempfile

from hangman import Hangman, WordReader, GameState, Guess


class WordReaderTest(unittest.TestCase):
	"""Test WordReader methods"""

	def test_invalid_resources(self) -> None:
		"""Invalid resources raise exceptions"""
		# Non-sequence JSON wordlist
		with self.assertRaises(Exception):
			WordReader.fetch_wordlist('https://httpbin.org/json')

		# Unexpected content type
		with self.assertRaises(NotImplementedError):
			WordReader.fetch_wordlist('https://httpbin.org/status/200')

		# Unknown location
		with self.assertRaises(NotImplementedError):
			WordReader.fetch_wordlist('notarealfile')

	def test_load_text(self) -> None:
		"""Words loaded from text file"""
		with tempfile.NamedTemporaryFile() as temp:
			temp.write(b'abc\ndef\nghi\n')
			temp.flush()

			self.assertEqual(WordReader.fetch_wordlist(temp.name), {'ABC', 'DEF', 'GHI'})

		with tempfile.NamedTemporaryFile() as temp:
			temp.write(b'qwe, rty, uio\n')
			temp.flush()

			self.assertEqual(WordReader.fetch_wordlist(temp.name), {'QWE', 'RTY', 'UIO'})

	def test_load_json(self) -> None:
		"""Words loaded from JSON array"""
		with tempfile.NamedTemporaryFile() as temp:
			temp.write(b'["abc", "def", "ghi"]')
			temp.flush()

			self.assertEqual(WordReader.fetch_wordlist(temp.name), {'ABC', 'DEF', 'GHI'})

	@unittest.skipUnless(os.getenv('CI'), 'CI not enabled')
	def test_fetch_text(self) -> None:
		"""Text wordlist is fetched"""
		self.assertEqual(
			len(WordReader.fetch_wordlist(
				'https://raw.githubusercontent.com/Xethron/Hangman/master/words.txt'
			)),
			850
		)

	@unittest.skipUnless(os.getenv('CI'), 'CI not enabled')
	def test_fetch_json(self) -> None:
		"""JSON wordlist is fetched"""
		self.assertEqual(
			len(WordReader.fetch_wordlist(
				'https://cdn.jsdelivr.net/gh/bevacqua/correcthorse/wordlist.json'
			)),
			2286
		)

class HangmanTest(unittest.TestCase):
	"""Test the base Hangman class"""

	def test_win(self) -> None:
		"""Won state is set"""
		game = Hangman(wordlist=['ONE WORD'])
		self.assertEqual(game.guess_word('ONE WORD'), 7)
		self.assertEqual(game.guess_count, 1)
		self.assertTrue(game.won)

	def test_gameover_protection(self) -> None:
		"""Actions are prevented when game is over"""
		game = Hangman(wordlist=['GAME OVER'])
		self.assertEqual(game.guess_word('GAME OVER'), 8)
		with self.assertRaises(Exception):
			game.guess_letter('A')

	@unittest.skipUnless(os.getenv('CI'), 'CI not enabled')
	def test_no_wordlist(self) -> None:
		"""Ensure error when no words loaded"""
		# Empty wordlist
		with self.assertRaises(ValueError):
			Hangman()
		with self.assertRaises(ValueError):
			Hangman(wordlist=[])

	@unittest.mock.patch('hangman.WordReader')
	def test_calls_wordreader(self, wordreader: unittest.mock.MagicMock) -> None:
		"""Calls WordReader when given given location"""
		with self.assertRaises(ValueError):
			Hangman(wordlocation='hello world')

		wordreader.fetch_wordlist.assert_called_with('hello world')

	def test_wordlist_uppercase(self) -> None:
		"""Ensure the wordlist is all uppercase"""
		self.assertEqual(Hangman(wordlist=['hello']).wordbank, {'HELLO'})

	def test_visible_word(self) -> None:
		"""Visible word contains guessed letters"""
		game = Hangman(wordlist=['ECHO LOCATION'])
		self.assertEqual(game.guess_letter('O'), 3)
		self.assertEqual(game.visible_word, '___O _O____O_')
		self.assertEqual(game.guess_word('ECHO LOCATION'), 9)
		self.assertEqual(game.guess_count, 2)
		self.assertTrue(game.won)

	def test_guesses(self) -> None:
		"""Guessing returns correct counts and history matches"""
		game = Hangman(wordlist=['KITTY CAT'])
		self.assertEqual(game.guess_letter('M'), 0)
		self.assertEqual(game.guess_letter('I'), 1)
		self.assertEqual(game.guess_letter('T'), 3)
		self.assertEqual(game.guess_word('KITTY CAT'), 4)
		self.assertEqual(
			[tuple(guess[1:]) for guess in game.guesses],
			[('M', 0), ('I', 1), ('T', 3), ('KITTY CAT', 4)]
		)
		self.assertEqual(game.guess_count, 4)
		self.assertTrue(game.won)

	def test_word_reuse(self) -> None:
		"""Wordbank is refreshed when exhausted"""
		game = Hangman(wordlist=['123', '456'])
		game.restart()
		game.restart()
		self.assertTrue(game.word in ['123', '456'])

	@unittest.mock.patch('time.time', return_value=0.0)
	def test_restart_state(self, _: unittest.mock.MagicMock) -> None:
		"""State is reset when restarting"""
		game = Hangman(wordlist=['ABC', 'DEF'])
		word = game.word
		self.assertEqual(game.guess_word(word), 3)
		self.assertIsInstance(game.ended, float)
		self.assertTrue(game.won)
		self.assertTrue(game.duration < 1)

		state = GameState(0.0, 0.0, word, [Guess(0.0, word, 3)])
		self.assertTupleEqual(game.restart(), state)

		self.assertNotEqual(game.word, word)
		self.assertEqual(game.guesses, [])
		self.assertFalse(game.won)
		self.assertTrue(game.duration < 1)
		self.assertEqual(game.rounds, [state])

if __name__ == '__main__':  # pragma: no cover
	unittest.main()
