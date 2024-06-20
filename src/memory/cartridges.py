from .bases import BaseCartridge


class NROMCartridge(BaseCartridge):
    _memory: bytearray

    def __init__(self, rom: bytearray):
        self._memory = rom

    def read(self, addr: int) -> int:
        if addr < 0x8000:
            raise ValueError(addr)
        return self._memory[addr - 0x8000]

    def write(self, addr: int, value: int):
        raise NotImplementedError()
