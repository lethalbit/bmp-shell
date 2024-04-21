
# SPDX-License-Identifier: BSD-3-Clause

from abc     import abstractmethod
from enum    import Enum, unique, auto

__all__ = (
	'ProtocolVersion',

	'BMPPacket',
	'HandshakePacket', 'ProtocolVersionPacket',
	'JTAGInitializePacket', 'JTAGResetPacket', 'JTAGTMSSequencePacket', 'JTAGTDITDOSequencePacket',
	'JTAGTDISequencePacket', 'JTAGNextPacket',

	'JTAGShiftDRPacket', 'JTAGShiftIRPacket', 'JTAGReturnIdlePacket'

)

@unique
class ProtocolVersion(Enum):
	V0      = auto()
	V0_PLUS = auto()
	V1      = auto()
	V2      = auto()
	V3      = auto()

	def __repr__(self) -> str:
		return str(self)

	def __str__(self) -> str:
		match self:
			case ProtocolVersion.V0:
				return 'v0'
			case ProtocolVersion.V0_PLUS:
				return 'v0+'
			case ProtocolVersion.V1:
				return 'v1'
			case ProtocolVersion.V2:
				return 'v2'
			case ProtocolVersion.V3:
				return 'v3'
			case ver:
				raise RuntimeError(f'Unknown BMP Protocol version {ver}')

class BMPPacket:
	RESP_OK            = 'K'
	RESP_PARAM_ERROR   = 'P'
	RESP_ERR           = 'E'
	RESP_NOT_SUPPORTED = 'N'

	def is_okay(self, result_code: str) -> bool:
		return result_code == self.RESP_OK

	def validate_resp(self, data: bytes) -> bool:
		return data[0] == ord('&') and data[-1] == ord('#')

	def unwrap(self, data: bytes) -> str | None:
		if not self.validate_resp(data):
			print('Malformed BMP Packet')
			return None

		return data.decode('utf-8')[1:-1]

	@property
	@abstractmethod
	def packet_template(self) -> str:
		...

	def generate(self) -> bytes:
		return self.packet.encode('utf-8')

	def __init__(self):
		self.packet = self.packet_template

	def parse_result(self, data: bytes):
		return data

	def __repr__(self) -> bytes:
		return self.generate()

	def __str__(self) -> str:
		return f'<{type(self).__name__} \'{self.packet_template}\'>'

class HandshakePacket(BMPPacket):
	packet_template = '+#!GA#'

	def parse_result(self, data: bytes) -> str | None:
		data = self.unwrap(data)
		if data is None:
			return None

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return None

		# Return the firmware version
		return data[1:]

class ProtocolVersionPacket(BMPPacket):
	packet_template = '!HC#'

	def parse_result(self, data: bytes) -> ProtocolVersion | None:
		data = self.unwrap(data)
		if data is None:
			return None

		if data[0] == self.RESP_NOT_SUPPORTED:
			return ProtocolVersion.V0

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return None

		match data[1:]:
			case '0':
				return ProtocolVersion.V0_PLUS
			case '1':
				return ProtocolVersion.V1
			case '2':
				return ProtocolVersion.V2
			case '3':
				return ProtocolVersion.V3
			case ver:
				raise RuntimeError(f'Unknown BMP Protocol version {ver}')


class JTAGInitializePacket(BMPPacket):
	packet_template = '!JS#'

	def parse_result(self, data: bytes) -> bool:
		data = self.unwrap(data)
		if data is None:
			return False

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return False

		return data[1] == '0'

class JTAGResetPacket(BMPPacket):
	packet_template = '!JR#'

	def parse_result(self, data: bytes) -> bool:
		data = self.unwrap(data)
		if data is None:
			return False

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return False

		return data[1] == '0'


class JTAGTMSSequencePacket(BMPPacket):
	packet_template = '!JT{:02X}{:02X}#'

	def __init__(self, *, cycles: int, tms_states: int):
		self.cycles     = cycles
		self.tms_states = tms_states

		self.packet     = self.packet_template.format(cycles, tms_states)

	def parse_result(self, data: bytes) -> bool:
		data = self.unwrap(data)
		if data is None:
			return False

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return False

		return data[1] == '0'


def JTAGShiftDRPacket() -> JTAGTMSSequencePacket:
	return JTAGTMSSequencePacket(cycles = 3, tms_states = 0x01)
def JTAGShiftIRPacket() -> JTAGTMSSequencePacket:
	return JTAGTMSSequencePacket(cycles = 4, tms_states = 0x03)
def JTAGReturnIdlePacket(*, cycles: int) -> JTAGTMSSequencePacket:
	return JTAGTMSSequencePacket(cycles = cycles + 1, tms_states = 0x01)


class JTAGTDITDOSequencePacket(BMPPacket):
	packet_template = '!J{}{:02X}{}#'

	def __init__(self, *, cycles: int, final_tms_state: bool, data: bytes | None):

		if data is None:
			data = b'\0' * (cycles + 3 // 4)

		if (cycles + 3 // 4) == len(data):
			raise ValueError(f'Improper amount of data for cycle count of {cycles}')

		self.cycles          = cycles
		self.data            = data
		self.final_tms_state = final_tms_state

		self.packet          = self.packet_template.format(
			'D' if final_tms_state else 'd', cycles, data.hex()
		)

	def parse_result(self, data: bytes) -> bytes | None:
		data = self.unwrap(data)
		if data is None:
			return None

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return None

		return bytes.fromhex(data[1:])


class JTAGTDISequencePacket(JTAGTDITDOSequencePacket):

	def parse_result(self, data: bytes) -> bool:
		data = self.unwrap(data)
		if data is None:
			return False

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return False

		return True


class JTAGNextPacket(BMPPacket):
	packet_template = '!JN{:X}{:X}#'

	def __init__(self, *, tms: bool, tdi: bool):
		self.tms = tms
		self.tdi = tdi

		self.packet = self.packet_template.format(int(tms), int(tdi))

	def parse_result(self, data: bytes) -> bool | None:
		data = self.unwrap(data)
		if data is None:
			return NotImplemented

		if not self.is_okay(data[0]):
			print('Got a non-okay response')
			return None

		return data[1] == '1'
