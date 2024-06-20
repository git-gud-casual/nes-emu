from enum import Enum


class AddrMode(Enum):
    ACCUMULATOR = 0
    IMMEDIATE = 1
    ZERO_PAGE = 2
    ZERO_PAGE_X = 3
    ZERO_PAGE_Y = 4
    RELATIVE = 5
    ABSOLUTE = 6
    ABSOLUTE_X = 7
    ABSOLUTE_Y = 8
    INDIRECT = 9
    INDIRECT_X = 10
    INDIRECT_Y = 11
    IMPLIED = 12
