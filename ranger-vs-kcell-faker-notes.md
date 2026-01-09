# Quick comparison
This is quick scribble based on using (at the moment) my ads1263 waveshare board and spidev code
Hardware tested:
* Rice Lake Ranger5
* Kcell Faker 2ch version.

# Summary
It's about 3 times lower noise? is that it?

# Details


KARL:; you need to be careful comparing raw sigma numbers, they are only meaningful when the means are the same

| hw              | mode     | mean        | sigma |
|-----------------| ---------|-------------|-------|
| ranger5 0.5mv/V | Idac-3mA | 34314700    | 2200  |
| ranger5 1mv/V   | Idac-3mA | 68656700    | 2000  |
| ranger5 1mv/V   | Idac-3mA | 68676500    | 2300  |
| ranger5 1.5mv/V | Idac-3mA | 1.02992e8   | 2600  |
| ranger5 2mv/V   | Idac-3mA | 1.37354e8   | 2800  |
| ranger5 3mv/V   | Idac-3mA | unstable!   | na    |
| ranger5 4.5mv/V | Idac-3mA | 3.090517e8  | 2600  |
| kc-calmode low  | idac-3mA | 2022000     | 15000 |
| kc-calmode high | idac-3mA | 2194000     | 14000 |
| ranger5 0.5mV/V | 5V exc   | 34332500    | 1500  |
| ranger5 1mV/V   | 5V exc   | 68672900    | 1600  |
| ranger5 1.5mV/V | 5V exc   | 1.030144e8  | 1500  |
| ranger5 2.0mv/V | 5V exc   | 1.373556e8  | 1800  |
| ranger5 2.5mv/V | 5V exc   | 1.716960e8  | 1600  |
| ranger5 3.0mv/V | 5V exc   | 2.060120e8  | 1700  |
| ranger5 4.5mV/V | 5V exc   | 3.090598e8  | 1600  |
| kc-calmode low  | 5V exc   | 99567000    | 4000  |
| kc-calmode high | 5V exc   | 67608000    | 3700  |
| pj05-2.5mv out  | 5V exc   | 69412719    | 5500  |
| ranger5 2.5mV   | 5V exc   | 69267280    | 5500  |


# rice lake ranger5

It doesn't seem very happy with idac mode, but then again, neither are we :)


# in millivolts (measureing flatness here really, not anything else)
| hw                      | mean mV  | sigma mV  |
|-------------------------| -------- |---------- |
| 1263-pj06 1mV/V/50%     | 2.5049  | 5.5e-5 mV | 
| 1263-ranger5 0.5mV/V    | 2.4995  | 5.5e-5 mV |  ~close enough I can't really say one is any better than the other...
| 124s08-pj06 2.5mV ChA   | 2.5033  | ~10e-5 mV | 
| 124s08-pj06 2.5mV ChB   | 2.5043  | ~10e-5 mV | 
| 124s08-ranger5 0.5mV/V  | 2.4998  | ~10e-5 mV |  ~close enough I can't really say one is any better than the other...
| 124s08-kcellfaker2 ChB  | 4.933   | ~14e-5 mV | todo, do that on the ads1263 too, but also, can't compare sigmas frrom diffrent means!


# ok, tracking sigma vs adc count...  (this is eyeballed the running mean/sigma of the last 200 samples at  ~30hz)
Ok, it's looking more ok then...

|     adc          | source     | mean mV  | sigma mV |
|------------------|------------|----------|----------|
| ads124s08 chA    | faker2     | 7.257 mV | 12e-5 mV |
| ads124s08 chA    | faker2     | 6.559 mV | 16e-5 mV |
| ads124s08 chA    | faker2     | 5.745 mV | 17e-5 mV |
| ads124s08 chA    | faker2     | 5.046 mV | 17e-5 mV |
| ads124s08 chA    | faker2     | 3.575 mV | 14e-5 mV |
| ads124s08 chA    | faker2     | 3.153 mV | 12e-5 mV |
| ads124s08 chA    | pj06-1-100 | 5.007 mV | 10e-5 mV |
| ads124s08 chA    | pj06-1-80  | 4.006 mV | 9.5e-5 mV |
| ads124s08 chA    | pj06-1-50  | 2.504 mV | 11e-5 mV |
| ads124s08 chA    | pj06-1-20  | 1.001 mV | 10e-5 mV |
| ads124s08 chA    | rang5-0.5  | 2.498 mV | 10e-5 mV |
| ads124s08 chA    | rang5-1.0  | 4.997 mV | 10e-5 mV |
| ads124s08 chA    | rang5-1.5  | 7.496 mV | 10e-5 mV |
| wv-1263          | rang5-0.5  | 2.500 mV | 6e-5 mV | these are all 6.x, but it does swing a bit.
| wv-1263          | rang5-1.0  | 4.998 mV | 6e-5 mV |
| wv-1263          | rang5-1.5  | 7.497 mV | 6e-5 mV |
| wv-1263          | pj06-1-100 | 5.008 mV | 5e-5 mV |  thse are all ~5.x
| wv-1263          | pj06-1-80  | 4.006 mV | 5e-5 mV |
| wv-1263          | pj06-1-50  | 2.504 mV | 5e-5 mV |
| wv-1263          | pj06-1-20  | 1.003 mV | 5e-5 mV |
| wv-1263          | faker2     | 7.245 mV | 10e-5 mV |
| wv-1263          | faker2     | 6.548 mV | 10e-5 mV |
| wv-1263          | faker2     | 5.793 mV | 11e-5 mV |
| wv-1263          | faker2     | 4.978 mV | 10e-5 mV |
| wv-1263          | faker2     | 3.507 mV | 10e-5 mV |
| wv-1263          | faker2     | 3.145 mV | 10e-5 mV |



# Alternate 6000 samples instead of 200
Note these are in MICOO VOLTS

This is 3 minutes, so you can see in the screencaps that it has 1/f wobble, but we still get very flat readings.

|     adc          | source     | mean uV  | sigma uV |
|------------------|------------|----------|----------|
| ads124s08 chA    | pj06-1-50  | 2504.02 uV | 0.105 uV |
| ads124s08 chA    | rang5-0.5  | 2499.70 uV | 0.105 uV |  As before, these are ~indistinguishable
| ads124s08 chA    | faker2     | 4931.1 uV | 0.188 uV |  
| ads124s08 chB    | pj06-1-50  | 2504.98 uV | 0.111 uV | ? is this statistically significant?  6 nano volts higher sigma?
| ads124s08 chA    | faker2     | 4934.26 uV | 0.162 uV | ? this improved by ~19nV? is that better? really?