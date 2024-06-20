from abc import ABC, abstractmethod


class BaseMemory(ABC):
    _memory: bytearray

    @abstractmethod
    def read(self, addr: int) -> int:
        pass

    @abstractmethod
    def write(self, addr: int, value: int):
        pass


class BaseCartridge(BaseMemory, ABC):
    pass
