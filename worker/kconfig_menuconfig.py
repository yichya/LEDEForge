# coding=utf8
import os
import sys
import faulthandler
from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, Choice, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value
from kconfig.menuconfig import menuconfig


if __name__ == "__main__":
    sys.setrecursionlimit(1000000)
    faulthandler.enable()
    os.chdir("/mnt/hdd/openwrt")
    # Load Kconfig configuration files
    kconf = Kconfig("Config.in")
    kconf.load_config(".config")
    menuconfig(kconf)
