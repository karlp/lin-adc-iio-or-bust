#!python3
"""
hack reading hx711 m5 kit shit
"""
import machine


pout = machine.Pin(machine.Pin.board.PWM4, machine.Pin.IN, pull=machine.Pin.PULL_DOWN)
psck = machine.Pin(machine.Pin.board.PWM5, machine.Pin.OUT)

import hx71x
import hx710_gpio


hxc = hx710_gpio.HX71X_IO(psck, pout)
hx71x = hx71x.HX71X(hxc)


