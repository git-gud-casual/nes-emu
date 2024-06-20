import logging

from cpu.cpu import Cpu
from memory import CpuMemory, NROMCartridge


logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # 0xDEAD_BEEF
    a = bytearray(64 * 1024)
    a[0] = 0xA9
    a[1] = 0xDE
    a[2] = 0xA2
    a[3] = 0xEF
    a[4] = 0x9A
    a[5] = 0xA2
    a[6] = 0xAD
    a[7] = 0xA0
    a[8] = 0xBE
    a[0xFFFC - 0x8000 + 1] = 0x80
    cpu = Cpu(CpuMemory(NROMCartridge(a)))
    for _ in range(5):
        cpu.process()
    print()
    cpu.print_info()
