"""
Pure python interface for the gpio character device
v2 chardev has been available since linux 5.10
v1 compat may or may not be enabled.  (Kernel config recommends enabled, but not all distros have done that)

Alternatives
* https://github.com/vpelletier/python-gpiochip2
  Only v2, but otherwise similar.  Much more expansive python side API.
* https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/
  "canonical" but... v2 library not backward compatible with v1,
   v1 library has bugs (timestamps are garbage in our environment at least)
* https://github.com/hhk7734/python3-gpiod
  Only v1, but otherwise similar.  Way more layered, explicitly attempting to match API
  with libgpiod, just without relying on libgpiod?!

Vintage: 2023....
"""
import ctypes
import enum
import time
import fcntl
import os
import selectors
import typing

_IOC_WRITE = 1
_IOC_READ = 2
_IOC_WR = 3


def _IOC(dir: int, type: int, number: int, size: int) -> int:
    return dir << 30 | size << 16 | type << 8 | number


def _IOR(type: int, number: int, size: int) -> int:
    return _IOC(_IOC_READ, type, number, size)


def _IOWR(type: int, number: int, size: int) -> int:
    return _IOC(_IOC_WR, type, number, size)


# This section is as literally as possible, copied from linux' include/uapi/gpio.h
GPIO_MAX_NAME_SIZE = 32
GPIO_V2_LINES_MAX = 64
GPIOHANDLES_MAX = 64
GPIO_V2_LINE_NUM_ATTRS_MAX = 10


class gpiochip_info(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("label", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("lines", ctypes.c_uint32),
    ]

    def __repr__(self):
        return f"{self.__class__.__name__}<name:{self.name}, label:{self.label}, lines:{self.lines}>"


GPIO_GET_CHIPINFO_IOCTL = _IOR(0xb4, 0x01, ctypes.sizeof(gpiochip_info))


# V2 enums and structs

class GPIO_V2_LINE_FLAG(enum.IntEnum):
    USED = (1 << 0)
    ACTIVE_LOW = (1 << 1)
    INPUT = (1 << 2)
    OUTPUT = (1 << 3)
    EDGE_RISING = (1 << 4)
    EDGE_FALLING = (1 << 5)
    OPEN_DRAIN = (1 << 6)
    OPEN_SOURCE = (1 << 7)
    BIAS_PULL_UP = (1 << 8)
    BIAS_PULL_DOWN = (1 << 9)
    BIAS_PULL_DISABLED = (1 << 10)
    EVENT_CLOCK_REALTIME = (1 << 11)
    EVENT_CLOCK_HTE = (1 << 12)


class GPIO_V2_LINE_ATTR_ID(enum.IntEnum):
    FLAGS = 1
    OUTPUT_VALUES = 2
    DEBOUNCE = 3


class GPIO_V2_LINE_CHANGED(enum.IntEnum):
    REQUESTED = 1
    RELEASED = 2
    CONFIG = 3


class GPIO_V2_LINE_EVENT(enum.IntEnum):
    RISING_EDGE = 1
    FALLING_EDGE = 2


class gpio_v2_line_values(ctypes.Structure):
    _fields_ = [
        ("bits", ctypes.c_uint64),
        ("mask", ctypes.c_uint64),
    ]


class _gpio_v2_line_attibute_u(ctypes.Union):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("values", ctypes.c_uint64),
        ("debounce_period_us", ctypes.c_uint32),
    ]


class gpio_v2_line_attribute(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("u", _gpio_v2_line_attibute_u),
    ]


class gpio_v2_line_config_attribute(ctypes.Structure):
    _fields_ = [
        ("attr", gpio_v2_line_attribute),
        ("mask", ctypes.c_uint64),
    ]


