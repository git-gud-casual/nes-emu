import logging

from typing import Dict, Optional
from .cpu_instruction import *
from memory import BaseMemory
from utils import FlagsRegister


class PSRegister(FlagsRegister):
    _MASK = 0x20

    def __init__(self):
        self._value = self._MASK

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_val: int):
        self._value = new_val | self._MASK

    # Carry Flag
    @property
    def c(self) -> bool:
        return self._get_bit(0)

    @c.setter
    def c(self, value: bool):
        self._set_bit(0, value)

    # Zero Flag
    @property
    def z(self) -> bool:
        return self._get_bit(1)

    @z.setter
    def z(self, value: bool):
        self._set_bit(1, value)

    # Interrupt Disable Flag
    @property
    def i(self) -> bool:
        return self._get_bit(2)

    @i.setter
    def i(self, value: bool):
        self._set_bit(2, value)

    # Break Flag
    @property
    def b(self) -> bool:
        return self._get_bit(4)

    @b.setter
    def b(self, value: bool):
        self._set_bit(4, value)

    # Overflow Flag
    @property
    def v(self) -> bool:
        return self._get_bit(6)

    @v.setter
    def v(self, value: bool):
        self._set_bit(6, value)

    # Negative Flag
    @property
    def n(self) -> bool:
        return self._get_bit(7)

    @n.setter
    def n(self, value: bool):
        self._set_bit(7, value)

    # Decimal mode flag
    @property
    def d(self) -> bool:
        return self._get_bit(3)

    @d.setter
    def d(self, value: bool):
        self._set_bit(3, value)


