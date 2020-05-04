"""Discord Bot version of Hangman"""

import os
import sys
import asyncio
import textwrap

from typing import Optional, Dict, Any

import discord
from discord.ext import commands

from hangman import Hangman, GameStatus


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

YESNO = ('✅', '❌')


class HangmanInstance:
	"""Per-user wrapper of Hangman game"""
	def __init__(self, user: discord.User, game: Hangman) -> None:
		self.user = user
		self.game = game
		self.message: Optional[discord.Message] = None

	async def message_exists(self) -> bool:
		"""Return if message exists"""
		if not self.message:
			return False


		try:
			return bool(await self.message.channel.fetch_message(self.message.id))
		except discord.DiscordException:
			return False

	def current_embed(self, feedback: Optional[str] = None) -> discord.Embed:
		"""Get current embed based on game state, with optional feedback"""
		description = f'`{" ".join(self.game.visible_word)}`\n'
		description += '```\n' + FRAMES[len(FRAMES) - 1 - self.game.lives].join(IMAGE) + '\n```\n'
		if self.game.guesses:
			description += 'Guesses: `' + ', '.join(guess.guess for guess in self.game.guesses) + '`'

		if feedback:
			description += '\n\n' + feedback

		if self.game.won or self.game.lost:
			gps = self.game.duration / (self.game.guess_count or self.game.duration)

			# pylint: disable=line-too-long
			description += '\n\n' + textwrap.dedent(f'''
			You won!

			It took you {self.game.duration:.1f} seconds - about {gps:.1f} seconds per guess, of which you took {self.game.guess_count} - to guess "{self.game.word}"!
			''') if self.game.won else textwrap.dedent(f'''
			You Lost!

			You couldn't guess "{self.game.word}" in {self.game.duration:.1f} seconds, at a rate of {gps:.1f} seconds per guess, of which you took {self.game.guess_count}...
			''')

		return discord.Embed(
			title=f'Hangman with {self.user.display_name}',
			description=description
		)

	# pylint: disable=line-too-long
	async def send_message(self, target: discord.abc.Messageable, feedback: Optional[str] = None) -> 'HangmanInstance':
		"""Send message to target - deleting current if it exists"""
		if self.message and await self.message_exists():
			await self.message.delete()

		self.message = await target.send(embed=self.current_embed(feedback))
		await self.message.add_reaction(YESNO[1])

		return self

	async def redraw(self, feedback: Optional[str] = None) -> None:
		"""Redraw message with optional feedback"""
		if not self.message:
			return

		if await self.message_exists():
			await self.message.edit(embed=self.current_embed(feedback))
		else:
			await self.send_message(self.message.channel, feedback)

	def is_valid_guess(self, guess: str) -> bool:
		"""Return if string is valid guess"""
		return len(guess) in (1, len(self.game.word))

	async def guess(self, guess: str) -> None:
		"""Make a guess"""
		revealed = getattr(self.game, 'guess_' + ('letter' if len(guess) == 1 else 'word'))(guess)
		await self.redraw(f'You revealed {revealed} letters' if revealed else None)

	def has_guessed(self, guess: str) -> bool:
		"""Return if guess has been guessed before"""
		return guess in [guess.guess for guess in self.game.guesses]