class gpio_v2_line_config(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("num_attrs", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("attrs", gpio_v2_line_config_attribute * GPIO_V2_LINE_NUM_ATTRS_MAX),
    ]


class gpio_v2_line_request(ctypes.Structure):
    _fields_ = [
        ("offsets", ctypes.c_uint32 * GPIO_V2_LINES_MAX),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("config", gpio_v2_line_config),
        ("num_lines", ctypes.c_uint32),
        ("event_buffer_size", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("fd", ctypes.c_int32),
    ]


class gpio_v2_line_info(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("offset", ctypes.c_uint32),
        ("num_attrs", ctypes.c_uint32),
        ("flags", ctypes.c_uint64),
        ("attrs", gpio_v2_line_attribute * GPIO_V2_LINE_NUM_ATTRS_MAX),
        ("padding", ctypes.c_int32 * 4),
    ]


class gpio_v2_line_info_changed(ctypes.Structure):
    _fields_ = [
        ("info", gpio_v2_line_info),
        ("timestamp_ns", ctypes.c_uint64),
        ("event_type", ctypes.c_uint32),
        ("padding", ctypes.c_int32 * 5),
    ]


class gpio_v2_line_event(ctypes.Structure):
    _fields_ = [
        ("timestamp_ns", ctypes.c_uint64),
        ("id", ctypes.c_uint32),
        ("offset", ctypes.c_uint32),
        ("seqno", ctypes.c_uint32),
        ("line_seqno", ctypes.c_uint32),
        ("padding", ctypes.c_int32 * 6),
    ]

    def __repr__(self):
        x = f"{self.__class__.__name__}<ts:{self.timestamp_ns} id:{self.id} ({GPIOEVENT_EVENT(self.id).name}) "
        x += f"offset: {self.offset}, seqno: {self.seqno}, line_seqno:{self.line_seqno}>"
        return x


# V1 enums and structs

class GPIOEVENT_REQUEST(enum.IntEnum):
    RISING_EDGE = (1 << 0)
    FALLING_EDGE = (1 << 1)
    BOTH_EDGES = (3)


class GPIOEVENT_EVENT(enum.IntEnum):
    RISING_EDGE = (1 << 0)
    FALLING_EDGE = (1 << 1)


class GPIOHANDLE_REQUEST(enum.IntEnum):
    INPUT = (1 << 0)
    OUTPUT = (1 << 1)
    ACTIVE_LOW = (1 << 2)
    OPEN_DRAIN = (1 << 3)
    OPEN_SOURCE = (1 << 4)
    BIAS_PULL_UP = (1 << 5)
    BIAS_PULL_DOWN = (1 << 6)
    BIAS_DISABLE = (1 << 7)


class GPIOLINE_FLAG(enum.IntEnum):
    KERNEL = (1 << 0)
    IS_OUT = (1 << 1)
    ACTIVE_LOW = (1 << 2)
    OPEN_DRAIN = (1 << 3)
    OPEN_SOURCE = (1 << 4)
    BIAS_PULL_UP = (1 << 5)
    BIAS_PULL_DOWN = (1 << 6)
    BIAS_DISABLE = (1 << 7)


class gpioline_info(ctypes.Structure):
    _fields_ = [
        ("line_offset", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("name", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME_SIZE),
    ]


class gpioline_info_changed(ctypes.Structure):
    _fields_ = [
        ("info", gpioline_info),
        ("timestamp", ctypes.c_uint64),
        ("event_type", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
    ]


class gpiohandle_request(ctypes.Structure):
    _fields_ = [
        ("lineoffsets", ctypes.c_uint32 * GPIOHANDLES_MAX),
        ("flags", ctypes.c_uint32),
        ("default_values", ctypes.c_uint8 * GPIOHANDLES_MAX),
        ("consumer_label", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("lines", ctypes.c_uint32),
        ("fd", ctypes.c_int),
    ]

    def __repr__(self):
        x = f"{self.__class__.__name__}<lineoffsets:{self.lineoffsets}, flags:{self.flags}, "
        x += f"defvals:{self.default_values}, consumer:{self.consumer_label}, lines:{self.lines}, "
        return x + f"fd:{self.fd}>"


class gpiohandle_config(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("default_values", ctypes.c_uint8 * GPIOHANDLES_MAX),
        ("padding", ctypes.c_uint32 * 4),
    ]


class gpiohandle_data(ctypes.Structure):
    _fields_ = [
        ("values", ctypes.c_uint8 * GPIOHANDLES_MAX),
    ]

    def __repr__(self):
        return f"{self.__class__.__name__}<values:{self.values}>"


class gpioevent_request(ctypes.Structure):
    _fields_ = [
        ("lineoffset", ctypes.c_uint32),
        ("handleflags", ctypes.c_uint32),
        ("eventflags", ctypes.c_uint32),
        ("consumer_label", ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ("fd", ctypes.c_int)
    ]


class gpioevent_data(ctypes.Structure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("id", ctypes.c_uint32)
    ]

    def __repr__(self):
        return f"{self.__class__.__name__}<ts:{self.timestamp} id:{self.id} ({GPIOEVENT_EVENT(self.id).name})>"


# TODO - group these into holder class?
GPIO_GET_LINEINFO_IOCTL = _IOWR(0xb4, 0x02, ctypes.sizeof(gpioline_info))
GPIO_GET_LINEHANDLE_IOCTL = _IOWR(0xb4, 0x03, ctypes.sizeof(gpiohandle_request))
GPIO_GET_LINEEVENT_IOCTL = _IOWR(0xb4, 0x4, ctypes.sizeof(gpioevent_request))
GPIOHANDLE_GET_LINE_VALUES_IOCTL = _IOWR(0xb4, 0x08, ctypes.sizeof(gpiohandle_data))
GPIOHANDLE_SET_LINE_VALUES_IOCTL = _IOWR(0xb4, 0x09, ctypes.sizeof(gpiohandle_data))
GPIOHANDLE_SET_CONFIG_IOCTL = _IOWR(0xb4, 0x0a, ctypes.sizeof(gpiohandle_config))
GPIO_GET_LINEINFO_WATCH_IOCTL = _IOWR(0xb4, 0x0b, ctypes.sizeof(gpioline_info))

GPIO_V2_GET_LINEINFO_IOCTL = _IOWR(0xB4, 0x05, ctypes.sizeof(gpio_v2_line_info))
GPIO_V2_GET_LINEINFO_WATCH_IOCTL = _IOWR(0xB4, 0x06, ctypes.sizeof(gpio_v2_line_info))
GPIO_V2_GET_LINE_IOCTL = _IOWR(0xB4, 0x07, ctypes.sizeof(gpio_v2_line_request))
GPIO_V2_LINE_SET_CONFIG_IOCTL = _IOWR(0xB4, 0x0D, ctypes.sizeof(gpio_v2_line_config))
GPIO_V2_LINE_GET_VALUES_IOCTL = _IOWR(0xB4, 0x0E, ctypes.sizeof(gpio_v2_line_values))
GPIO_V2_LINE_SET_VALUES_IOCTL = _IOWR(0xB4, 0x0F, ctypes.sizeof(gpio_v2_line_values))

## Now we have more user facing helpers


class MonitorRequest():
    """line monitor helper"""
    def __init__(self, chip: str, lines: typing.Iterable[int] | int,
                 rising=True, falling=False, consumer="gcdev-monitor", clock_realtime=False):
        self._fd = open(chip, "wb")
        info = gpiochip_info()
        x = fcntl.ioctl(self._fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)

        g2e_req = gpio_v2_line_request()
        try:
            for i, v in enumerate(lines):
                g2e_req.offsets[i]=v
            g2e_req.num_lines = i
        except TypeError:
            # assume single line int then...
            g2e_req.offsets[0] = lines
            g2e_req.num_lines = 1

        g2e_req.consumer = consumer.encode("utf8")
        g2l_config = gpio_v2_line_config()
        g2l_config.flags = GPIO_V2_LINE_FLAG.INPUT
        if rising:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.EDGE_RISING
        if falling:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.EDGE_FALLING
        if clock_realtime:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.EVENT_CLOCK_REALTIME
        g2e_req.config = g2l_config

        x = fcntl.ioctl(self._fd.fileno(), GPIO_V2_GET_LINE_IOCTL, g2e_req)
        assert(x == 0)
        # ok, we've made our request, we're live
        self.rfd = g2e_req.fd

    def get_fd(self):
        return self.rfd

    def get_events(self):
        """returns v2 line events"""
        ret = os.read(self.rfd, 16 * ctypes.sizeof(gpio_v2_line_event))
        # Must have gotten at least 1!
        assert(len(ret) >= ctypes.sizeof(gpio_v2_line_event))
        num_events = len(ret) // ctypes.sizeof(gpio_v2_line_event)
        return [gpio_v2_line_event.from_buffer_copy(ret, i*ctypes.sizeof(gpio_v2_line_event)) for i in range(num_events)]


class OutputRequestSingle:
    """ only supporting a single line right now """
    def __init__(self, chip: str, line, consumer="gcdev-output-req", active_low=False, pullup=False, pulldown=False):
        self._fd = open(chip, "wb")
        info = gpiochip_info()
        x = fcntl.ioctl(self._fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)

        g2e_req = gpio_v2_line_request()
        g2e_req.offsets[0] = line
        g2e_req.num_lines = 1
        self.line_count = g2e_req.num_lines # We might be clever and support more than one
        g2e_req.consumer = consumer.encode("utf8")
        g2l_config = gpio_v2_line_config()
        g2l_config.flags = GPIO_V2_LINE_FLAG.OUTPUT
        if active_low:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.ACTIVE_LOW
        if pullup:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.BIAS_PULL_UP
        if pulldown:
            g2l_config.flags |= GPIO_V2_LINE_FLAG.BIAS_PULL_DOWN
        g2e_req.config = g2l_config

        x = fcntl.ioctl(self._fd.fileno(), GPIO_V2_GET_LINE_IOCTL, g2e_req)
        assert(x == 0)
        self.rfd = g2e_req.fd

    def get(self):
        g2l_vals = gpio_v2_line_values()
        g2l_vals.mask = 0x1
        x = fcntl.ioctl(self.rfd, GPIO_V2_LINE_GET_VALUES_IOCTL, g2l_vals)
        assert(x == 0)
        vals = [g2l_vals.bits & (1<<a) > 0 for a in range(self.line_count)]
        return vals[0]

    def set(self, newval):
        g2l_vals = gpio_v2_line_values()
        g2l_vals.mask = 0x1
        if newval:
            g2l_vals.bits = 1
        else:
            g2l_vals.bits = 0
        x = fcntl.ioctl(self.rfd, GPIO_V2_LINE_SET_VALUES_IOCTL, g2l_vals)
        assert(x == 0)


def hammer_device_v1():
    with open("/dev/gpiochip0", "wb") as fd:
        info = gpiochip_info()
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)
        print(f"working with chip: {info.name} label: {info.label} with {info.lines} lines")

        gh_req = gpiohandle_request()
        gh_req.lineoffsets[0] = 140  # rs485 power as well please
        gh_req.lineoffsets[1] = 20  # digital 0
        gh_req.lineoffsets[2] = 21  # digital 1
        gh_req.lines = 3
        gh_req.consumer_label = b"lolicat-hammer"
        gh_req.flags = GPIOHANDLE_REQUEST.OUTPUT
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_LINEHANDLE_IOCTL, gh_req)
        assert (x == 0)
        print(f"Got a line req: {gh_req}")
        # this new fd scopes our request
        rfd = gh_req.fd

        data = gpiohandle_data()
        x = fcntl.ioctl(rfd, GPIOHANDLE_GET_LINE_VALUES_IOCTL, data)
        assert (x == 0)
        print(f"get values returned: ", [data.values[i] for i in range(gh_req.lines)])

        i = 0
        while True:
            i += 1
            data.values[0] = 1
            data.values[1] = i % 2
            data.values[2] = i % 2

            x = fcntl.ioctl(rfd, GPIOHANDLE_SET_LINE_VALUES_IOCTL, data)
            print(f"set returned ", [data.values[i] for i in range(gh_req.lines)])
            time.sleep(0.5)
            # apparently, re-read to get them back...
            x = fcntl.ioctl(rfd, GPIOHANDLE_GET_LINE_VALUES_IOCTL, data)
            print(f"get values returned: ", [data.values[i] for i in range(gh_req.lines)])


def hammer_device_v2():
    with open("/dev/gpiochip0", "wb") as fd:
        info = gpiochip_info()
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)
        print(f"working with chip: {info.name} label: {info.label} with {info.lines} lines")

        g2e_req = gpio_v2_line_request()
        g2e_req.offsets[0] = 140
        g2e_req.offsets[1] = 20
        g2e_req.offsets[2] = 21
        g2e_req.num_lines = 3
        g2e_req.consumer = b"lol-v2-hammer"
        g2l_config = gpio_v2_line_config()
        g2l_config.flags = GPIO_V2_LINE_FLAG.OUTPUT
        g2e_req.config = g2l_config

        x = fcntl.ioctl(fd.fileno(), GPIO_V2_GET_LINE_IOCTL, g2e_req)
        assert(x == 0)
        print(f"Opened an request, line: {g2e_req.offsets[0]}, got fd: {g2e_req.fd}")

        g2l_vals = gpio_v2_line_values()
        g2l_vals.mask = 0x7 # manually assemble three bits
        x = fcntl.ioctl(g2e_req.fd, GPIO_V2_LINE_GET_VALUES_IOCTL, g2l_vals)
        assert(x == 0)

        print("initial values = ", g2l_vals, [g2l_vals.bits & (1<<a) > 0 for a in range(g2e_req.num_lines)])

        i = 0
        while True:
            i += 1
            g2l_vals.bits = (1 << 0) | ((i % 2) << 1) | ((i + 1 % 2) << 2)
            x = fcntl.ioctl(g2e_req.fd, GPIO_V2_LINE_SET_VALUES_IOCTL, g2l_vals)
            assert(x == 0)
            print(f"set returned: ", g2l_vals, [g2l_vals.bits & (1<<a) > 0 for a in range(g2e_req.num_lines)])
            x = fcntl.ioctl(g2e_req.fd, GPIO_V2_LINE_GET_VALUES_IOCTL, g2l_vals)
            assert(x == 0)
            print("GET returned = ", g2l_vals, [g2l_vals.bits & (1<<a) > 0 for a in range(g2e_req.num_lines)])
            time.sleep(0.3)



def monitor_device_v1():
    with open("/dev/gpiochip1", "wb") as fd:
        info = gpiochip_info()
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)
        print(f"working with chip: {info.name} label: {info.label} with {info.lines} lines")

        ge_req = gpioevent_request()
        ge_req.lineoffset = 11
        ge_req.handleflags = 0
        # ge_req.eventflags = GPIOEVENT_REQUEST.BOTH_EDGES  ## testing first
        ge_req.eventflags = GPIOEVENT_REQUEST.RISING_EDGE
        ge_req.consumer_label = b"lolicat-monitor"

        x = fcntl.ioctl(fd.fileno(), GPIO_GET_LINEEVENT_IOCTL, ge_req)
        assert (x == 0)
        print(f"Opened an event request, line: {ge_req.lineoffset}, got fd: {ge_req.fd}")

        while True:
            ret = os.read(ge_req.fd, ctypes.sizeof(gpioevent_data))
            ev = gpioevent_data.from_buffer_copy(ret)
            print(f"which converts to ", ev)


def monitor_device_v2():
    with open("/dev/gpiochip1", "wb") as fd:
        info = gpiochip_info()
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)
        print(f"working with chip: {info.name} label: {info.label} with {info.lines} lines")

        g2e_req = gpio_v2_line_request()
        g2e_req.offsets[0] = 11
        g2e_req.num_lines = 1
        g2e_req.consumer = b"lol-v2-monitor"
        g2l_config = gpio_v2_line_config()
        g2l_config.flags = GPIO_V2_LINE_FLAG.INPUT | GPIO_V2_LINE_FLAG.EDGE_RISING #| GPIO_V2_LINE_FLAG.EDGE_FALLING
        g2e_req.config = g2l_config

        x = fcntl.ioctl(fd.fileno(), GPIO_V2_GET_LINE_IOCTL, g2e_req)
        assert(x == 0)
        print(f"Opened an event request, line: {g2e_req.offsets[0]}, got fd: {g2e_req.fd} ev buf: {g2e_req.event_buffer_size}")

        def handle_zx(fd):
            # Attempt to read entire kfifo, at most 16 entries.
            ret = os.read(fd, 16 * ctypes.sizeof(gpio_v2_line_event))
            print("read ", len(ret))
            # Must have gotten at least 1!
            assert(len(ret) >= ctypes.sizeof(gpio_v2_line_event))
            num_events = len(ret) // ctypes.sizeof(gpio_v2_line_event)
            for i in range(num_events):
                ev = gpio_v2_line_event.from_buffer_copy(ret, i*ctypes.sizeof(gpio_v2_line_event))
                print(f"zxi: {i} -> which converts to {ev}")

        sel = selectors.DefaultSelector()
        sel.register(g2e_req.fd, selectors.EVENT_READ, handle_zx)
        while True:
            time.sleep(0.10) # If you make this too big, you'll start seeing gaps in your sequence numbers received
            events = sel.select(0)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)



