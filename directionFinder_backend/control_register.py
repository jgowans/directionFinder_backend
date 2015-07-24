""" Interface to the control register on the FPGA
Bits:
    0 - manual sync
    1 - snap gate
    2 - accumulation counter reset
    3 - FFT overflow latch reset
    4:5 - adc select
    6:18 - fft shift schedule
"""

import logging

class ControlRegister:
    def __init__(self, fpga, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.fpga = fpga
        self.value = self.fpga.read_uint('control')
        self.write()

    def write(self):
        self.fpga.write_int('control', self.value)
        self.logger.debug("Control register written to value: {val:#x}".format(val = self.value))
    
    def pulse_sync(self):
        self.value &= ~(1 << 0)  # clear bit 0
        self.write()
        self.value |= (1 << 0)  # set bit 0
        self.write()
        self.value &= ~(1 << 0)  # clear bit 0
        self.write()
        self.logger.debug("Pulsed sync bit")

    def block_trigger(self):
        self.value &= ~(1 << 1)
        self.write()
        self.logger.debug("Control register set to block trigger.")

    def allow_trigger(self):
        self.value |= (1 << 1)
        self.write()
        self.logger.debug("Control register set to allow trigger.")

    def reset_accumulation_counter(self):
        self.value &= ~(1 << 2)
        self.write()
        self.value |= (1 << 2)
        self.write()
        self.value &= ~(1 << 2)
        self.write()
        self.logger.debug("Control register pulsed accumulation counter reset bit")

    def pulse_overflow_rst(self):
        self.value &= ~(1 << 3)
        self.write()
        self.value |= (1 << 3)
        self.write()
        self.value &= ~(1 << 3)
        self.write()
        self.logger.debug("Control register pulsed overflow reset bit")

    def select_adc(self, adc):
        """ Selects which ADC channel is connected to the time domain snap

        adc -- '0I', '0Q', '1I' or '1Q'
        """
        channel_to_mux = {
            '0I': 0b00,
            '0Q': 0b01,
            '1I': 0b10,
            '1Q': 0b11,
        }
        self.value &= ~(0b11 << 4)
        self.value |= (channel_to_mux[adc] << 4)
        self.write()
        self.logger.debug("Control register selected ADC channel {c}.".format(c = adc))

    def set_shift_schedule(self, schedule):
        self.value &= ~(0xFFF << 6)
        self.value |= (schedule << 6)
        self.write()
        self.logger.debug("Setting shift schedule to {ss:#x}.".format(ss = schedule))
