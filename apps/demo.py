#!python3
"""
"App" that configures and runs the ADC...

### Note: waveshare in their infinite wisdom didn't use one of the hardware chip select
pins.  You _either_ do it all by hand around spidev calls, like a fucking caveman,
_or_ use something like below, which doesn't seem to work via a runtime dtoverlay at least,
but might work with a boot config,
_or_ just jumper from CE0 or CE1 over to the right pin :| thanks guys, really helpful.
Name:   spi0-2cs
Info:   Change the CS pins for SPI0
Load:   dtoverlay=spi0-2cs,<param>=<val>
Params: cs0_pin                 GPIO pin for CS0 (default 8)
        cs1_pin                 GPIO pin for CS1 (default 7)
        no_miso                 Don't claim and use the MISO pin (9), freeing
                                it for other uses.

# look at rme-meter2 for more asyncio running examples...
"""

import argparse
import csv
import time
import selectors

import ads126x
import ads124s0x
import gcdev
import spidev

def getopts():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--gpiochip", help="gpio chip path for DRDY line", default="/dev/gpiochip0")
    # These are for waveshare ads1263 pihat
    #parser.add_argument("--gpio-drdy", help="Gpio line number for DRDY line", default=17)
    #parser.add_argument("--gpio-rst", help="Gpio line number for DRDY line", default=18)
    # These are for my pihat-ads124s08r1
    parser.add_argument("--gpio-drdy", help="Gpio line number for DRDY line", default=24)
    parser.add_argument("--gpio-rst", help="Gpio line number for DRDY line", default=22)
    parser.add_argument("-c", "--csv-file", help="Write a csv file with values read")
    parser.add_argument("--spibus", help="spi bus to use in userspace", default=0, type=int)
    # This is the 'm' in which of the SPIn.CSm right?
    parser.add_argument("--spidevice", help="spi device to use in userspace", default=0, type=int)
    return parser.parse_args()


def basic1(opts):
    print("opts are", opts)
    # Simplistic basic setup
    # I think I need to set the reset pin properly?
    gpio_rst = gcdev.OutputRequestSingle(opts.gpiochip, opts.gpio_rst, consumer="ads126x-test-reset")
    gpio_rst.set(0)
    time.sleep(0.1)
    gpio_rst.set(1)
    print("finished resetting cip")
    gpio_req = gcdev.MonitorRequest(opts.gpiochip, opts.gpio_drdy, consumer="ads126x-test-drdy", rising=False, falling=True)

    #adc = ads126x.ADS126x.Probe(opts.spibus, opts.spidevice)
    adc = ads124s0x.ADS124S0x.Probe(opts.spibus, opts.spidevice)
    print(f"Found an adc: {adc}")

    # differential, using names
    #adc.set_channel([ads126x.InputMuxChannel.AIN2, ads126x.InputMuxChannel.AIN3])
    # pihat 124s08 ch-A
    adc.set_channel([ads124s0x.InputMuxChannel.AIN4, ads124s0x.InputMuxChannel.AIN5])
    adc.set_reference(ads124s0x.Reference.Ref_P0N0)
    # pihat 124s08 ch-B
    #adc.set_channel([ads124s0x.InputMuxChannel.AIN2, ads124s0x.InputMuxChannel.AIN3])
    #adc.set_reference(ads124s0x.Reference.Ref_P1N1)
    #adc.set_channel([ads126x.InputMuxChannel.AIN6, ads126x.InputMuxChannel.AIN7])
    # or single ended, using raw numbers.
    #adc.set_channel(3)
    adc.set_chop(ads124s0x.ChopMode.Global)
    #adc.set_chop(ads126x.ChopMode.Disabled)
    adc.set_continuous(True)
    adc.set_filter(ads124s0x.DigitalFilter.Sinc3)
    # 2400 will ocassionally glitch out, lower is fine.
    # 20 is just so I don't bury my screen :)
    adc.set_data_rate(ads124s0x.DataRate.SPS_100)
    #adc.set_conv_delay(ads126x.ConversionDelay.Delay_35u)
    adc.set_idac_mux(ads124s0x.IDACChannel.NoConnection, ads124s0x.IDACChannel.NoConnection)
    #adc.set_idac_mux(ads126x.IDACChannel.AIN4, ads126x.IDACChannel.NoConnection)
    #adc.set_idac_mag(ads126x.IDACMagnitude.uA_3000, ads126x.IDACMagnitude.Off)
    #adc.set_reference(ads126x.RefPositive.Interval2V5P, ads126x.RefNegative.Interval2V5N)
    #adc.set_reference(ads126x.RefPositive.ExtAIN0, ads126x.RefNegative.ExtAIN1)
    adc.set_pga(ads126x.PGAGain.Gain32)
    adc.gpio_directions_all(0xf)
    adc.gpio_set_all(0x5)

    wf = None
    wff = None
    if opts.csv_file:
        wf = open(opts.csv_file, 'w')
        fieldnames = ['timestamp_ns', 'value']
        wff = csv.DictWriter(wf, fieldnames=fieldnames)
        wff.writeheader()

    print("About to start: regs are: ", adc.dump_regs())
    adc.dump_regs_hack()
    adc.start()
    # now, poll the gc dev for input events grab the timestamp and read in the data!

    last_ts_ns = 0
    last_delta_ns = 0
    def handle_drdy(fd):
        evs = gpio_req.get_events()
        # We should get kernel tstamps here, and we _should_ only get 1
        if len(evs) > 1:
            print("FATAL! you got multiple falling edges and have lost data!")
        #[print(e) for e in evs]
        ev = evs[0]
        nonlocal last_ts_ns
        nonlocal last_delta_ns
        delta_t = ev.timestamp_ns - last_ts_ns
        jitter = delta_t - last_delta_ns
        last_ts_ns = ev.timestamp_ns
        last_delta_ns = delta_t

        # TODO - now read the data out
        #val = adc.read_data()
        #print(f"lollllalv: {val}")
        status, val = adc.read_data_rel()
        print(f"tdelta: {delta_t} ({1e9/delta_t:#.5g} Hz) jitter: {jitter:+06} ns status: {status:#02x} -> value: {val}")
        if wff:
            wff.writerow({'timestamp_ns': ev.timestamp_ns, 'value': val})
            wf.flush()

    # How I used this in asyncio elsewhere..n
    #fd_gpio = self.gpio_req.get_fd()
    #asyncio.get_running_loop().add_reader(fd_gpio, handle_zx)
    # alternatively use "selectors"
    sel = selectors.DefaultSelector()
    sel.register(gpio_req.get_fd(), selectors.EVENT_READ, handle_drdy)
    while True:
        #time.sleep(0.01) # If you make this too big, you'll start seeing gaps in your sequence numbers received
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj)


if __name__ == "__main__":
    opts = getopts()
    basic1(opts)