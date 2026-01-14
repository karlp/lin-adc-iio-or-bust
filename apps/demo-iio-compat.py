#!python3
"""
Fork of the demo app, intended to test out single ended reading, using start/stop commands ala the in tree iio driver
"""

import argparse
import csv
import enum
import pathlib
import time
import selectors

import ads126x
import ads124s0x
import gcdev
import spidev

class Board(enum.StrEnum):
    # https://www.waveshare.com/18983.htm
    WV_ADS1263 = "wv-ads1263"
    # https://github.com/karlp/exp-iio-ads124s08
    HAT_ADS124S08_IIO = "hat-ads124s08-iio"

def getopts():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--gpiochip", help="gpio chip path for DRDY line", default="/dev/gpiochip0")
    # These are for waveshare ads1263 pihat
    #parser.add_argument("--gpio-drdy", help="Gpio line number for DRDY line", default=17)
    #parser.add_argument("--gpio-rst", help="Gpio line number for DRDY line", default=18)
    # These are for my pihat-ads124s08r1
    parser.add_argument("--gpio-drdy", help="Gpio line number for DRDY line", default=24)
    parser.add_argument("--gpio-rst", help="Gpio line number for RST line", default=22)
    parser.add_argument("--gpio-start", help="Gpio line number for START line", default=5)
    parser.add_argument("-c", "--csv-file", help="Write a csv file with values read")
    parser.add_argument("--spibus", help="spi bus to use in userspace", default=0, type=int)
    # This is the 'm' in which of the SPIn.CSm right?
    parser.add_argument("--spidevice", help="spi device to use in userspace", default=0, type=int)

    parser.add_argument("-V", "--volts",  help="Convert readings to volts if non-zero, using this excitation voltage", type=float, default=0)
    # allow a top level switch to try and set a few things automatically
    parser.add_argument("-b", "--board", help="Which ADC board are you trying to use (will override gpio pin choices)",
                        choices=[Board.HAT_ADS124S08_IIO, Board.WV_ADS1263, "auto"],
                        default="auto")
    opts = parser.parse_args()
    if opts.board == "auto":
        # ok, magic time!
        q = pathlib.Path("/proc/device-tree/hat/product")
        if q.exists():
            pname:str = q.open().read()
            if pname.startswith("Hat-ADS124S08-IIO"):
                opts.board = Board.HAT_ADS124S08_IIO
            else:
                raise RuntimeError(f"Hat with ids found, but not one we support: {pname}")
        else:
            print("No hat eeprom found, defaulting to the waveshare board that doesn't hve that..")
            opts.board = Board.WV_ADS1263
            #raise RuntimeError(f"Cannot attempt auto config when hat has no eeprom ids")
    if opts.board == Board.WV_ADS1263:
        opts.gpio_drdy = 17
        opts.gpio_rst = 18
    if opts.board == Board.HAT_ADS124S08_IIO:
        opts.gpio_drdy = 24
        opts.gpio_rst = 22
        opts.gpio_start = 5
    return opts


