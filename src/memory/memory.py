from ppu import PPU
from .bases import BaseMemory, BaseCartridge


class CpuMemoryMapper(BaseMemory):
    _SIZE = 2 ** 16
    _RAM_SIZE = 0x0800
    _RAM_END = 0x2000
    _PPU_START = 0x2000
    _PPU_END = 0x4000
    _PPU_SIZE = 0x8
    _APU_AND_IO_END = 0x4018
    _APU_UNUSED_END = 0x4020
    _CART_MEM_END = 0xFFFF

    _PPU_CONTROLLER_ADDR = 0x2000
    _PPU_MASK_ADDR = 0x2001
    _PPU_OAM_ADDR = 0x2003

    _memory: bytearray
    _ppu: PPU

    def __init__(self, cart: BaseCartridge, ppu: PPU):
        self._memory = bytearray(self._SIZE)
        self._ppu = ppu
        self._cart = cart

    def read(self, addr: int) -> int:
        if addr < self._RAM_END:
            return self._memory[addr % self._RAM_SIZE]
        elif addr < self._PPU_END:
            addr %= self._PPU_SIZE
            raise NotImplementedError()
        elif addr < self._APU_AND_IO_END:
            raise NotImplementedError()
        elif addr < self._APU_UNUSED_END:
            return 0
        else:
            return self._cart.read(addr)

    def write(self, addr: int, value: int):
        if addr < self._RAM_END:
            self._memory[addr % self._RAM_SIZE] = value
        elif addr < self._PPU_END:
            addr %= self._PPU_SIZE
            if addr == self._PPU_CONTROLLER_ADDR:
                self._ppu.set_ctrl_reg(value)
            elif addr == self._PPU_MASK_ADDR:
                self._ppu.set_mask_reg(value)
            elif addr == self._PPU_OAM_ADDR:
                pass
            raise NotImplementedError()
        elif addr < self._APU_AND_IO_END:
            print("APU_AND_IO WRITE")
            # raise NotImplementedError()
        elif addr < self._APU_UNUSED_END:
            pass
        else:
            raise NotImplementedError()


