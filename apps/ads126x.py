#!python3
"""
Util for talking to an ads1262/ads1263 over spidev,
or something implementing spidev...

DRDY is via.... lolll... can we just defer that to an external app?
(yes please)

Karl Palsson <karlp@tweak.au> Sept 2025
"""

import enum
import struct

# try import, else import a stub one?
import spidev
#import gcdev

class Registers(enum.Enum):
    ID = 0
    POWER = enum.auto()
    INTERFACE = enum.auto()
    MODE0 = enum.auto()
    MODE1 = enum.auto()
    MODE2 = enum.auto()
    INPMUX = enum.auto()
    OFCAL0 = enum.auto()
    OFCAL1 = enum.auto()
    OFCAL2 = enum.auto()
    FSCAL0 = enum.auto()
    FSCAL1 = enum.auto()
    FSCAL2 = enum.auto()
    IDACMUX = enum.auto()
    IDACCFG = enum.auto()
    REFMUX = enum.auto()
    TDACP = enum.auto()
    TDACN = enum.auto()
    GPIOCON = enum.auto()
    GPIODIR = enum.auto()
    GPIODAT = enum.auto()
    ADC2CFG = enum.auto()
    ADC2MUX = enum.auto()
    ADC2OFC0 = enum.auto()
    ADC2OFC1 = enum.auto()
    ADC2FSC0 = enum.auto()
    ADC2FSC1 = enum.auto()

class Command(enum.Enum):
    NOP = 0
    RESET = 0x6
    START1 = 0x8
    STOP1 = 0xa
    START2 = 0xc
    STOP2 = 0xe
    RDATA1 = 0x12
    RDATA2 = 0x14
    SYOCAL1 = 0x16
    SYGCAL1 = 0x17
    SFOCAL1 = 0x19
    SYOCAL2 = 0x1b
    SYGCAL2 = 0x1c
    SFOCAL2 = 0x1e
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
    InputChop = enum.auto()
    IDACRotate = enum.auto()
    ChopAndRotate = enum.auto()
    # Is this a good idea or a terrible idea?
    _SHIFT = 4
    _MASK = 0x3

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
    AINCOM = enum.auto()
    TempMonN = 11
    TempMonP = 11
    APwrMonN = 12
    APwrMonP = 12
    DPwrMonN = 13
    DPwrMonP = 13
    TDACN = 14
    TDACP = 14
    Float = 15

class DigitalFilter(enum.Enum):
    Sinc1 = 0
    Sinc2 = enum.auto()
    Sinc3 = enum.auto()
    Sinc4 = enum.auto()
    FIR = enum.auto()
    _MASK = 0x7
    _SHIFT = 5

class PGAGain(enum.Enum):
    Gain1 = 0
    Gain2 = enum.auto()
    Gain4 = enum.auto()
    Gain8 = enum.auto()
    Gain16 = enum.auto()
    Gain32 = enum.auto()
    _MASK = 0x7
    _SHIFT = 4

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
    SPS_400 = enum.auto()
    SPS_1200 = enum.auto()
    SPS_2400 = enum.auto()
    SPS_4800 = enum.auto()
    SPS_7200 = enum.auto()
    SPS_14400 = enum.auto()
    SPS_19200 = enum.auto()
    SPS_38400 = enum.auto()
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
    AINCOM = enum.auto()
    NoConnection = enum.auto()

class IDACMagnitude(enum.Enum):
    Off = 0
    uA_50 = enum.auto()
    uA_100 = enum.auto()
    uA_250 = enum.auto()
    uA_500 = enum.auto()
    uA_750 = enum.auto()
    uA_1000 = enum.auto()
    uA_1500 = enum.auto()
    uA_2000 = enum.auto()
    uA_2500 = enum.auto()
    uA_3000 = enum.auto()

