# SPDX-License-Identifier: BSD-3-Clause

from IPython.terminal.prompts import Prompts, Token
from IPython.terminal.embed   import InteractiveShellEmbed
from traitlets.config.loader  import Config


from .magics import BMPMagics

__all__ = (
	'REPL'
)

class REPLPrompt(Prompts):
	def __init__(self, shell):
		super().__init__(shell)

	def in_prompt_tokens(self) -> tuple[tuple]:
		dev = self.shell.user_ns.get('probe', None)
		has_dev = dev is not None

		if not has_dev:
			return (
				(Token.Generic.Error, 'No Device '),
				(Token.Prompt, '> ')
			)
		else:

			return (
				(Token, 'Protocol: '),
				(Token.Number, str(dev._protocol_version)),
				(Token.Prompt, ' > ' if not dev._jtag_initialized else ' # ')
			)


class REPL(InteractiveShellEmbed):
	def __init__(self, **kwargs):
		self.repl_ns = dict()

		repl_cfg = Config()
		repl_cfg.InteractiveShellApp.hide_initial_ns = True
		repl_cfg.InteractiveShellApp.ignore_cwd = True
		repl_cfg.TerminalIPythonApp.quick = True
		repl_cfg.TerminalInteractiveShell.prompts_class = REPLPrompt
		repl_cfg.HistoryAccessor.enabled = True
		repl_cfg.HistoryAccessor.hist_file = ':memory:'


		super().__init__(config = repl_cfg, user_ns = self.repl_ns)

		self.register_magics(BMPMagics)
