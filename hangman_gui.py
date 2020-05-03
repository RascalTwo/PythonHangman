"""Tkinter GUI version of Hangman"""

import os
import textwrap

import turtle
import tkinter
import tkinter.simpledialog
import tkinter.messagebox

from typing import Tuple, Any

from hangman import Hangman, WordReader



class HangmanTurtle(turtle.RawTurtle):
	"""Turtle with hangman-drawing methods"""

	@property
	def canvas_dimensions(self) -> Tuple[int, int]:
		"""Get dimensions of canvas"""
		canvas = self.getscreen().cv
		return canvas.winfo_width(), canvas.winfo_height()

	def shorthand(self, tcmds: str) -> None:
		"""Evaluate shorthand commands"""
		for cmd in tcmds.split(';'):
			method, *args = cmd.strip().split('<')
			getattr(self, method)(*(map(float, args[0].split('|')) if args else tuple()))

	def draw_base(self) -> None:
		"""Draw hangman base"""
		width, height = self.canvas_dimensions
		base_width = width / 4
		base_height = height / 10

		# Move to bottom-left corner
		self.shorthand(
			f'penup;setpos<{-width/2 + (width / 10)}|{-height/2 + (height / 10)};setheading<0'
		)

		# Draw rectangle base
		self.shorthand('pendown;begin_fill')
		for _ in range(2):
			self.shorthand(f'forward<{base_width};left<90;forward<{base_height};left<90')
		self.shorthand(
			f'end_fill;penup;left<90;forward<{base_height};right<90;forward<{base_width / 2};left<90'
		)

		# Draw poles
		self.shorthand(
			f'pendown;forward<{height / 1.5};right<90;forward<{width / 4};right<90;forward<{height / 10}'
		)

	def draw_life(self, life: int) -> None:
		"""Draw the provided life of the hangman"""
		height = self.canvas_dimensions[1]
		origin = self.position(), self.heading()

		self.penup()
		if life == 5:
			self.shorthand(f'pendown;right<90;begin_fill;circle<{height / 15};end_fill')
		elif life == 4:
			self.shorthand(f'forward<{height / 7.5};pendown;forward<{height / 5}')
		elif life in (3, 2):
			direction = 'right' if life == 3 else 'left'
			self.shorthand(f'forward<{height / 7.5};pendown;{direction}<45;forward<{height / 7.5}')
		elif life in (1, 0):
			direction = 'right' if life == 1 else 'left'
			self.shorthand(
				f'forward<{height / 7.5 + height / 5};pendown;{direction}<45;forward<{height / 7.5}'
			)
		self.penup()

		self.setpos(origin[0])
		self.setheading(origin[1])



