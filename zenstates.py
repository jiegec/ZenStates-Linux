#!/usr/bin/env python3
import struct
import os
import glob
import argparse
from contextlib import contextmanager

# MSRC001_0064 [P-state [7:0]] (PStateDef)
pstates = range(0xC0010064, 0xC001006C)

# read cpu family
cpu_family = None
with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
    for line in f:
        if "cpu family" in line:
            cpu_family = int(line.strip().split()[-1])


def writemsr(msr, val, cpu=-1):
    try:
        if cpu == -1:
            for c in glob.glob("/dev/cpu/[0-9]*/msr"):
                f = os.open(c, os.O_WRONLY)
                os.lseek(f, msr, os.SEEK_SET)
                os.write(f, struct.pack("Q", val))
                os.close(f)
        else:
            f = os.open("/dev/cpu/%d/msr" % (cpu), os.O_WRONLY)
            os.lseek(f, msr, os.SEEK_SET)
            os.write(f, struct.pack("Q", val))
            os.close(f)
    except PermissionError:
        raise RuntimeError("Permission denied (try running as root)")
    except FileNotFoundError as e:
        raise OSError("msr module not loaded (run modprobe msr)") from e


def readmsr(msr, cpu=0):
    try:
        f = os.open("/dev/cpu/%d/msr" % cpu, os.O_RDONLY)
        os.lseek(f, msr, os.SEEK_SET)
        val = struct.unpack("Q", os.read(f, 8))[0]
        os.close(f)
        return val
    except PermissionError:
        raise RuntimeError("Permission denied (try running as root)")
    except FileNotFoundError as e:
        raise OSError("msr module not loaded (run modprobe msr)") from e


def pstate2str(val):
    # Bits[63]: PstateEn
    if val & (1 << 63):
        # ref: https://github.com/torvalds/linux/blob/c2ee9f594da826bea183ed14f2cc029c719bf4da/tools/power/cpupower/utils/helpers/amd.c#L75
        # Family 1Ah
        if cpu_family == 26:
            # Bits[11:0]: CpuFid[11:0]: core frequency ID
            # Value: FFFh-010h
            # Description: <Value>*5
            fid = val & 0xFFF
            freq = 5 * fid
            # Bits[32]: CpuVid[8]: core VID[8]
            # Bits[21:14]: CpuVid[7:0]: core VID[7:0]
            vid = (val & 0x3FC000) >> 14
            vid |= (val & 0x100000000) >> 24
            return "Enabled - FID = %X - VID = %X - Freq = %.2f MHz" % (fid, vid, freq)
        else:
            # Bits[7:0]: CpuFid[7:0]: core frequency ID
            # Value: FFh-10h
            # Description: <Value>*25
            fid = val & 0xFF
            # Bits[13:8]: CpuDfsId: core divisor ID
            did = (val & 0x3F00) >> 8
            # Bits[21:14]: CpuVid[7:0]: core VID
            vid = (val & 0x3FC000) >> 14
            # VCO/<Value/8>
            # FIXME: Handle VCO/1 and VCO/1.125 special cases
            # Base frequency = 100MHz
            freq = 100 * 25 * fid / (12.5 * did)
            # FIXME: Source?
            vcore = 1.55 - 0.00625 * vid
            return (
                "Enabled - FID = %X - DID = %X - VID = %X - Freq = %.2f MHz - vCore = %.5f"
                % (fid, did, vid, freq, vcore)
            )
    else:
        return "Disabled"


def setbits(val, base, length, new):
    return (val ^ (val & ((2**length - 1) << base))) + (new << base)


def setfid(val, new):
    if cpu_family == 26:
        # Bits[11:0]: CpuFid[11:0]: core frequency ID
        return setbits(val, 0, 12, new)
    else:
        # Bits[7:0]: CpuFid[7:0]: core frequency ID
        return setbits(val, 0, 8, new)


def setdid(val, new):
    if cpu_family == 26:
        print("Not supported on family 1Ah")
        return val
    else:
        # Bits[13:8]: CpuDfsId: core divisor ID
        return setbits(val, 8, 6, new)


def setvid(val, new):
    if cpu_family == 26:
        # Bits[32]: CpuVid[8]: core VID[8]
        # Bits[21:14]: CpuVid[7:0]: core VID[7:0]
        val = setbits(val, 14, 8, new & 0xFF)
        return setbits(val, 32, 1, new >> 8)
    else:
        # Bits[21:14]: CpuVid[7:0]: core VID
        return setbits(val, 14, 8, new)


def hex(x):
    return int(x, 16)


parser = argparse.ArgumentParser(description="Sets P-States for Ryzen processors")
parser.add_argument("-l", "--list", action="store_true", help="List all P-States")
parser.add_argument(
    "-p", "--pstate", default=-1, type=int, choices=range(8), help="P-State to set"
)
parser.add_argument("--enable", action="store_true", help="Enable P-State")
parser.add_argument("--disable", action="store_true", help="Disable P-State")
parser.add_argument("-f", "--fid", default=-1, type=hex, help="FID to set (in hex)")
parser.add_argument("-d", "--did", default=-1, type=hex, help="DID to set (in hex)")
parser.add_argument("-v", "--vid", default=-1, type=hex, help="VID to set (in hex)")
parser.add_argument("--c6-enable", action="store_true", help="Enable C-State C6")
parser.add_argument("--c6-disable", action="store_true", help="Disable C-State C6")
parser.add_argument(
    "--cpb-enable", action="store_true", help="Enable Core Performance Boost"
)
parser.add_argument(
    "--cpb-disable", action="store_true", help="Disable Core Performance Boost"
)