class Cpu:
    _pc: int  # Program Counter
    _ps: PSRegister  # Processor State
    _sp: int  # Stack Pointer
    _a: int
    _x: int
    _y: int
    _instructions: Dict[int, CpuInstruction]
    _memory: BaseMemory
    _cycles_count: int

    _MASK8 = 0xFF
    _MASK16 = 0xFFFF
    _MASK_NEG = 1 << 7
    _STACK_POINTER_INIT_VAL = 0xFD
    _STACK_PAGE_ADDR = 0x100
    _RESET_VECTOR_ADDR = 0xFFFC
    _BRQ_VECTOR_ADDR = 0xFFFE

    def __init__(self, memory: BaseMemory):
        self._logger = logging.getLogger("cpu")
        self._memory = memory
        self._instructions = self._get_function_dict()
        self.reset()

    @classmethod
    def _get_function_dict(cls) -> Dict[int, CpuInstruction]:
        instructions = {}
        for _, val in cls.__dict__.items():
            if not isinstance(val, CpuInstructionWrapper):
                continue

            for instr in val.descriptions:
                instructions[instr.opcode] = instr
        return instructions

    def reset(self):
        self._pc = self._read_word(self._RESET_VECTOR_ADDR)
        self._ps = PSRegister()
        self._a = 0
        self._x = 0
        self._y = 0
        self._sp = self._STACK_POINTER_INIT_VAL
        self._cycles_count = 0

    def _log_instruction(self, instr: CpuInstruction):
        log_msg = " {instr_name}".format(instr_name=instr.function.__name__.lstrip("_").upper())
        if instr.addr_mode == AddrMode.IMMEDIATE:
            value = self._memory.read(self._pc)
            log_msg += " #" + format(value, "02X")
        elif instr.addr_mode == AddrMode.ZERO_PAGE:
            addr = self._memory.read(self._pc)
            log_msg += " $" + format(addr, "02X")
        elif instr.addr_mode == AddrMode.ZERO_PAGE_X:
            value = self._memory.read(self._pc)
            log_msg += " $" + format(value, "02X") + ",X"
        elif instr.addr_mode == AddrMode.ZERO_PAGE_Y:
            value = self._memory.read(self._pc)
            log_msg += " $" + format(value, "02X") + ",Y"
        elif instr.addr_mode == AddrMode.RELATIVE:
            value = self._memory.read(self._pc)
            log_msg += " $" + format(self._to_sign(value) + self._pc + 1, "04X")
        elif instr.addr_mode == AddrMode.ABSOLUTE:
            addr = self._read_word(self._pc)
            log_msg += " $" + format(addr, "04X")
        elif instr.addr_mode == AddrMode.ABSOLUTE_X:
            addr = self._read_word(self._pc)
            log_msg += " $" + format(addr, "04X") + ",X"
        elif instr.addr_mode == AddrMode.ABSOLUTE_Y:
            addr = self._read_word(self._pc)
            log_msg += " $" + format(addr, "04X") + ",Y"
        elif instr.addr_mode == AddrMode.INDIRECT:
            val = self._read_word(self._pc)
            log_msg += " ($" + format(val, "04X") + ")"
        elif instr.addr_mode == AddrMode.INDIRECT_X:
            val = self._memory.read(self._pc)
            log_msg += " ($" + format(val, "02X") + ",X)"
        elif instr.addr_mode == AddrMode.INDIRECT_Y:
            val = self._memory.read(self._pc)
            log_msg += " ($" + format(val, "02X") + "),Y"
        self._logger.info(log_msg)

    def process(self):
        opcode = self._memory.read(self._pc)
        cpu_instr = self._instructions[opcode]
        self._pc += 1

        self._log_instruction(cpu_instr)
        if cpu_instr.addr_mode in (AddrMode.IMPLIED, AddrMode.ACCUMULATOR):
            cpu_instr.function(self)
        elif cpu_instr.addr_mode == AddrMode.IMMEDIATE:
            value = self._memory.read(self._pc)
            self._pc += 1
            cpu_instr.function(self, value=value)
        elif cpu_instr.addr_mode == AddrMode.ZERO_PAGE:
            addr = self._memory.read(self._pc)
            self._pc += 1
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.ZERO_PAGE_X:
            val = self._memory.read(self._pc)
            addr = (val + self._x) & self._MASK8
            self._pc += 1
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.ZERO_PAGE_Y:
            val = self._memory.read(self._pc)
            addr = (val + self._y) & self._MASK8
            self._pc += 1
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.RELATIVE:
            value = self._memory.read(self._pc)
            self._pc += 1
            cpu_instr.function(self, value=value)
        elif cpu_instr.addr_mode == AddrMode.ABSOLUTE:
            addr = self._read_word(self._pc)
            self._pc += 2
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.ABSOLUTE_X:
            addr = (self._read_word(self._pc) + self._x) & self._MASK16
            self._pc += 2
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.ABSOLUTE_Y:
            addr = (self._read_word(self._pc) + self._y) & self._MASK16
            self._pc += 2
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.INDIRECT:
            addr = self._read_word(self._read_word(self._pc), wrap_page=True)
            self._pc += 2
            cpu_instr.function(self, addr=addr)
        elif cpu_instr.addr_mode == AddrMode.INDIRECT_X:
            target_addr = (self._memory.read(self._pc) + self._x) & self._MASK8
            addr = self._read_word(target_addr, wrap_page=True)
            self._pc += 1
            cpu_instr.function(self, addr=addr)
        else:
            target_addr = self._memory.read(self._pc)
            addr = (self._read_word(target_addr, wrap_page=True) + self._y) & self._MASK16
            self._pc += 1
            cpu_instr.function(self, addr=addr)
        self._cycles_count += cpu_instr.cycles

    def print_info(self):
        msg = "Registers-----BIN----------------HEX----\n" + \
              "Accumulator---%s-----------0x%s---\n" % (format(self._a, "08b"), format(self._a, "02X")) + \
              "IndexX--------%s-----------0x%s---\n" % (format(self._x, "08b"), format(self._x, "02X")) + \
              "IndexY--------%s-----------0x%s---\n" % (format(self._y, "08b"), format(self._y, "02X")) + \
              "SP------------%s-----------0x%s---\n" % (format(self._sp, "08b"), format(self._sp, "02X")) + \
              "PC------------%s---0x%s-\n" % (format(self._pc, "016b"), format(self._pc, "04X")) + \
              "State---------NV-BDIZC------------------\n" + \
              "--------------%s-----------0x%s---\n" % (format(self._ps.value, "08b"), format(self._ps.value, "02X"))

        print(msg)

    @instruction(
        CpuInstructionDesc(0x69, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x65, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x75, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x6D, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x7D, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x79, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0x61, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0x71, AddrMode.INDIRECT_Y, 5)
    )
    def _adc(self, value: Optional[int] = None, addr: Optional[int] = None):
        """
        Add with carry
        """

        value = value if value is not None else self._memory.read(addr)
        res = self._a + value + self._ps.c
        self._ps.c = res > 255
        self._ps.v = (self._a & self._MASK_NEG == value & self._MASK_NEG) and \
                     (self._a & self._MASK_NEG != res & self._MASK_NEG)
        self._ps.n = res & self._MASK_NEG
        self._a = res & self._MASK8
        self._ps.z = self._a == 0

    @instruction(
        CpuInstructionDesc(0x29, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x25, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x35, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x2D, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x3D, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x39, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0x21, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0x31, AddrMode.INDIRECT_Y, 5)
    )
    def _and(self, value: Optional[int] = None, addr: Optional[int] = None):
        """
        Bit by bit AND
        """

        value = value if value is not None else self._memory.read(addr)
        self._a &= value
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x0A, AddrMode.ACCUMULATOR, 2),
        CpuInstructionDesc(0x06, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x16, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x0E, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x1E, AddrMode.ABSOLUTE_X, 7),
    )
    def _asl(self, addr: Optional[int] = None):
        """
        Arithmetic Shift Left
        """
        val = self._a if addr is None else self._memory.read(addr)
        val <<= 1
        self._ps.c = val > 255
        val &= self._MASK8
        self._ps.z = val == 0
        self._ps.n = val & self._MASK_NEG
        if addr:
            self._memory.write(addr, val)
        else:
            self._a = val

    @instruction(
        CpuInstructionDesc(0x90, AddrMode.RELATIVE, 2)
    )
    def _bcc(self, value: int):
        if self._ps.c:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0xB0, AddrMode.RELATIVE, 2)
    )
    def _bcs(self, value: int):
        if not self._ps.c:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0xF0, AddrMode.RELATIVE, 2)
    )
    def _beq(self, value: int):
        if not self._ps.z:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0x24, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x2C, AddrMode.ABSOLUTE, 4)
    )
    def _bit(self, addr: int):
        val = self._memory.read(addr)
        self._ps.z = self._a & val == 0
        self._ps.v = val & 1 << 6
        self._ps.n = val & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x30, AddrMode.RELATIVE, 2)
    )
    def _bmi(self, value: int):
        if not self._ps.n:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0xD0, AddrMode.RELATIVE, 2)
    )
    def _bne(self, value: int):
        if self._ps.z:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0x10, AddrMode.RELATIVE, 2)
    )
    def _bpl(self, value: int):
        if self._ps.n:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0x00, AddrMode.IMPLIED, 7)
    )
    def _brk(self):
        self._ps.b = True
        self._push_word_to_stack(self._pc)
        self._push_to_stack(self._ps.value)
        self._pc = self._BRQ_VECTOR_ADDR

    @instruction(
        CpuInstructionDesc(0x50, AddrMode.RELATIVE, 2)
    )
    def _bvc(self, value: int):
        if self._ps.v:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0x70, AddrMode.RELATIVE, 2)
    )
    def _bvs(self, value: int):
        if not self._ps.v:
            return
        offset = self._to_sign(value)
        self._cycles_count += 1 if self._pc & 0xFF00 == (self._pc + offset) & 0xFF00 else 2
        self._pc += offset

    @instruction(
        CpuInstructionDesc(0x18, AddrMode.IMPLIED, 2)
    )
    def _clc(self):
        self._ps.c = 0

    @instruction(
        CpuInstructionDesc(0x58, AddrMode.IMPLIED, 2)
    )
    def _cli(self):
        self._ps.i = 0

    @instruction(
        CpuInstructionDesc(0xB8, AddrMode.IMPLIED, 2)
    )
    def _clv(self):
        self._ps.v = 0

    @instruction(
        CpuInstructionDesc(0xC9, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xC5, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xD5, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xCD, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xDD, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0xD9, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0xC1, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0xD1, AddrMode.INDIRECT_Y, 5)
    )
    def _cmp(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        self._ps.c = self._a >= value
        self._ps.z = self._a == value
        self._ps.n = (self._a - value) & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xE0, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xE4, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xEC, AddrMode.ABSOLUTE, 4),
    )
    def _cpx(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        self._ps.c = self._x >= value
        self._ps.z = self._x == value
        self._ps.n = (self._x - value) & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xC0, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xC4, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xCC, AddrMode.ABSOLUTE, 4),
    )
    def _cpy(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        self._ps.c = self._y >= value
        self._ps.z = self._y == value
        self._ps.n = (self._y - value) & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xC6, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0xD6, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0xCE, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0xDE, AddrMode.ABSOLUTE_X, 7)
    )
    def _dec(self, addr: int):
        value = (self._memory.read(addr) - 1) & self._MASK8
        self._ps.z = value == 0
        self._ps.n = value & self._MASK_NEG
        self._memory.write(addr, value)

    @instruction(
        CpuInstructionDesc(0xCA, AddrMode.IMPLIED, 2)
    )
    def _dex(self):
        self._x = (self._x - 1) & self._MASK8
        self._ps.z = self._x == 0
        self._ps.n = self._x & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x88, AddrMode.IMPLIED, 2)
    )
    def _dey(self):
        self._y = (self._y - 1) & self._MASK8
        self._ps.z = self._y == 0
        self._ps.n = self._y & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x49, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x45, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x55, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x4D, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x5D, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x59, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0x41, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0x51, AddrMode.INDIRECT_Y, 5)
    )
    def _eor(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        self._a = self._a ^ value & self._MASK8
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xE6, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0xF6, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0xEE, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0xFE, AddrMode.ABSOLUTE_X, 7)
    )
    def _inc(self, addr: int):
        value = (self._memory.read(addr) + 1) & self._MASK8
        self._ps.z = value == 0
        self._ps.n = value & self._MASK_NEG
        self._memory.write(addr, value)

    @instruction(
        CpuInstructionDesc(0xE8, AddrMode.IMPLIED, 2)
    )
    def _inx(self):
        self._x = (self._x + 1) & self._MASK8
        self._ps.z = self._x == 0
        self._ps.n = self._x & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xC8, AddrMode.IMPLIED, 2)
    )
    def _iny(self):
        self._y = (self._y + 1) & self._MASK8
        self._ps.z = self._y == 0
        self._ps.n = self._y & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x4C, AddrMode.ABSOLUTE, 3),
        CpuInstructionDesc(0x6C, AddrMode.INDIRECT, 5)
    )
    def _jmp(self, addr: int):
        self._pc = addr

    @instruction(
        CpuInstructionDesc(0x20, AddrMode.ABSOLUTE, 6)
    )
    def _jsr(self, addr: int):
        self._push_word_to_stack(self._pc - 1)
        self._pc = addr

    @instruction(
        CpuInstructionDesc(0xA9, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xA5, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xB5, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xAD, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xBD, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0xB9, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0xA1, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0xB1, AddrMode.INDIRECT_Y, 5)
    )
    def _lda(self, value: Optional[int] = None, addr: Optional[int] = None):
        self._a = value if value is not None else self._memory.read(addr)
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xA2, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xA6, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xB6, AddrMode.ZERO_PAGE_Y, 4),
        CpuInstructionDesc(0xAE, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xBE, AddrMode.ABSOLUTE_Y, 4),
    )
    def _ldx(self, value: Optional[int] = None, addr: Optional[int] = None):
        self._x = value if value is not None else self._memory.read(addr)
        self._ps.z = self._x == 0
        self._ps.n = self._x & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xA0, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xA4, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xB4, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xAC, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xBC, AddrMode.ABSOLUTE_X, 4),
    )
    def _ldy(self, value: Optional[int] = None, addr: Optional[int] = None):
        self._y = value if value is not None else self._memory.read(addr)
        self._ps.z = self._y == 0
        self._ps.n = self._y & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x4A, AddrMode.ACCUMULATOR, 2),
        CpuInstructionDesc(0x46, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x56, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x4E, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x5E, AddrMode.ABSOLUTE_X, 7),
    )
    def _asr(self, addr: Optional[int] = None):
        val = self._a if addr is None else self._memory.read(addr)
        self._ps.c = val & 1
        val >>= 1
        val &= self._MASK8
        self._ps.z = val == 0
        self._ps.n = 0
        if addr:
            self._memory.write(addr, val)
        else:
            self._a = val

    @instruction(
        CpuInstructionDesc(0xEA, AddrMode.IMPLIED, 2),
    )
    def _nop(self):
        pass

    @instruction(
        CpuInstructionDesc(0x09, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x05, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x15, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x0D, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x1D, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x19, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0x01, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0x11, AddrMode.INDIRECT_Y, 5)
    )
    def _ora(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        self._a = self._a | value
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x48, AddrMode.IMPLIED, 3)
    )
    def _pha(self):
        self._push_to_stack(self._a)

    @instruction(
        CpuInstructionDesc(0x08, AddrMode.IMPLIED, 3)
    )
    def _php(self):
        self._push_to_stack(self._ps.value)

    @instruction(
        CpuInstructionDesc(0x68, AddrMode.IMPLIED, 4)
    )
    def _pla(self):
        self._a = self._pull_from_stack()
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x28, AddrMode.IMPLIED, 4)
    )
    def _plp(self):
        self._ps.value = self._pull_from_stack() & ~(1 << 4) | (self._ps.b << 4)

    @instruction(
        CpuInstructionDesc(0x2A, AddrMode.ACCUMULATOR, 2),
        CpuInstructionDesc(0x26, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x36, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x2E, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x3E, AddrMode.ABSOLUTE_X, 7),
    )
    def _rol(self, addr: Optional[int] = None):
        val = self._a if addr is None else self._memory.read(addr)
        temp = self._ps.c
        self._ps.c = val & self._MASK_NEG
        val = (val << 1 | temp) & self._MASK8
        self._ps.z = val == 0
        self._ps.n = val & self._MASK_NEG
        if addr:
            self._memory.write(addr, val)
        else:
            self._a = val

    @instruction(
        CpuInstructionDesc(0x6A, AddrMode.ACCUMULATOR, 2),
        CpuInstructionDesc(0x66, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x76, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x6E, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x7E, AddrMode.ABSOLUTE_X, 7),
    )
    def _ror(self, addr: Optional[int] = None):
        val = self._a if addr is None else self._memory.read(addr)
        temp = self._ps.c
        self._ps.c = val & 1
        val = val >> 1 | temp << 7
        self._ps.z = val == 0
        self._ps.n = temp
        if addr:
            self._memory.write(addr, val)
        else:
            self._a = val

    @instruction(
        CpuInstructionDesc(0x40, AddrMode.IMPLIED, 6)
    )
    def _rti(self):
        self._ps.value = self._pull_from_stack()
        self._pc = self._pull_word_from_stack()

    @instruction(
        CpuInstructionDesc(0x60, AddrMode.IMPLIED, 6)
    )
    def _rts(self):
        self._pc = self._pull_word_from_stack() + 1

    @instruction(
        CpuInstructionDesc(0xE9, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xE5, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xF5, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xED, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xFD, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0xF9, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0xE1, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0xF1, AddrMode.INDIRECT_Y, 5)
    )
    def _sbc(self, value: Optional[int] = None, addr: Optional[int] = None):
        value = value if value is not None else self._memory.read(addr)
        res = self._a - value - (1 - self._ps.c)
        self._ps.c = res >= 0
        self._ps.v = (self._a & self._MASK_NEG != value & self._MASK_NEG) and \
                     (res & self._MASK_NEG == value & self._MASK_NEG)
        self._ps.z = res == 0
        self._ps.n = res & self._MASK_NEG
        self._a = res & self._MASK8

    @instruction(
        CpuInstructionDesc(0x38, AddrMode.IMPLIED, 2)
    )
    def _sec(self):
        self._ps.c = True

    @instruction(
        CpuInstructionDesc(0x78, AddrMode.IMPLIED, 2)
    )
    def _sei(self):
        self._ps.i = True

    @instruction(
        CpuInstructionDesc(0x85, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x95, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x8D, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x9D, AddrMode.ABSOLUTE_X, 5),
        CpuInstructionDesc(0x99, AddrMode.ABSOLUTE_Y, 5),
        CpuInstructionDesc(0x81, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0x91, AddrMode.INDIRECT_Y, 6)
    )
    def _sta(self, addr: int):
        self._memory.write(addr, self._a)

    @instruction(
        CpuInstructionDesc(0x86, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x96, AddrMode.ZERO_PAGE_Y, 4),
        CpuInstructionDesc(0x8E, AddrMode.ABSOLUTE, 4),
    )
    def _stx(self, addr: int):
        self._memory.write(addr, self._x)

    @instruction(
        CpuInstructionDesc(0x84, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x94, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x8C, AddrMode.ABSOLUTE, 4),
    )
    def _sty(self, addr: int):
        self._memory.write(addr, self._y)

    @instruction(
        CpuInstructionDesc(0xAA, AddrMode.IMPLIED, 2)
    )
    def _tax(self):
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG
        self._x = self._a

    @instruction(
        CpuInstructionDesc(0xA8, AddrMode.IMPLIED, 2)
    )
    def _tay(self):
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG
        self._y = self._a

    @instruction(
        CpuInstructionDesc(0xBA, AddrMode.IMPLIED, 2)
    )
    def _tsx(self):
        self._ps.z = self._sp == 0
        self._ps.n = self._sp & self._MASK_NEG
        self._x = self._sp

    @instruction(
        CpuInstructionDesc(0x8A, AddrMode.IMPLIED, 2)
    )
    def _txa(self):
        self._a = self._x
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x9A, AddrMode.IMPLIED, 2)
    )
    def _txs(self):
        self._sp = self._x

    @instruction(
        CpuInstructionDesc(0x98, AddrMode.IMPLIED, 2)
    )
    def _tya(self):
        self._a = self._y
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0xF8, AddrMode.IMPLIED, 2)
    )
    def _sed(self):
        self._ps.d = True

    @instruction(
        CpuInstructionDesc(0xD8, AddrMode.IMPLIED, 2)
    )
    def _cld(self):
        self._ps.d = False

    def _pull_from_stack(self) -> int:
        self._sp += 1
        return self._memory.read(self._STACK_PAGE_ADDR | self._sp)

    def _pull_word_from_stack(self) -> int:
        value = self._pull_from_stack() | \
                self._pull_from_stack() << 8
        return value

    def _push_to_stack(self, value: int):
        self._memory.write(self._STACK_PAGE_ADDR | self._sp, value)
        self._sp -= 1

    def _push_word_to_stack(self, value: int):
        self._push_to_stack(value >> 8)
        self._push_to_stack(value & self._MASK8)

    def _read_word(self, addr: int, wrap_page: bool = False) -> int:
        if wrap_page and addr & 0xFF == 0xFF:
            return self._memory.read(addr & 0xFF00) << 8 | self._memory.read(addr)
        else:
            return self._memory.read(addr + 1) << 8 | self._memory.read(addr)

    @classmethod
    def _to_sign(cls, num: int) -> int:
        neg = num & cls._MASK_NEG
        return -(~num & cls._MASK8) - 1 if neg else num

    """
    Illegal Opcodes
    """

    @instruction(
        CpuInstructionDesc(0xA7, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0xB7, AddrMode.ZERO_PAGE_Y, 4),
        CpuInstructionDesc(0xAF, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0xBF, AddrMode.ABSOLUTE_Y, 4),
        CpuInstructionDesc(0xA3, AddrMode.INDIRECT_X, 6),
        CpuInstructionDesc(0xB3, AddrMode.INDIRECT_Y, 5)
    )
    def _lax(self, addr: int):
        self._a = self._x = self._memory.read(addr)
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG

    @instruction(
        CpuInstructionDesc(0x87, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x97, AddrMode.ZERO_PAGE_Y, 4),
        CpuInstructionDesc(0x8F, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x83, AddrMode.INDIRECT_X, 6)
    )
    def _sax(self, addr: int):
        self._memory.write(addr, self._a & self._x)

    @instruction(
        CpuInstructionDesc(0xEB, AddrMode.IMMEDIATE, 2)
    )
    def _sbc_illegal(self, value):
        res = self._a - value - (1 - self._ps.c)
        self._ps.c = res >= 0
        self._ps.v = (self._a & self._MASK_NEG != value & self._MASK_NEG) and \
                     (res & self._MASK_NEG == value & self._MASK_NEG)
        self._ps.z = res == 0
        self._ps.n = res & self._MASK_NEG
        self._a = res & self._MASK8

    @instruction(
        CpuInstructionDesc(0xC7, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0xD7, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0xCF, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0xDF, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0xDB, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0xC3, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0xD3, AddrMode.INDIRECT_Y, 8)
    )
    def _dcp(self, addr: int):
        value = (self._memory.read(addr) - 1) & self._MASK8
        self._ps.c = self._a >= value
        self._ps.z = self._a == value
        self._ps.n = (self._a - value) & self._MASK_NEG
        self._memory.write(addr, value)

    @instruction(
        CpuInstructionDesc(0xE7, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0xF7, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0xEF, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0xFF, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0xFB, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0xE3, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0xF3, AddrMode.INDIRECT_Y, 8)
    )
    def _isb(self, addr: int):
        value = (self._memory.read(addr) + 1) & self._MASK8
        self._memory.write(addr, value)
        res = self._a - value - (1 - self._ps.c)
        self._ps.c = res >= 0
        self._ps.v = (self._a & self._MASK_NEG != value & self._MASK_NEG) and \
                     (res & self._MASK_NEG == value & self._MASK_NEG)
        self._ps.z = res == 0
        self._ps.n = res & self._MASK_NEG
        self._a = res & self._MASK8

    @instruction(
        CpuInstructionDesc(0x07, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x17, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x0F, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x1F, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0x1B, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0x03, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0x13, AddrMode.INDIRECT_Y, 8)
    )
    def _slo(self, addr: int):
        val = self._memory.read(addr)
        val <<= 1
        self._ps.c = val > 255
        val &= self._MASK8
        self._a = self._a | val
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG
        self._memory.write(addr, val)

    @instruction(
        CpuInstructionDesc(0x27, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x37, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x2F, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x3F, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0x3B, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0x23, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0x33, AddrMode.INDIRECT_Y, 8)
    )
    def _rla(self, addr: int):
        val = self._memory.read(addr)
        temp = self._ps.c
        self._ps.c = val & self._MASK_NEG
        val = (val << 1 | temp) & self._MASK8
        self._a &= val
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG
        self._memory.write(addr, val)

    @instruction(
        CpuInstructionDesc(0x47, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x57, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x4F, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x5F, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0x5B, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0x43, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0x53, AddrMode.INDIRECT_Y, 8)
    )
    def _sre(self, addr: int):
        val = self._memory.read(addr)
        self._ps.c = val & 1
        val >>= 1
        self._a = self._a ^ val & self._MASK8
        self._ps.z = self._a == 0
        self._ps.n = self._a & self._MASK_NEG
        self._memory.write(addr, val)

    @instruction(
        CpuInstructionDesc(0x67, AddrMode.ZERO_PAGE, 5),
        CpuInstructionDesc(0x77, AddrMode.ZERO_PAGE_X, 6),
        CpuInstructionDesc(0x6F, AddrMode.ABSOLUTE, 6),
        CpuInstructionDesc(0x7F, AddrMode.ABSOLUTE_X, 7),
        CpuInstructionDesc(0x7B, AddrMode.ABSOLUTE_Y, 7),
        CpuInstructionDesc(0x63, AddrMode.INDIRECT_X, 8),
        CpuInstructionDesc(0x73, AddrMode.INDIRECT_Y, 8)
    )
    def _rra(self, addr: int):
        val = self._memory.read(addr)
        temp = self._ps.c
        self._ps.c = val & 1
        val = val >> 1 | temp << 7
        res = self._a + val + self._ps.c
        self._ps.c = res > 255
        self._ps.v = (self._a & self._MASK_NEG == val & self._MASK_NEG) and \
                     (self._a & self._MASK_NEG != res & self._MASK_NEG)
        self._ps.n = res & self._MASK_NEG
        self._a = res & self._MASK8
        self._ps.z = self._a == 0
        self._memory.write(addr, val)

    @instruction(
        CpuInstructionDesc(0x1A, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0x3A, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0x5A, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0x7A, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0xDA, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0xFA, AddrMode.IMPLIED, 2),
        CpuInstructionDesc(0x80, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x82, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x89, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xC2, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0xE2, AddrMode.IMMEDIATE, 2),
        CpuInstructionDesc(0x04, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x44, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x64, AddrMode.ZERO_PAGE, 3),
        CpuInstructionDesc(0x14, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x34, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x54, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x74, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xD4, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0xF4, AddrMode.ZERO_PAGE_X, 4),
        CpuInstructionDesc(0x0C, AddrMode.ABSOLUTE, 4),
        CpuInstructionDesc(0x1C, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x3C, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x5C, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0x7C, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0xDC, AddrMode.ABSOLUTE_X, 4),
        CpuInstructionDesc(0xFC, AddrMode.ABSOLUTE_X, 4)
    )
    def _nop_illegal(self, value=None, addr=None):
        pass
