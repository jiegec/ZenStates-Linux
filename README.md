# ZenStates-Linux
Collection of utilities for Ryzen processors and motherboards

## zenstates.py
Dynamically edit AMD Ryzen processor P-States

Requires root access and the msr kernel module loaded (just run "modprobe msr" as root).

    usage: zenstates.py [-h] [-l] [-p {0,1,2,3,4,5,6,7}] [--enable] [--disable]
                        [-f FID] [-d DID] [-v VID] [--c6-enable] [--c6-disable]
                        [--cpb-enable] [--cpb-disable]
    
    Sets P-States for Ryzen processors
    
    options:
      -h, --help            show this help message and exit
      -l, --list            List all P-States
      -p {0,1,2,3,4,5,6,7}, --pstate {0,1,2,3,4,5,6,7}
                            P-State to set
      --enable              Enable P-State
      --disable             Disable P-State
      -f FID, --fid FID     FID to set (in hex)
      -d DID, --did DID     DID to set (in hex)
      -v VID, --vid VID     VID to set (in hex)
      --c6-enable           Enable C-State C6
      --c6-disable          Disable C-State C6
      --cpb-enable          Enable Core Performance Boost
      --cpb-disable         Disable Core Performance Boost

Example for frequency set and pin:

```shell
# on AMD EPYC 7551
# current frequency: 2500MHz -> 2000MHz
$ sudo ./zenstates.py --cpb-disable

# set frequency to 1900MHz
$ sudo ./zenstates.py -l
P0 - Enabled - FID = 64 - DID = A - VID = 5E - Freq = 2000.00 MHz - vCore = 0.96250
P1 - Enabled - FID = 60 - DID = C - VID = 63 - Freq = 1600.00 MHz - vCore = 0.93125
P2 - Enabled - FID = 60 - DID = 10 - VID = 69 - Freq = 1200.00 MHz - vCore = 0.89375
$ sudo ./zenstates.py -p 0 --fid 5f
Current P0: Enabled - FID = 64 - DID = A - VID = 5E - Freq = 2000.00 MHz - vCore = 0.96250
Setting FID to 5F
New P0: Enabled - FID = 5F - DID = A - VID = 5E - Freq = 1900.00 MHz - vCore = 0.96250

# on AMD Ryzen 9 9950X
# current frequency: 5700MHz -> 4300MHz
$ sudo ./zenstates.py --cpb-disable

# set frequency to 4200MHz
$ sudo ./zenstates.py -l
P0 - Enabled - FID = 35C - VID = C9 - Freq = 4300.00
$ sudo ./zenstates.py -p 0 --fid 348
Current P0: Enabled - FID = 35C - VID = C9 - Freq = 4300.00
Setting FID to 348
New P0: Enabled - FID = 348 - VID = C9 - Freq = 4200.00
```
