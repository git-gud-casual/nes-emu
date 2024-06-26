import logging

from time import time
from cpu.cpu import Cpu
from memory import CpuMemoryMapper, NROMCartridge
from ppu import PPU


logging.basicConfig(level=logging.INFO, filename="../nestest/mylog.log", filemode="w")

if __name__ == "__main__":
    size = 16384
    with open("../nestest/nestest.nes", 'rb') as f:
        cont = f.read()
    a = bytearray(16384)
    a.extend(cont[16:size + 16])
    a.extend(bytearray(16384 * 2))
    a[0xFFFC - 0x8000] = 0x00
    a[0xFFFC - 0x8000 + 1] = 0xC0

    ppu = PPU()
    cpu = Cpu(CpuMemoryMapper(NROMCartridge(a), ppu))
    start = time()
    for i in range(8991):
        cpu.process()
    print(f"Time: {time() - start}. CPU Cycles: {cpu._cycles_count}")
    print(ppu._ppu_ctrl.value)