def monitor_helper_async():
    import asyncio
    r = MonitorRequest("/dev/gpiochip1", 11, consumer="hohokarl", clock_realtime=True)

    def handle_zx():
        evs = r.get_events()
        [print(e) for e in evs]

    async def inner():
        fd_gpio = r.get_fd()
        asyncio.get_running_loop().add_reader(fd_gpio, handle_zx)

        never = asyncio.Event()
        await never.wait()

    asyncio.run(inner())

def hammer_abstract():

    g1 = OutputRequestSingle("/dev/gpiochip0", 140, consumer="blah1")
    g2 = OutputRequestSingle("/dev/gpiochip0", 20, consumer="blahdigital20")
    g3 = OutputRequestSingle("/dev/gpiochip0", 21, consumer="kdigital21")

    g1.set(True)
    while True:
        x = g2.get()
        g2.set(not x)
        x = g3.get()
        g3.set(not x)
        time.sleep(0.3)



def main():
    with open("/dev/gpiochip1", "wb") as fd:
        info = gpiochip_info()
        x = fcntl.ioctl(fd.fileno(), GPIO_GET_CHIPINFO_IOCTL, info)
        assert (x == 0)
        print(f"working with chip: {info.name} label: {info.label} with {info.lines} lines")


if __name__ == "__main__":
    # hammer_device_v1()
    #hammer_device_v2()
    #monitor_device_v1()
    #monitor_device_v2()
    monitor_helper_async()
    #hammer_abstract()
    # main()
