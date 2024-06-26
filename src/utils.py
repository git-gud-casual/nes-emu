from abc import ABC


class FlagsRegister(ABC):
    _value: int

    def _get_bit(self, bit_index: int) -> bool:
        return bool(self._value & (1 << bit_index))

    def _set_bit(self, bit_index: int, value: bool):
        if value:
            self._value |= 1 << bit_index
        else:
            self._value &= ~(1 << bit_index)

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_val: int):
        self._value = new_val
