#!python3
"""
Util for talking to an ads124s06/ads124s08 over spidev,
or something implementing spidev...
(pretty sure you only need to change the read function to support 114s0x as well)

DRDY is via.... lolll... can we just defer that to an external app?
(yes please)

Karl Palsson <karlp@tweak.au> Nov 2025
"""

import enum
import struct

# try import, else import a stub one?
import spidev
#import gcdev

class Registers(enum.Enum):
    ID = 0
    STATUS = enum.auto()
    INPMUX = enum.auto()
    PGA = enum.auto()
    DATARATE = enum.auto()
    REF = enum.auto()
    IDACMAG = enum.auto()
    IDACMUX = enum.auto()
    VBIAS = enum.auto()
    SYS = enum.auto()
    OFCAL0 = enum.auto()
    OFCAL1 = enum.auto()
    OFCAL2 = enum.auto()
    FSCAL0 = enum.auto()
    FSCAL1 = enum.auto()
    FSCAL2 = enum.auto()
    GPIODAT = enum.auto()
    GPIOCON = enum.auto()

class Command(enum.Enum):
    NOP = 0
    WAKEUP = 0X2
    POWERDOWN = 0X4
    RESET = 0x6
    START1 = 0x8
    STOP1 = 0xa
    RDATA1 = 0x12
    SYOCAL1 = 0x16
    SYGCAL1 = 0x17
    SFOCAL1 = 0x19
    _RREG = 0x20
    _WREG = 0x40

    @classmethod
    def RREG(cls, reg: Registers):
        return cls._RREG.value + reg.value

    @classmethod
    def WREG(cls, reg: Registers):
        return cls._WREG.value + reg.value

class ChopMode(enum.Enum):
    Disabled = 0
    Global = enum.auto()
    _SHIFT = 7
    _MASK = 0x1

class InputMuxChannel(enum.Enum):
    AIN0 = 0
    AIN1 = enum.auto()
    AIN2 = enum.auto()
    AIN3 = enum.auto()
    AIN4 = enum.auto()
    AIN5 = enum.auto()
    AIN6 = enum.auto()
    AIN7 = enum.auto()
    AIN8 = enum.auto()
    AIN9 = enum.auto()
    AIN10 = enum.auto()
    AIN11 = enum.auto()
    AINCOM = enum.auto()

class DigitalFilter(enum.Enum):
    Sinc3 = 0
    LowLatency = enum.auto()
    _MASK = 0x1
    _SHIFT = 4

class PGAGain(enum.Enum):
    Gain1 = 0
    Gain2 = enum.auto()
    Gain4 = enum.auto()
    Gain8 = enum.auto()
    Gain16 = enum.auto()
    Gain32 = enum.auto()
    Gain64 = enum.auto()
    Gain128 = enum.auto()
    _MASK = 0x7
    _SHIFT = 0

class ConversionDelay(enum.Enum):
    Delay_14t = 0
    Delay_25t =enum.auto()
    Delay_64t =enum.auto()
    Delay_256t =enum.auto()
    Delay_1024t =enum.auto()
    Delay_2048t =enum.auto()
    Delay_4096t =enum.auto()
    Delay_1t =enum.auto()
    _MASK = 0x7
    _SHIFT = 5

class DataRate(enum.Enum):
    """
    Remember, these numbers are based on the nominal clock rate!
    Not all are available in all modes.
    """
    SPS_2_5 = 0
    SPS_5 = enum.auto()
    SPS_10 = enum.auto()
    SPS_16_6 = enum.auto()
    SPS_20 = enum.auto()
    SPS_50 = enum.auto()
    SPS_60 = enum.auto()
    SPS_100 = enum.auto()
    SPS_200 = enum.auto()
    SPS_400 = enum.auto()
    SPS_800 = enum.auto()
    SPS_1000 = enum.auto()
    SPS_2000 = enum.auto()
    SPS_4000 = enum.auto()
    _MASK = 0xf
    _SHIFT = 0

