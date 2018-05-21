# coding=utf8
import os
import sys
import faulthandler
from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, Choice, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value
from kconfig.menuconfig import menuconfig

if __name__ == "__main__":
    sys.setrecursionlimit(1000000)
    faulthandler.enable()
    os.chdir("/mnt/hdd/openwrt/build_dir/target-mips_24kc_musl/linux-ar71xx_tiny/linux-4.9.100")
    # Load Kconfig configuration files
    kconf = Kconfig("Kconfig")
    kconf.load_config(".config")
    menuconfig(kconf)
