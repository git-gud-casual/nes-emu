from utils import FlagsRegister


class ControllerRegister(FlagsRegister):
    _value: int = 0

    @property
    def nametable_addr(self) -> int:
        return self._value & 0b11

    @property
    def addr_inc(self) -> bool:
        return self._get_bit(2)

    @property
    def sprite_addr(self) -> bool:
        return self._get_bit(3)

    @property
    def bg_addr(self) -> bool:
        return self._get_bit(4)

    @property
    def sprite_size(self) -> bool:
        return self._get_bit(5)

    @property
    def ms_select(self) -> bool:
        return self._get_bit(6)

    @property
    def gen_nmi(self) -> bool:
        return self._get_bit(7)


class MaskRegister(FlagsRegister):
    _value: int = 0

    @property
    def greyscale(self) -> bool:
        return self._get_bit(0)

    @property
    def show_bg8(self) -> bool:
        return self._get_bit(1)

    @property
    def show_sprites8(self) -> bool:
        return self._get_bit(2)

    @property
    def show_bg(self) -> bool:
        return self._get_bit(3)

    @property
    def show_spites(self) -> bool:
        return self._get_bit(4)

    @property
    def emphasize_red(self) -> bool:
        return self._get_bit(5)

    @property
    def emphasize_green(self) -> bool:
        return self._get_bit(6)

    @property
    def emphasize_blue(self) -> bool:
        return self._get_bit(7)


class StatusRegister(FlagsRegister):
    pass


class PPU:
    # Registers
    _ppu_ctrl: ControllerRegister = ControllerRegister()
    _ppu_mask: MaskRegister = MaskRegister()
    _ppu_status: StatusRegister = 0
    _oam_addr: int = 0
    _oam_data: int = 0
    _ppu_scroll: int = 0
    _ppu_addr: int = 0
    _ppu_data: int = 0
    _oam_dma: int = 0

    def set_ctrl_reg(self, value: int):
        self._ppu_ctrl.value = value

    def set_mask_reg(self, value: int):
        self._ppu_mask.value = value