class IDACChannel(enum.Enum):
    AIN0 = 0
    AIN1 = enum.auto()
    AIN2 = enum.auto()
    AIN3 = enum.auto()
    AIN4 = enum.auto()
    AIN5 = enum.auto()
    AIN6 = enum.auto()
    AIN7 = enum.auto()
    AIN8 = enum.auto()
    AIN9 = enum.auto()
    AIN10 = enum.auto()
    AIN11 = enum.auto()
    AINCOM = enum.auto()
    NoConnection = enum.auto()

class IDACMagnitude(enum.Enum):
    Off = 0
    uA_10 = enum.auto()
    uA_50 = enum.auto()
    uA_100 = enum.auto()
    uA_250 = enum.auto()
    uA_500 = enum.auto()
    uA_750 = enum.auto()
    uA_1000 = enum.auto()
    uA_1500 = enum.auto()
    uA_2000 = enum.auto()

class Reference(enum.Enum):
    Ref_P0N0 = 0
    Ref_P1N1 = enum.auto()
    Internal_2v5 = enum.auto()
    _MASK = 0x3
    _SHIFT = 2

class ADS124S0x:
    def __init__(self, spid, chipid):
        self.spid = spid
        self.chipid = chipid
        # default is status on, crc as checksum
        self.rd_size = 6

    def _read1reg(self, reg: Registers):
        regs = self.spid.xfer([Command.RREG(reg), 0, 0])
        return regs[2]

    def _write1reg(self, reg: Registers, val):
        self.spid.xfer2([Command.WREG(reg), 0, val])


    def set_channel(self, chans):
        """
        Given a single or pair of channels, configure the input mux
        """
        if type(chans) in [list,tuple]:
            # differential
            muxp = (chans[0].value & 0xf) << 4
            muxn = chans[1].value & 0xf
        else:
            # single ended
            muxp = (chans.value & 0xf) << 4
            muxn = InputMuxChannel.AINCOM
        reg = muxn | muxp
        self._write1reg(Registers.INPMUX, reg)

    def set_digital_filter(self, filter: DigitalFilter):
        regs = self.spid.xfer([Command.RREG(Registers.DATARATE), 0, 0])
        oval = regs[2] & ~(DigitalFilter._MASK.value << DigitalFilter._SHIFT.value)
        oval |= filter.value << DigitalFilter._SHIFT.value
        self.spid.xfer2([Command.WREG(Registers.DATARATE), 0, oval])

    def set_chop(self, chop: ChopMode):
        reg = self._read1reg(Registers.DATARATE)
        reg &= ~(ChopMode._MASK.value << ChopMode._SHIFT.value)
        reg |= chop.value << ChopMode._SHIFT.value
        self._write1reg(Registers.DATARATE, reg)

    def set_continuous(self, continuous: bool):
        reg = self._read1reg(Registers.DATARATE)
        if continuous:
            reg &= ~(1<<5)
        else:
            reg |= (1<<5)
        self._write1reg(Registers.DATARATE, reg)

    def set_filter(self, filter: DigitalFilter):
        reg = self._read1reg(Registers.DATARATE)
        reg &= ~(DigitalFilter._MASK.value << DigitalFilter._SHIFT.value)
        reg |= filter.value << DigitalFilter._SHIFT.value
        self._write1reg(Registers.DATARATE, reg)

    def set_conv_delay(self, val: ConversionDelay):
        reg = self._read1reg(Registers.PGA)
        reg &= ~(ConversionDelay._MASK.value << ConversionDelay._SHIFT.value)
        reg |= val.value << ConversionDelay._SHIFT.value
        self._write1reg(Registers.PGA, reg)

    def set_data_rate(self, val: DataRate):
        reg = self._read1reg(Registers.DATARATE)
        reg &= ~(DataRate._MASK.value << DataRate._SHIFT.value)
        reg |= val.value << DataRate._SHIFT.value
        self._write1reg(Registers.DATARATE, reg)

    def set_idac_mux(self, idac1:IDACChannel, idac2: IDACChannel):
        reg = idac2.value << 4 | idac1.value
        self._write1reg(Registers.IDACMUX, reg)

    def set_idac_mag(self, idac1:IDACMagnitude, idac2: IDACMagnitude):
        reg = idac2.value << 4 | idac1.value
        self._write1reg(Registers.IDACMAG, reg)

    def set_reference(self, ref: Reference):
        reg = self._read1reg(Registers.REF)
        reg &= ~(Reference._MASK.value << Reference._SHIFT.value)
        reg |= ref.value << Reference._SHIFT.value
        self._write1reg(Registers.REF, reg)

    def set_pga(self, val: PGAGain):
        # TODO do we care about supprot for PGA _on_ with gain 1?
        reg = self._read1reg(Registers.PGA)
        reg &= ~(PGAGain._MASK.value << PGAGain._SHIFT.value)
        enbits = 1
        if val == PGAGain.Gain1:
            enbits = 0
        reg |= val.value << PGAGain._SHIFT.value | enbits << 3
        self._write1reg(Registers.PGA, reg)

    def start(self):
        self.spid.xfer2([Command.START1.value])

    def read_data(self):
        # sko, a few options here.  read direct? just clock out as much as we expect?
        # todo, keep track of howm anybytes to expect based on our calls so far?
        # 5 is status + 32bit data? reading 10 repeats, that would be sexy...
        bla = self.spid.xfer2([0]*self.rd_size)
        struct.unpack("<Bi", bytes(bla))
        return struct.unpack("<Bi", bla)

    def read_data_rel(self):
        # This uses the "repeating" mode of direct reads to check that there was no bit corruption
        # It's _probably_ wayyyy overkill really, we low pass everythign anyway, but it's fine to do and demonstrate
        blah = self.spid.xfer2([0]*self.rd_size*2)
        #print("double check?", blah)
        if self.rd_size == 6:
            s1, d1, c1, s2, d2, c2 = struct.unpack(">BiBBiB", bytes(blah))
        elif self.rd_size == 5:
            s1, d1, s2, d2 = struct.unpack(">BiBi", bytes(blah))
        if s1 != s2 or d1 != d2:
            print("WARNING! data read had transmission errors")
        # ok. now jsut return it
        return s1, d1

    def dump_regs_hack(self):
        for v in Registers:
            print(f"Register: {v.name} is : {self._read1reg(v):#02x}")

    def gpio_directions_all(self, dir):
        reg = self._read1reg(Registers.GPIODAT)
        reg &= ~(4 << 4)
        reg |= dir << 4
        self._write1reg(Registers.GPIODAT, reg)

    def gpio_set_all(self, val):
        reg = self._read1reg(Registers.GPIODAT)
        reg &= ~(4 << 0)
        reg |= val
        self._write1reg(Registers.GPIODAT, reg)


    # FIXME - update for ads124s08?
    def dump_regs(self):
        # this is not really better is it :)
        blob = [Command.RREG(Registers(0)), 0x11 - 2]
        blob.extend([0]*0x11)
        regs = self.spid.xfer(blob)
        return regs[2:]

    @classmethod
    def Probe(cls, spibus, spidevice, max_speed=8000000):
    #def Probe(cls, spibus, spidevice, max_speed=2000000):
        spid = spidev.SpiDev(spibus, spidevice)
        spid.max_speed_hz = max_speed
        spid.mode = 1
        chipid = spid.xfer2([Command.RREG(Registers.ID), 0, 0])
        print("ok, rex", chipid)
        #devid = chipid[2] >> 5
        # upper 5 bits are reserved, no values provided
        devid = chipid[2] & 0x7
        print(f"Read chipid as: {chipid} => dev {devid}")
        # TODO: more validation please!
        # Attempting a reset and reading idacmux and mode?
        if devid == 1:
            return ADS124S06(spid, chipid)
        if devid == 0:
            return ADS124S08(spid, chipid)

class ADS124S06(ADS124S0x):
    def __init__(self, spid, chipid):
        super().__init__(spid, chipid)
        pass
    
class ADS124S08(ADS124S0x):
    def __init__(self, spid, chipid):
        super().__init__(spid, chipid)
        pass