class HangmanCog(commands.Cog):  # type: ignore
	"""Cog to allow users to play Hangman"""
	def __init__(self, *args: Any, wordfile: str, **kwargs: Any):
		super().__init__(*args, **kwargs)
		self.wordfile = wordfile

		self.instances: Dict[int, HangmanInstance] = {}

	def new_game(self) -> Hangman:
		"""Create new base game"""
		return Hangman(
			lives=6,
			wordlocation=self.wordfile if os.path.exists(self.wordfile) else None,
			allow_empty=True
		)

	def computer_can_play(self) -> bool:
		"""Return if computer can currently play against users"""
		try:
			Hangman(
				lives=6,
				wordlocation=self.wordfile if os.path.exists(self.wordfile) else None,
			)
			return True
		except (ValueError, NotImplementedError):
			return False

	async def end_instance(self, instance: HangmanInstance) -> None:
		"""End an instance, making the message an orphan"""
		if instance.game.status == GameStatus.ACTIVE:
			instance.game.status = GameStatus.LOST
			await instance.redraw()

		del self.instances[instance.user.id]
		if instance.message and await instance.message_exists():
			await instance.message.clear_reactions()

	@commands.Cog.listener()
	async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None:
		"""Detect the canceling of a game"""
		instance = self.instances.get(user.id, None)
		if not instance or not instance.message:
			return

		if reaction.message.id != instance.message.id or str(reaction) != YESNO[1]:
			return

		await self.end_instance(instance)

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message) -> None:
		"""Receive - and cleanup - valid guesses"""
		if not message.clean_content:
			return

		instance = self.instances.get(message.author.id, None)
		if not instance or not instance.message:
			return

		if instance.message.channel.id != message.channel.id:
			return

		guess = message.clean_content.upper()
		if not instance.is_valid_guess(guess):
			return

		await message.delete()

		if instance.has_guessed(guess):
			await instance.redraw(f'You already guessed `{guess}`')
			return

		await instance.guess(guess)

		if not instance.game.active:
			await self.end_instance(instance)

	@commands.Cog.listener()
	async def on_ready(self) -> None:
		"""Print to console when bot is ready"""
		print('HangmanCog ready')

	@commands.command()
	async def hangman(self, ctx: commands.Context, challenging: Optional[discord.User]) -> None:
		"""Start a game of hangman, either against the computer or against another user"""
		instance = self.instances.get(ctx.author.id, None)
		if instance:
			if instance.message and await instance.message_exists():
				await ctx.send(embed=discord.Embed(
					title='Hangman',
					description=(
						'A game of Hangman is'
						f'[already in progress]({instance.message.jump_url} "click to view")'
					)
				))
			else:
				await instance.send_message(ctx, 'Game recovered')
			return

		if not challenging:
			if not self.computer_can_play():
				await ctx.send('Cannot play against computer, wordlist is empty')
				return

			instance = await HangmanInstance(ctx.author, self.new_game().start()).send_message(
				ctx,
				'Enter a guess to start'
			)
		else:
			prompt = await ctx.send(
				f'{challenging.mention}, {ctx.author} has challenged you to a game of Hangman.\n\n'
				'Do you accept?'
			)
			for emoji in YESNO:
				await prompt.add_reaction(emoji)

			try:
				reaction, _ = await ctx.bot.wait_for(
					'reaction_add',
					timeout=60,
					check=lambda reaction, user: user.id == challenging.id and str(reaction.emoji) in YESNO
				)
				accepted = str(reaction.emoji) == YESNO[0]
			except asyncio.TimeoutError:
				accepted = False

			await prompt.clear_reactions()

			if not accepted:
				await prompt.edit(
					content=f'{ctx.author.mention}, {challenging.mention} has declined your Hangman challenge'
				)
				return

			await prompt.edit(content=(
				f'{ctx.author.mention}, {challenging.mention} has accepted your Hangman challenge.'
				f'\n\nRespond via DM with the word you wish to challenge {challenging.mention} with.'
			))

			channel = ctx.author.dm_channel or await ctx.author.create_dm()
			dm_prompt = await channel.send(f'Enter the word for {challenging.mention} to guess: ')

			try:
				message = await ctx.bot.wait_for(
					'message',
					timeout=60,
					check=lambda message: (
						message.channel.id == channel.id
						and message.author.id == ctx.author.id
						and message.clean_content
					)
				)
			except asyncio.TimeoutError:
				await dm_prompt.edit(
					content=f'Did not receive word to challenge {challenging.mention} with within 60 seconds'
				)
				return

			instance = await HangmanInstance(
				ctx.author,
				self.new_game().start(message.clean_content.upper())).send_message(
					ctx,
					'Enter a guess to start'
				)
			await prompt.delete()

			assert instance.message
			await dm_prompt.edit(embed=discord.Embed(
				title='Hangman',
				description=f'[Game started]({instance.message.jump_url} "jump to game")'
			))

		self.instances[ctx.author.id] = instance


if __name__ == '__main__':
	if len(sys.argv) != 2:
		print('No Discord Token passed')
		sys.exit(1)

	BOT = commands.Bot(command_prefix='!')
	BOT.add_cog(HangmanCog(wordfile='wordlist.txt'))
	BOT.run(sys.argv[-1])