class RefPositive(enum.Enum):
    Interval2V5P = 0
    ExtAIN0 = enum.auto()
    ExtAIN2 = enum.auto()
    ExtAIN4 = enum.auto()
    InternaleAVDD = enum.auto()

class RefNegative(enum.Enum):
    Interval2V5N = 0
    ExtAIN1 = enum.auto()
    ExtAIN3 = enum.auto()
    ExtAIN5 = enum.auto()
    InternaleAVSS = enum.auto()

class ADS126x:
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
        regs = self.spid.xfer([Command.RREG(Registers.MODE1), 0, 0])
        oval = regs[2] & ~(7<<5)
        oval |= filter.value << 5
        self.spid.xfer2([Command.WREG(Registers.MODE1), 0, oval])

    def set_chop(self, chop: ChopMode):
        reg = self._read1reg(Registers.MODE0)
        reg &= ~(ChopMode._MASK.value << ChopMode._SHIFT.value)
        reg |= chop.value << ChopMode._SHIFT.value
        self._write1reg(Registers.MODE0, reg)

    def set_continuous(self, continuous: bool):
        reg = self._read1reg(Registers.MODE0)
        if continuous:
            reg &= ~(1<<6)
        else:
            reg |= (1<<6)
        self._write1reg(Registers.MODE0, reg)

    def set_filter(self, filter: DigitalFilter):
        reg = self._read1reg(Registers.MODE1)
        reg &= ~(DigitalFilter._MASK.value << DigitalFilter._SHIFT.value)
        reg |= filter.value << DigitalFilter._SHIFT.value
        self._write1reg(Registers.MODE1, reg)

    def set_data_rate(self, val: DataRate):
        reg = self._read1reg(Registers.MODE2)
        reg &= ~(DataRate._MASK.value << DataRate._SHIFT.value)
        reg |= val.value << DataRate._SHIFT.value
        self._write1reg(Registers.MODE2, reg)

    def set_idac(self, idac1:IDACChannel, idac2: IDACChannel):
        reg = idac2.value << 4 | idac1.value
        self._write1reg(Registers.IDACMUX, reg)

    def set_reference(self, pos: RefPositive, neg: RefNegative):
        reg = pos.value << 3 | neg.value
        self._write1reg(Registers.REFMUX, reg)

    def set_pga(self, val: PGAGain):
        reg = self._read1reg(Registers.MODE2)
        reg &= ~(PGAGain._MASK.value << PGAGain._SHIFT.value)
        reg |= val.value << PGAGain._SHIFT.value
        self._write1reg(Registers.MODE2, reg)

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

    def _set_tdac(self, tdac, enable: bool, mag=0):
        reg = mag & 0x1f
        if enable:
            reg |= 0x80
        self._write1reg(tdac, reg)

    def set_tdacp(self, enable: bool, mag=0):
        """Enable is to enable on the ain6"""
        self._set_tdac(Registers.TDACP, enable, mag)
    def set_tdacn(self, enable: bool, mag=0):
        """Enable is to enable on the ain7"""
        self._set_tdac(Registers.TDACN, enable, mag)

    def dump_regs_hack(self):
        for v in Registers:
            print(f"Register: {v.name} is : {self._read1reg(v):#02x}")

    def dump_regs(self):
        # this is not really better is it :)
        blob = [Command.RREG(Registers(0)), 0x19]
        blob.extend([0]*0x1a)
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
        devid = chipid[2] >> 5
        revid = chipid[2] & 0x1f
        print(f"Read chipid as: {chipid} => dev {devid} revid: {revid}")
        # TODO: more validation please!
        # Attempting a reset and reading idacmux and mode?
        if devid == 1:
            return ADS1263(spid, chipid)
        if devid == 0:
            return ADS1262(spid, chipid)

class ADS1262(ADS126x):
    def __init__(self, spid, chipid):
        super().__init__(spid, chipid)
        pass
    
class ADS1263(ADS126x):
    def __init__(self, spid, chipid):
        super().__init__(spid, chipid)
        pass

