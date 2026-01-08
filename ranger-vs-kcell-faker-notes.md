# Quick comparison
This is quick scribble based on using (at the moment) my ads1263 waveshare board and spidev code
Hardware tested:
* Rice Lake Ranger5
* Kcell Faker 2ch version.

# Summary
It's about 3 times lower noise? is that it?

# Details


KARL:; you need to be careful comparing raw sigma numbers, they are only meaningful when the means are the same

| hw | mode | mean | sigma | sigma/mean |
|------------------ ---| ---- |----- |------|-------- |
| ranger5 0.5mv/V| Idac-3mA | 34314700 | 2200| 7e-5
| ranger5 1mv/V| Idac-3mA | 68656700 | 2000| 3e-5
| ranger5 1mv/V| Idac-3mA | 68676500 | 2300| 3.3e-5
| ranger5 1.5mv/V| Idac-3mA | 1.02992e8 | 2600| 2.3e-5
| ranger5 2mv/V| Idac-3mA | 1.37354e8 | 2800| 1.5e-5
| ranger5 3mv/V| Idac-3mA | unstable!
| ranger5 4.5mv/V| Idac-3mA | 3.090517e8 | 2600 | 9e-6
| kc-calmode low  | idac-3mA | 2022000 | 15000 | 0.0072
| kc-calmode high | idac-3mA | 2194000 | 14000 | 0.0072
| ranger5 0.5mV/V | 5V exc | 34332500   | 1500 | 4.7e-5
| ranger5 1mV/V   | 5V exc | 68672900   | 1600 | 2.3e-5
| ranger5 1.5mV/V | 5V exc | 1.030144e8 | 1500 | 1.4e-5
| ranger5 2.0mv/V | 5V exc | 1.373556e8 | 1800 | 1.3e-5
| ranger5 2.5mv/V | 5V exc | 1.716960e8 | 1600 | 0.9e-5
| ranger5 3.0mv/V | 5V exc | 2.060120e8 | 1700 | 0.9e-5
| ranger5 4.5mV/V | 5V exc | 3.090598e8 | 1600 | 0.5e-5
| kc-calmode low  | 5V exc | 99567000   | 4000 | 3e-5
| kc-calmode high | 5V exc | 67608000   | 3700 | 4.5e-5

## another night.  these are almost the same.
| pj05-2.5mv out    | 5V exc | 69412719 | 5500 | 8.0e-5
| ranger5 2.5mV out | 5V exc | 69267280 | 5500 | 8.0e-5


# rice lake ranger5

It doesn't seem very happy with idac mode, but then again, neither are we :)


# in millivolts (measureing flatness here really, not anything else)
| hw                      | mean mV  | sigma mV  | sigma/mean |
|-------------------------| -------- |---------- |------------|
| 1263-pj06 1mV/V/50%     | 2.5049  | 5.5e-5 mV | 2.3e-5 | 
| 1263-ranger5 0.5mV/V    | 2.4995  | 5.5e-5 mV | 2.3e-5 | ~close enough I can't really say one is any better than the other...
| 124s08-pj06 2.5mV ChA   | 2.5033  | ~10e-5 mV | ~4e-5  | 
| 124s08-pj06 2.5mV ChB   | 2.5043  | ~10e-5 mV | ~4e-5  | 
| 124s08-ranger5 0.5mV/V  | 2.4998  | ~10e-5 mV | ~4e-5  | ~close enough I can't really say one is any better than the other...
| 124s08-kcellfaker2 ChB  | 4.933  | ~14e-5 mV | ~4e-5  | 
