# SPDX-License-Identifier: BSD-3-Clause



from pathlib                      import Path

from IPython.core.magic           import Magics, magics_class, line_magic, line_cell_magic
from IPython.core.magic_arguments import magic_arguments, argument, parse_argstring
from IPython.core.display         import display
from IPython.core.error           import UsageError

from rich                         import print

from .bmp                         import BMP

__all__ = (
	'BMPMagics'
)

@magics_class
class BMPMagics(Magics):
	def __init__(self, shell, *kw):
		super().__init__(shell, *kw)
		self.hex_output = True

	@line_magic
	@magic_arguments()
	@argument('enable', type = int, nargs = '?')
	def display_hex(self, line):
		''' Set or show the display hex flag '''
		args = parse_argstring(self.display_hex, line)

		if args.enable is not None:
			self.hex_output = bool(args.enable)
		else:
			print(self.hex_output)


	@line_magic
	@magic_arguments()
	@argument('verb', help = 'JTAG Action to perform')
	@argument('args', nargs = '*', help = 'Additional arguments for the verb')
	def jtag(self, line):
		'''
			Preform a JTAG action with the connected blackmagic probe.

			Valid verbs are:
			 * init - Initialize BMP JTAG
			 * scan
			 * trans [dev] [instr] [data]
		'''

		dev: BMP | None = self.shell.user_ns.get('probe')
		if dev is None:
			print('Must connect to BMP First!')
			return

		args = parse_argstring(self.jtag, line)

		verb: str = args.verb
		verb_args: list[str] = args.args

		match verb:
			case 'init':
				res = dev.jtag_init()
			case 'scan':
				res = dev.jtag_scan()
			case 'trans':
				res = dev.jtag_io()
			case _:
				print(f'Unknown JTAG verb \'{verb}\'')

		print(f'result: {res}')


	@line_magic
	def disconnect(self, _):
		dev: BMP | None = self.shell.user_ns.get('probe')
		if dev is None:
			print('Must connect to BMP First!')
			return

		del self.shell.user_ns['probe']

	@line_magic
	@magic_arguments()
	@argument('endpoint', type = Path, help = 'BMP device endpoint for communication')
	def connect(self, line):
		'''
			Connect to the blackmagic probe at the given endpoint.
		'''

		dev: BMP | None = self.shell.user_ns.get('probe')
		if dev is not None and dev.connected:
			print('Device already connected')
			return

		args = parse_argstring(self.connect, line)
		ep: Path = args.endpoint

		if not ep.exists():
			print(f'The specified endpoint \'{ep}\', does not exist!')
			return

		dev = BMP(ep)

		if not dev.open_endpoint():
			print('Unable to open endpoint')
			return

		fw_version    = dev._handshake()
		proto_version = dev._get_protocol_version()

		if fw_version is None or proto_version is None:
			print('Unable to get probe firmware or protocol versions!')
			return

		print(f'BMP Firmware Version: {fw_version}')
		print(f'Using Protocol Version {proto_version}')

		self.shell.user_ns['probe'] = dev