args = parser.parse_args()


@contextmanager
def optional_feature(name):
    try:
        yield
    except OSError as e:
        print("Optional feature %s not available: %s" % (name, e))


if args.list:
    for p in range(len(pstates)):
        print("P" + str(p) + " - " + pstate2str(readmsr(pstates[p])))
    # FIXME: Source?
    print(
        "C6 State - Package - "
        + ("Enabled" if readmsr(0xC0010292) & (1 << 32) else "Disabled")
    )
    print(
        "C6 State - Core - "
        + (
            "Enabled"
            if readmsr(0xC0010296) & ((1 << 22) | (1 << 14) | (1 << 6))
            == ((1 << 22) | (1 << 14) | (1 << 6))
            else "Disabled"
        )
    )

    # MSRC001_0015 [Hardware Configuration] (HWCR)
    # Bits[25]: CpbDis: core performance boost disable. Read-write. Reset: 0. 0=CPB is
    # requested to be enabled.  1=CPB is disabled. Specifies whether core
    # performance boost is requested to be enabled or disabled. If core
    # performance boost is disabled while a core is in a boosted P-state, the
    # core automatically transitions to the highest performance non-boosted
    # P-state.
    print(
        "Core Performance Boost - "
        + ("Disabled" if readmsr(0xC0010015) & (1 << 25) else "Enabled")
    )

    # MSRC001_02B1 [CPPC Enable] (Core::X86::Msr::CppcEnable)
    with optional_feature("CPPC Enable"):
        print("CPPC - " + ("Enabled" if readmsr(0xC00102B1) & (1 << 0) else "Disable"))

    # MSRC001_02B0 [CPPC Capability 1] (Core::X86::Msr::CppcCapability1)
    with optional_feature("CPPC Highest Perf"):
        cppc_cap1 = readmsr(0xC00102B0)
        print(
            "CPPC Highest Perf = %d - Nominal Perf = %d - Lowest Nonlinear Perf = %d - Lowest Perf = %d"
            % (
                (cppc_cap1 >> 24) & 0xFF,
                (cppc_cap1 >> 16) & 0xFF,
                (cppc_cap1 >> 8) & 0xFF,
                cppc_cap1 & 0xFF,
            )
        )

    # MSRC001_02B2 [CPPC Capability 2] (Core::X86::Msr::CppcCapability2)
    with optional_feature("CPPC Guaranteed Perf"):
        cppc_cap2 = readmsr(0xC00102B2)
        print("CPPC Guaranteed Perf = %d" % (cppc_cap2 & 0xFF,))

    # MSRC001_02B3 [CPPC Request] (Core::X86::Msr::CppcRequest)
    with optional_feature("CPPC EPP"):
        cppc_req = readmsr(0xC00102B3)
        print(
            "CPPC EPP = %d - Desired Perf = %d - Min Perf = %d - Max Perf = %d"
            % (
                (cppc_req >> 24) & 0xFF,
                (cppc_req >> 16) & 0xFF,
                (cppc_req >> 8) & 0xFF,
                cppc_req & 0xFF,
            )
        )

if args.pstate >= 0:
    new = old = readmsr(pstates[args.pstate])
    print("Current P" + str(args.pstate) + ": " + pstate2str(old))
    if args.enable:
        new = setbits(new, 63, 1, 1)
        print("Enabling state")
    if args.disable:
        new = setbits(new, 63, 1, 0)
        print("Disabling state")
    if args.fid >= 0:
        new = setfid(new, args.fid)
        print("Setting FID to %X" % args.fid)
    if args.did >= 0:
        new = setdid(new, args.did)
        print("Setting DID to %X" % args.did)
    if args.vid >= 0:
        new = setvid(new, args.vid)
        print("Setting VID to %X" % args.vid)
    if new != old:
        # Bits[21]: LockTscToCurrentP0: lock the TSC to the current P0
        # frequency. Read-write. Reset: 0. 0=The TSC will count at the P0
        # frequency. 1=The TSC frequency is locked to the current P0 frequency
        # at the time this bit is set and remains fixed regardless of future
        # changes to the P0 frequency.
        if not (readmsr(0xC0010015) & (1 << 21)):
            print("Locking TSC frequency")
            for c in range(len(glob.glob("/dev/cpu/[0-9]*/msr"))):
                writemsr(0xC0010015, readmsr(0xC0010015, c) | (1 << 21), c)
        print("New P" + str(args.pstate) + ": " + pstate2str(new))
        writemsr(pstates[args.pstate], new)

# FIXME: Source?
if args.c6_enable:
    writemsr(0xC0010292, readmsr(0xC0010292) | (1 << 32))
    writemsr(0xC0010296, readmsr(0xC0010296) | ((1 << 22) | (1 << 14) | (1 << 6)))
    print("Enabling C6 state")

if args.c6_disable:
    writemsr(0xC0010292, readmsr(0xC0010292) & ~(1 << 32))
    writemsr(0xC0010296, readmsr(0xC0010296) & ~((1 << 22) | (1 << 14) | (1 << 6)))
    print("Disabling C6 state")

if args.cpb_enable:
    writemsr(0xC0010015, readmsr(0xC0010015) & ~(1 << 25))
    print("Enabling core performance boost")

if args.cpb_disable:
    writemsr(0xC0010015, readmsr(0xC0010015) | (1 << 25))
    print("Disabling core performance boost")

if (
    not args.list
    and args.pstate == -1
    and not args.c6_enable
    and not args.c6_disable
    and not args.cpb_enable
    and not args.cpb_disable
):
    parser.print_help()