def basic1(opts):
    print("opts are", opts)
    # Simplistic basic setup
    # tie start low when using commands instead of pins
    gpio_start = gcdev.OutputRequestSingle(opts.gpiochip, opts.gpio_start, consumer="ads128s0x-start")
    gpio_start.set(0)
    # I think I need to set the reset pin properly?
    gpio_rst = gcdev.OutputRequestSingle(opts.gpiochip, opts.gpio_rst, consumer="ads128s0x-test-reset")
    gpio_rst.set(0)
    time.sleep(0.1)
    gpio_rst.set(1)
    print("finished resetting cip")
    #gpio_req = gcdev.MonitorRequest(opts.gpiochip, opts.gpio_drdy, consumer="ads126x-test-drdy", rising=False, falling=True)

    adc = None
    if opts.board == Board.WV_ADS1263:
        raise RuntimeError("Not tested code path")
        # adc = ads126x.ADS126x.Probe(opts.spibus, opts.spidevice)
        # adc.set_channel([ads126x.InputMuxChannel.AIN2, ads126x.InputMuxChannel.AIN3])
        # #adc.set_chop(ads126x.ChopMode.Disabled)
        # adc.set_chop(ads126x.ChopMode.ChopAndRotate)
        # adc.set_conv_delay(ads126x.ConversionDelay.Delay_35u)
        # adc.set_idac_mux(ads126x.IDACChannel.NoConnection, ads126x.IDACChannel.NoConnection)
        # #adc.set_idac_mux(ads126x.IDACChannel.AIN4, ads126x.IDACChannel.NoConnection)
        # #adc.set_idac_mag(ads126x.IDACMagnitude.uA_3000, ads126x.IDACMagnitude.Off)
        # #adc.set_reference(ads126x.RefPositive.Interval2V5P, ads126x.RefNegative.Interval2V5N)
        # adc.set_reference(ads126x.RefPositive.ExtAIN0, ads126x.RefNegative.ExtAIN1)
        # adc.set_pga(ads126x.PGAGain.Gain32)
    elif opts.board == Board.HAT_ADS124S08_IIO:
        adc = ads124s0x.ADS124S0x.Probe(opts.spibus, opts.spidevice)
        # pihat 124s08 ch-A
        adc.set_channel(ads124s0x.InputMuxChannel.AIN0)
        #adc.set_channel(ads124s0x.InputMuxChannel.AIN9)
        #adc.set_reference(ads124s0x.Reference.Ref_P0N0)
        #adc.set_chop(ads124s0x.ChopMode.Global)
        #adc.set_channel(ads124s0x.InputMuxChannel.AIN0)
        # hack to turn on the internal reference
        #reg = adc._read1reg(ads124s0x.Registers.REF)
        #reg &= ~(0x3)
        # hack to turn on the internal ref, and the buffers off.
        adc._write1reg(ads124s0x.Registers.REF, 1 | (3<<4))
        adc.set_reference(ads124s0x.Reference.Internal_2v5) # in tree relies on reset values, which is the ext ref pins
        #adc.set_filter(ads124s0x.DigitalFilter.Sinc3)
        #adc.set_data_rate(ads124s0x.DataRate.SPS_100)
        #adc.set_idac_mux(ads124s0x.IDACChannel.NoConnection, ads124s0x.IDACChannel.NoConnection)
        #adc.set_pga(ads124s0x.PGAGain.Gain32)
        adc.send_status(True)
        #adc.set_crc(True)
    print(f"Found an adc: {adc}")

    adc.set_continuous(False)  # Missing in the in kernel driver!
    # adc.gpio_directions_all(0xf)
    # adc.gpio_set_all(0x5)
    adc.gpio_directions_all(0)
    adc.gpio_set_all(0)
    adc.gpio_as_gpio_all(0xf)

    wf = None
    wff = None
    if opts.csv_file:
        wf = open(opts.csv_file, 'w')
        fieldnames = ['timestamp_ns', 'value']
        wff = csv.DictWriter(wf, fieldnames=fieldnames)
        wff.writeheader()

    print("About to start: regs are: ", adc.dump_regs())
    adc.dump_regs_hack()
    #adc.start()
    # now, poll the gc dev for input events grab the timestamp and read in the data!

    last_ts = time.time() * 1000
    last_delta = 0

    gpio_tick = 0
    while True:
        adc.start()
        # there's no way this is actually ready right?
        time.sleep(0.01)
        status, rval, crc = adc.manual_read()
        adc.stop()
        val = rval
        if opts.volts > 0:
            val = adc.to_volts(rval, opts.volts)

        latest_ts = time.time() * 1000
        delta_t = latest_ts - last_ts
        jitter = delta_t - last_delta

        last_ts = latest_ts
        last_delta = delta_t

        print(f"tdelta: {delta_t} ({1e3/delta_t:#.5g} Hz) jitter: {jitter*1000:+06} us status: {status:#02x} -> rval: {rval} -> value: {val}")
        if wff:
            wff.writerow({'timestamp_ns': latest_ts, 'value': val})
            wf.flush()
        time.sleep(0.5)
        adc.gpio_set_all(gpio_tick % 8)
        gpio_tick += 1
        adc.dump_regs_hack()


if __name__ == "__main__":
    opts = getopts()
    basic1(opts)