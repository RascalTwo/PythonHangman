# type: ignore
# pylint: disable=line-too-long
"""Task runner"""

import glob
import sys
import os

from unittest.mock import patch
from inspect import getfullargspec, ArgSpec

import invoke
from invoke import Context, task


def fix_annotations():
	"""
		Pyinvoke doesnt accept annotations by default, this fix that
		Based on: https://github.com/pyinvoke/invoke/pull/606

		Copied from: https://github.com/pyinvoke/invoke/issues/357#issuecomment-583851322
	"""
	def patched_inspect_getargspec(func):
		spec = getfullargspec(func)
		return ArgSpec(*spec[0:4])

	org_task_argspec = invoke.tasks.Task.argspec

	def patched_task_argspec(*args, **kwargs):
		with patch(target="inspect.getargspec", new=patched_inspect_getargspec):
			return org_task_argspec(*args, **kwargs)

	invoke.tasks.Task.argspec = patched_task_argspec
fix_annotations()


PY_FILES = ' '.join(glob.glob('**/*.py', recursive=True))
TEST_FILES = ' '.join(glob.glob('**/*_test.py', recursive=True))


ARTIFACTS = ['pylint.json', 'pylint.html', 'coverage.xml', 'coverage.html']

@task
def cleanup(_: Context) -> None:
	"""Cleanup task artifacts"""
	deleting = [filename for filename in ARTIFACTS if os.path.exists(filename)]
	if not deleting:
		return

	print('Deleting: ' + ', '.join(deleting))
	for filename in deleting:
		os.remove(filename)


@task
def mypy(ctx: Context) -> None:
	"""Run mypy"""
	ctx.run('mypy --strict .', echo=True, pty=True)

@task()
def pylint(ctx: Context, html=False) -> None:
	"""Run pylint"""
	if html:
		try:
			result = ctx.run('pylint --load-plugins=pylint_json2html --output-format=jsonextended {} > pylint.json'.format(PY_FILES), echo=True)
		except invoke.UnexpectedExit as ex:
			try:
				print('Failed, getting text output...')
				ctx.run('pylint ' + PY_FILES, echo=True)
			except:  # pylint: disable=bare-except
				pass
			result = ex.result
		ctx.run('pylint-json2html pylint.json -f jsonextended -o "pylint.html"', echo=True)
		print('HTML absolute path: ' + os.path.abspath('pylint.html'))
		ctx.run(f'(exit {result.exited})')
	else:
		ctx.run('pylint ' + PY_FILES, echo=True)

@task(mypy, pylint)
def lint(_: Context):
	"""Run mypy and pylint"""


@task()
def test(ctx: Context, coverage=False, html=False) -> None:
	"""Run tests"""
	if html and not coverage:
		print('coverage required for HTML, enabling')
		coverage = True

	if not coverage:
		ctx.run(sys.executable + ' -m unittest ' + TEST_FILES, echo=True)
		return

	try:
		result = ctx.run('coverage run -m unittest ' + TEST_FILES, echo=True, warn=True)
	except invoke.UnexpectedExit as ex:
		result = ex.result

	if not html:
		return

	ctx.run('coverage xml', echo=True)
	ctx.run('pycobertura show --format html --output coverage.html coverage.xml', echo=True)
	print('HTML absolute path: ' + os.path.abspath('coverage.html'))
	ctx.run(f'(exit {result.exited})')

@task
def cli(ctx: Context) -> None:
	"""Start CLI game"""
	ctx.run('python hangman_cli.py')
