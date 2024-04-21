# SPDX-License-Identifier: BSD-3-Clause
import logging    as log
from argparse     import ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace

from rich         import traceback
from rich.logging import RichHandler

from .core.repl   import REPL

__all__ = (
	'main',
)

def setup_logging(args: Namespace = None) -> None:
	level = log.INFO
	if args is not None and args.verbose:
		level = log.DEBUG

	log.basicConfig(
		force    = True,
		format   = '%(message)s',
		datefmt  = '[%X]',
		level    = level,
		handlers = [
			RichHandler(rich_tracebacks = True, show_path = False)
		]
	)


def main() -> int:

	traceback.install()
	setup_logging()

	parser = ArgumentParser(
		formatter_class = ArgumentDefaultsHelpFormatter,
		description     = 'blackmagic probe JTAG shell',
		prog            = 'bmp-shell'
	)



	repl_shell = REPL()

	repl_shell.mainloop()
