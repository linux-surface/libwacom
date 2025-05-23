#!/usr/bin/env python3
#
# Run with pytest

import configparser
import os
import re
from pathlib import Path


WACOM_RECEIVER_USBIDS = [
    (0x56A, 0x84),
]


def datadir():
    return Path(os.getenv("MESON_SOURCE_ROOT") or ".") / "data"


def layoutsdir():
    return datadir() / "layouts"


def pytest_generate_tests(metafunc):
    # for any function that takes a "tabletfile" argument return the path to
    # a tablet file
    if "tabletfile" in metafunc.fixturenames:
        files = [f for f in datadir().glob("*.tablet")]
        metafunc.parametrize("tabletfile", files, ids=[f.name for f in files])


def test_device_match(tabletfile):
    config = configparser.ConfigParser()
    config.read(tabletfile)

    # Match format must be bus:vid:pid:name
    # where bus is 'usb' or 'bluetooth'
    # where vid/pid is a lowercase hex
    # where name is optional
    for match in config["Device"]["DeviceMatch"].split(";"):
        if not match or match == "generic":
            continue

        bus, vid, pid = match.split("|")[:3]  # skip the name part of the match
        assert bus in [
            "usb",
            "bluetooth",
            "i2c",
            "serial",
            "virt",
            "mei",
        ], f"{tabletfile}: unknown bus type"
        assert re.match("[0-9a-f]{4}", vid), (
            f"{tabletfile}: {vid} must be lowercase hex"
        )
        assert re.match("[0-9a-f]{4}", pid), (
            f"{tabletfile}: {pid} must be lowercase hex"
        )


def test_no_receiver_id(tabletfile):
    config = configparser.ConfigParser(strict=True)
    # Don't convert to lowercase
    config.optionxform = lambda option: option
    config.read(tabletfile)

    receivers = ["usb|{:04x}|{:04x}".format(*r) for r in WACOM_RECEIVER_USBIDS]
    for match in config["Device"]["DeviceMatch"].split(";"):
        assert match not in receivers


def test_svg_exists(tabletfile):
    config = configparser.ConfigParser(strict=True)
    # Don't convert to lowercase
    config.optionxform = lambda option: option
    config.read(tabletfile)

    try:
        svg = config["Device"]["Layout"]
        assert svg != "", "Empty Layout= line not permitted"
        assert (layoutsdir() / svg).exists()

    except KeyError:
        pass


def test_button_evcodes(tabletfile):
    config = configparser.ConfigParser(strict=True)
    # Don't convert to lowercase
    config.optionxform = lambda option: option
    config.read(tabletfile)

    try:
        nbuttons = 0
        for where in ["Top", "Bottom", "Left", "Right"]:
            try:
                buttons = config["Buttons"][where]
                nbuttons += len([s for s in buttons.split(";") if s])
            except KeyError:
                pass
        str = config["Buttons"]["EvdevCodes"]
        codes = [
            c for c in str.split(";") if c
        ]  # drop empty strings from trailing semicolons
        assert len(codes) == nbuttons, "Number of buttons mismatches the EvdevCodes"
    except KeyError:
        pass
