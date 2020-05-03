"""Test base Hangman class"""
import os

import unittest
import unittest.mock
import tempfile

from hangman import Hangman, WordReader, GameState, GameStatus, Guess, HangmanOver


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

	def test_inactive(self) -> None:
		"""Is properly set to inactive"""
		with self.assertRaises(HangmanOver):
			Hangman(wordlist=['one']).guess_letter('o')

		with self.assertRaises(HangmanOver):
			Hangman(allow_empty=True).start().guess_letter('o')

		self.assertTrue(Hangman(allow_empty=True).inactive)

	@unittest.mock.patch('time.time', return_value=0.0)
	def test_stop(self, _: unittest.mock.MagicMock) -> None:
		"""Game can be stopped"""
		game = Hangman(wordlist=['one']).start()
		self.assertTrue(game.active)
		game.stop()
		self.assertTrue(game.inactive)
		self.assertEqual(game.rounds, [GameState(0.0, 0.0, GameStatus.ACTIVE, 'ONE', [], 6)])

	def test_win(self) -> None:
		"""Won state is set"""
		game = Hangman(wordlist=['ONE WORD']).start()
		self.assertEqual(game.guess_word('ONE WORD'), 7)
		self.assertEqual(game.guess_count, 1)
		self.assertTrue(game.won)

	def test_gameover_protection(self) -> None:
		"""Actions are prevented when game is over"""
		game = Hangman(wordlist=['GAME OVER']).start()
		self.assertEqual(game.guess_word('GAME OVER'), 8)
		with self.assertRaises(HangmanOver):
			game.guess_letter('A')

	def test_no_wordlist(self) -> None:
		"""Ensure error when no words loaded"""
		# Empty wordlist
		with self.assertRaises(ValueError):
			Hangman()
		with self.assertRaises(ValueError):
			Hangman(wordlist=[])

	def test_uses_provided_word(self) -> None:
		"""Uses word provided"""
		game = Hangman(allow_empty=True).start('my word')
		self.assertTrue(game.active)
		self.assertEqual(game.word, 'my word')

	def test_ignored_wordlist(self) -> None:
		"""Empty wordlist is allowable"""
		game = Hangman(allow_empty=True)
		self.assertEqual(game.word, '')
		game.start()
		self.assertEqual(game.word, '')
		self.assertFalse(game.used_words)

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
		game = Hangman(wordlist=['ECHO LOCATION']).start()
		self.assertEqual(game.guess_letter('O'), 3)
		self.assertEqual(game.visible_word, '___O _O____O_')
		self.assertEqual(game.guess_word('ECHO LOCATION'), 9)
		self.assertEqual(game.guess_count, 2)
		self.assertTrue(game.won)

	def test_guesses(self) -> None:
		"""Guessing returns correct counts and history matches"""
		game = Hangman(wordlist=['KITTY CAT']).start()
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
		game = Hangman(wordlist=['123', '456']).start()
		game.start()
		game.start()
		self.assertTrue(game.word in ['123', '456'])

	def test_game_lost(self) -> None:
		"""Game is stopped when the user is out of lives"""
		game = Hangman(lives=1, wordlist=['abc']).start()
		self.assertEqual(game.guess_letter('A'), 1)
		self.assertEqual(game.lives, 1)
		self.assertEqual(game.guess_letter('z'), 0)
		self.assertTrue(game.lost)

	@unittest.mock.patch('time.time', return_value=0.0)
	def test_restart_state(self, _: unittest.mock.MagicMock) -> None:
		"""State is reset when restarting"""
		game = Hangman(wordlist=['ABC', 'DEF']).start()
		word = game.word
		self.assertEqual(game.guess_word(word), 3)
		self.assertIsInstance(game.ended, float)
		self.assertTrue(game.won)
		self.assertTrue(game.duration < 1)

		state = GameState(0.0, 0.0, GameStatus.WON, word, [Guess(0.0, word, 3)], game.max_lives)
		self.assertTupleEqual(game.state, state)
		game.start()

		self.assertNotEqual(game.word, word)
		self.assertEqual(game.guesses, [])
		self.assertFalse(game.won)
		self.assertTrue(game.duration < 1)
		self.assertEqual(game.rounds, [state])

if __name__ == '__main__':  # pragma: no cover
	unittest.main()
