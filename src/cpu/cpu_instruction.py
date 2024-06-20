from typing import List, Callable
from .addr_modes import AddrMode
from dataclasses import dataclass


@dataclass(frozen=True)
class CpuInstructionDesc:
    opcode: int
    addr_mode: AddrMode
    cycles: int


@dataclass(frozen=True)
class CpuInstruction:
    opcode: int
    addr_mode: AddrMode
    cycles: int
    function: Callable


@dataclass(frozen=True)
class CpuInstructionWrapper:
    descriptions: List[CpuInstruction]


def instruction(*descriptions: CpuInstructionDesc):
    def wrap(function):
        return CpuInstructionWrapper([CpuInstruction(desc.opcode, desc.addr_mode, desc.cycles, function)
                                      for desc in descriptions])
    return wrap
