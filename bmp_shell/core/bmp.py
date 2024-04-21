# SPDX-License-Identifier: BSD-3-Clause

from pathlib   import Path
import logging as log

from .protocol import *

__all__ = (
	'BMP'
)


def _setup_termios(fd: int) -> None:
	from termios import (
		tcgetattr, tcsetattr, TCSANOW,
		CSIZE, CSTOPB, CS8, CLOCAL, CREAD, IGNBRK, IXON, IXOFF, IXANY,
		VMIN, VTIME
	)

	IFLAG  = 0
	OFLAG  = 1
	CFLAG  = 2
	LFLAG  = 3
	CC     = 6

	attrs = tcgetattr(fd)

	attrs[CFLAG] &= ~(CSIZE | CSTOPB)
	attrs[CFLAG] |= CS8 | CLOCAL | CREAD
	attrs[IFLAG] &= ~(IGNBRK | IXON | IXOFF | IXANY)
	attrs[OFLAG] = 0
	attrs[LFLAG] = 0

	attrs[CC][VMIN]  = 0
	attrs[CC][VTIME] = 5

	tcsetattr(fd, TCSANOW, attrs)

class JTAGDevice:
	ir_prescan: int
	current_ir: int

	def __init__(self, *, idcode: int):
		self.idcode = idcode
		self.ir_len = 0

	def __repr__(self):
		return str(self)

	def __str__(self):
		return f'<JTAGDevice id = {self.idcode:08X} ir = {self.ir_len}>'

def to_int32_le(bytes: bytes) -> int:
	return (
		bytes[0] |
		(bytes[1] << 8) |
		(bytes[2] << 16) |
		(bytes[3] << 24)
	)

def to_int32_be(bytes: bytes) -> int:
	return (
		(bytes[0] << 24) |
		(bytes[1] << 16) |
		(bytes[2] << 8) |
		bytes[3]
	)

class BMP:
	def __init__(self, endpoint: Path | None):
		self._endpoint = endpoint
		self.connected = False
		self._file     = None

		self._protocol_version = None
		self._fw_version = None
		self._jtag_initialized = False
		self._jtag_devices: list[JTAGDevice] = []


		self._pkt_dbg = False

	def _handshake(self) -> str:
		res = self.send_packet(HandshakePacket())

		if res is None:
			return ''

		self.connected = True
		self._fw_version = res

		return res

	def _get_protocol_version(self) -> ProtocolVersion | None:
		res = self.send_packet(ProtocolVersionPacket())

		if res is None:
			return None

		self._protocol_version = res
		return res

	def jtag_init(self) -> bool:
		self._jtag_initialized = self.send_packet(JTAGInitializePacket())
		return self._jtag_initialized

	def jtag_scan(self) -> bool:
		self._pkt_dbg = True

		if not self._jtag_initialized:
			if not self.jtag_init():
				log.error('Failed to initialize JTAG')
				return False

		self._jtag_devices.clear()

		log.info('Resetting JTAG TAPs')
		if not self.send_packet(JTAGResetPacket()):
			log.error('Failed to reset JTAG TAPs')
			return False

		log.info('Changing state to Shift-DR')
		if not self.send_packet(JTAGShiftDRPacket()):
			log.error('Failed to change state to Shift-DR')
			return False

		log.info('Scanning out ID codes')

		while True:
			idcode = self.send_packet(JTAGTDITDOSequencePacket(
				cycles = 32, final_tms_state = False, data = b'\xFF' * 4
			))

			if idcode is None:
				raise RuntimeError('Failure reading scan chain')

			idcode = to_int32_be(idcode)

			if idcode == 0xFFFFFFFF:
				break

			dev = JTAGDevice(idcode = idcode)

			self._jtag_devices.append(dev)

		log.info('Retuning to Run-Test/Idle')
		if (self.send_packet(JTAGNextPacket(tms = True, tdi = True)) is None or
			not self.send_packet(JTAGReturnIdlePacket(cycles = 1))
		):
			log.error('Failed to return JTAG State Machine to Idle')


		log.info('Changing state to Shift-IR')
		if not self.send_packet(JTAGShiftIRPacket()):
			log.error('Failed to change state to Shift-IR')
			return False

		log.info('Scanning out IRs')

		ir_len: int    = 0
		dev_index: int = 0
		prescan: int   = 0

		while ir_len <= 64:
			next_bit = self.send_packet(JTAGNextPacket(tms = False, tdi = True))

			if next_bit is None:
				raise RuntimeError('Failed reading scan chain')

			if ir_len == 0 and not next_bit:
				log.warning('Non-conformant JTAG IR!')

			ir_len += 1

			log.info(f'ir_len: {ir_len}, bit: {next_bit}')

			if next_bit and ir_len > 1:
				if ir_len == 2:
					break

				dev_ir_len = ir_len - 1

				if dev_index >= len(self._jtag_devices):
					raise RuntimeError('Device index overflow, non-compliant IR?')

				dev = self._jtag_devices[dev_index]

				dev.ir_len = dev_ir_len
				dev.ir_prescan = prescan
				dev.current_ir = 0xFFFF_FFFF_FFFF_FFFF

				prescan += dev_ir_len
				dev_index += 1
				ir_len = 1


		self._pkt_dbg = False

		return self._jtag_devices

	def jtag_trans(self) -> bool:
		pass

	def open_endpoint(self) -> bool:
		if self._endpoint is None:
			return False
		if self._file is not None:
			return True

		self._file = self._endpoint.open('r+b', buffering = 0)
		_setup_termios(self._file.fileno())

		return True


	def close_endpoint(self) -> bool:
		if self._file is None:
			self.connected = False

		self._file.close()

	def send_packet(self, pkt: BMPPacket):
		data = pkt.generate()

		if self._pkt_dbg:
			log.info(f' -> {data}')

		sent = self.raw_write(data)

		if sent != len(data):
			return None

		res = self.raw_read()
		if res is None:
			return None

		if self._pkt_dbg:
			log.info(f' <- {res}')

		return pkt.parse_result(res)

	def raw_read(self) -> bytes:
		if self._file is None:
			return b''

		data = self._file.read(1024)
		return data

	def raw_write(self, data: bytes) -> int:
		if self._file is None:
			return 0

		return self._file.write(data)

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		if self.connected:
			return f'<BMP FW: {self._fw_version} PROTO: {self._protocol_version}>'
		else:
			return '<BMP Unconnected>'