class GameDisplay(tkinter.Frame):  # pylint: disable=too-many-ancestors
	"""Frame containing current game state"""
	def __init__(self, *args: Any, game: Hangman, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.game = game

		self.visible_word = tkinter.Label(
			self, relief=tkinter.SUNKEN,
			bd=2, padx=5, pady=5, font='TkFixedFont'
		)
		self.visible_word.grid(row=0, column=0, sticky='ns')


		self.canvas = tkinter.Canvas(self, bd=0, highlightthickness=0)
		self.canvas.grid(row=1, column=0, sticky='news')

		self.turtle_screen = turtle.TurtleScreen(self.canvas)
		self.turtle_screen.bgcolor(self['background'])
		self.turtle = HangmanTurtle(self.turtle_screen)
		self.turtle.pensize(2)
		self.turtle.hideturtle()


		self.feedback = tkinter.Label(self)
		self.feedback.grid(row=2, column=0, sticky='news')

		self.feedback.bind(
			'<Configure>',
			lambda _: self.feedback.configure(wraplength=self.feedback.winfo_width())
		)


		self.controls = tkinter.Frame(self)
		self.controls.grid(row=3, column=0, sticky='news')
		self.update_controls()

	def update_controls(self) -> None:
		"""Update game controls depending on the current game state"""
		for widget in self.controls.winfo_children():
			widget.destroy()


		if self.game.active:
			self.visible_word.grid()
			self.visible_word.configure(text=' '.join(self.game.visible_word))

			self.turtle.fillcolor('brown4')
			self.turtle.pencolor('saddlebrown')
			self.turtle.draw_base()

			self.feedback.grid()
			self.feedback.config(text='Guesses: ', anchor='w')

			submit = tkinter.Button(self.controls, text='Guess')

			entry = tkinter.Entry(self.controls)
			entry.focus_set()
			entry.bind('<Return>', lambda _: self.guess(entry, submit))
			entry.bind('KP_Enter', lambda _: self.guess(entry, submit))

			submit.configure(command=lambda: self.guess(entry, submit))

			entry.pack(side=tkinter.LEFT, expand=True)
			submit.pack(side=tkinter.LEFT, expand=True)

		elif self.game.inactive:
			self.turtle.clear()

			self.feedback.grid_remove()
			self.feedback.config(text='', anchor='center')

			self.visible_word.grid_remove()

			player = tkinter.Button(self.controls, text='Player', command=lambda: self.start_game(True))
			player.focus_set()
			computer = tkinter.Button(self.controls, text='Computer', command=lambda: self.start_game(False))

			player.pack(side=tkinter.LEFT, expand=True)
			computer.pack(side=tkinter.LEFT, expand=True)

		else:
			new_text = (
				textwrap.dedent(f'''
				You won!

				It took you {self.game.duration:.1f} seconds - about {self.game.duration / self.game.guess_count:.1f} seconds per guess, of which you took {self.game.guess_count} - to guess "{self.game.word}"!
				''')
				if self.game.won else
				textwrap.dedent(f'''
				You Lost!

				You couldn't guess "{self.game.word}" in {self.game.duration:.1f} seconds, at a rate of {self.game.duration / self.game.guess_count:.1f} seconds per guess, of which you took {self.game.guess_count}...
				''')
			)
			self.feedback.grid()
			self.feedback.config(text=new_text, anchor='center')

			rtn = tkinter.Button(
				self.controls, text='Main Menu',
				command=lambda: self.game.stop() and self.update_controls()  # type: ignore
			)
			rtn.focus_set()
			rtn.pack()

	def start_game(self, prompt: bool = False) -> None:
		"""Attempt to start the game"""
		word = None
		if prompt:
			word = tkinter.simpledialog.askstring('Word', 'Enter word other player must guess').upper()
			if not word:
				self.grab_set()
				tkinter.messagebox.showwarning('Invalid Word', 'Word provided was invalid')
				return

		self.game.start(word)
		self.update_controls()
		if not self.game.active:
			self.grab_set()
			tkinter.messagebox.showerror('Unplayable', 'No words in wordbank')

	def guess(self, entry: tkinter.Entry, submit: tkinter.Button) -> None:
		"""Attempt to guess with user input"""
		if entry['state'] == tkinter.DISABLED:
			return

		guess = entry.get().strip().upper()
		if not guess:
			return

		entry.configure(state=tkinter.DISABLED)
		submit.configure(state=tkinter.DISABLED)

		if guess in [guess.guess for guess in self.game.guesses]:
			self.grab_set()
			tkinter.messagebox.showinfo('', 'Already guessed that')
		elif not getattr(self.game, 'guess_' + ('letter' if len(guess) == 1 else 'word'))(guess):
			self.turtle.fillcolor('#d1a3a4')
			self.turtle.pencolor('#d1a3a4')
			self.turtle.draw_life(self.game.lives)
		else:
			self.visible_word.configure(text=' '.join(self.game.visible_word))

		entry.configure(state=tkinter.NORMAL)
		submit.configure(state=tkinter.NORMAL)

		entry.delete(0, tkinter.END)

		self.feedback.config(text='Guesses: ' + ', '.join(guess.guess for guess in self.game.guesses))
		if not self.game.active:
			self.update_controls()

class WordViewer(tkinter.Toplevel):
	"""Dialog to allow viewing and deleting of words"""
	def __init__(self, *args: Any, game: Hangman, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.game = game
		self.title('Current Words')

		self.wordbox = tkinter.Listbox(self, selectmode=tkinter.MULTIPLE)
		self.wordbox.pack()
		for word in sorted(self.game.wordbank):
			self.wordbox.insert(tkinter.END, word)

		self.bind('Delete', lambda _: self.delete_selected())
		self.bind('KP_Delete', lambda _: self.delete_selected())

		tkinter.Button(self, text='Delete', command=self.delete_selected).pack(side=tkinter.LEFT)

		tkinter.Button(self, text='Close', command=self.destroy).pack(side=tkinter.RIGHT)

	def delete_selected(self) -> None:
		"""Delete the currencly selected words"""
		words = {self.wordbox.get(idx) for idx in self.wordbox.curselection()}
		if not words:
			return

		before = len(self.game.wordbank)
		self.game.wordbank.difference_update(words)

		self.grab_set()
		tkinter.messagebox.showinfo(
			'Words deleted',
			f'{before - len(self.game.wordbank)} words deleted'
		)

		self.wordbox.delete(0, tkinter.END)
		for word in sorted(self.game.wordbank):
			self.wordbox.insert(tkinter.END, word)

class HangmanGUI(tkinter.Tk):
	"""Tkinter GUI variation of Hangman"""
	def __init__(self, wordfile: str, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.wordfile = wordfile

		self.title('Hangman')
		self.game = Hangman(
			lives=6,
			wordlocation=wordfile if os.path.exists(wordfile) else None,
			allow_empty=True
		)
		GameDisplay(self, game=self.game).pack(fill=tkinter.BOTH, expand=True)
		# Generate menus
		menu = tkinter.Menu(self)

		word_menu = tkinter.Menu(tearoff=0)
		word_menu.add_command(label='View', command=self.view_words)

		add_word_menu = tkinter.Menu(tearoff=0)
		add_word_menu.add_command(label='Word', command=self.add_word)
		add_word_menu.add_command(label='Wordlist', command=self.add_word_list)
		word_menu.add_cascade(label='Add', menu=add_word_menu)

		remove_word_menu = tkinter.Menu(tearoff=0)
		remove_word_menu.add_command(label='All', command=self.remove_all)
		remove_word_menu.add_command(label='Word', command=self.remove_word)
		remove_word_menu.add_command(label='Wordlist', command=self.remove_word_list)
		word_menu.add_cascade(label='Remove', menu=remove_word_menu)

		menu.add_cascade(label='Words', menu=word_menu)

		self.config(menu=menu)

		self.bind('<Return>', self._button_keyhandlers)

	@staticmethod
	def _button_keyhandlers(event: tkinter.Event) -> None:
		"""Allow enter & return to invoke buttons"""
		# pylint: disable=line-too-long
		if isinstance(event.widget, tkinter.Button) and event.widget['state'] != tkinter.DISABLED:  # type: ignore
			event.widget.invoke()  # type: ignore

	def save_wordfile(self) -> None:
		"""Save content of wordbank to wordfile"""
		with open(self.wordfile, 'w') as wordfile:
			wordfile.write('\n'.join(self.game.wordbank))

	def view_words(self) -> None:
		"""Open wordviewer"""
		viewer = WordViewer(game=self.game)
		viewer.bind('<Destroy>', lambda _: self.save_wordfile())
		viewer.grab_set()

	def add_word(self) -> None:
		"""Prompt user for word to add"""
		self.grab_set()
		word = tkinter.simpledialog.askstring('New Word', 'Enter word to add').upper()
		if not word:
			return

		if word in self.game.wordbank:
			self.grab_set()
			tkinter.messagebox.showinfo('Cannot Add', 'Word already exists in wordbank')
			return

		self.game.wordbank.add(word)
		self.save_wordfile()

		self.grab_set()
		tkinter.messagebox.showinfo('Word Added', 'Word successfully added')

	def add_word_list(self) -> None:
		"""Prompt user for word list to add to wordbank"""
		self.grab_set()
		location = tkinter.simpledialog.askstring('Add Wordlist', 'Enter location of wordlist').strip()
		if not location:
			return

		try:
			before = len(self.game.wordbank)
			self.game.wordbank.update(WordReader.fetch_wordlist(location))
			self.save_wordfile()

			self.grab_set()
			tkinter.messagebox.showinfo(
				'Wordlist added',
				f'{len(self.game.wordbank) - before} words added from "{location}"'
			)
		except (ValueError, NotImplementedError) as ex:
			self.grab_set()
			tkinter.messagebox.showerror(
				'Failed to add Wordlist',
				f'Exception occured fetching wordlist from {location}: {ex}'
			)

	def remove_all(self) -> None:
		"""Remove all words"""
		self.game.wordbank.clear()
		self.save_wordfile()

		self.grab_set()
		tkinter.messagebox.showinfo('Words cleared', 'All words removed')

	def remove_word(self) -> None:
		"""Prompt user for one word to remove"""
		self.grab_set()
		word = tkinter.simpledialog.askstring('Remove Word', 'Enter word to remove').upper()
		if not word:
			return

		if word not in self.game.wordbank:
			self.grab_set()
			tkinter.messagebox.showinfo('Cannot Remove', 'Word does not exist in wordbank')
			return

		self.game.wordbank.remove(word)
		self.save_wordfile()
		self.grab_set()
		tkinter.messagebox.showinfo('Word Removed', 'Word successfully removed')

	def remove_word_list(self) -> None:
		"""Prompt user for wordlist to remove all included words from workbank"""
		self.grab_set()
		location = tkinter.simpledialog.askstring(
			'Remove Wordlist',
			'Enter location of wordlist'
		).strip()
		if not location:
			return

		try:
			before = len(self.game.wordbank)
			self.game.wordbank.difference_update(WordReader.fetch_wordlist(location))
			self.save_wordfile()
			self.grab_set()
			tkinter.messagebox.showinfo(
				'Wordlist removed',
				f'{before - len(self.game.wordbank)} words removed from "{location}"'
			)
		except (ValueError, NotImplementedError) as ex:
			self.grab_set()
			tkinter.messagebox.showerror(
				'Failed to remove Wordlist',
				f'Exception occured fetching wordlist from {location}: {ex}'
			)


if __name__ == '__main__':
	HangmanGUI(wordfile='wordlist.txt').mainloop()
