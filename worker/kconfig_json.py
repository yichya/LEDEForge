# coding=utf8
import os
import sys
import faulthandler
from pprint import pprint

from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value


# Add help description to output
WITH_HELP_DESC = False


def value_str(sc):
    result = {"type": sc.type}

    if sc.type in (STRING, INT, HEX):
        result['value'] = sc.str_value
        return result

    if isinstance(sc, Symbol) and sc.choice and sc.visibility == 2:
        result['value'] = {
            'selected': sc.choice.selection is sc
        }
        return result

    tri_val_str = sc.tri_value

    if len(sc.assignable) == 1:
        result['value'] = {
            'assignable': sc.assignable,
            'value': tri_val_str
        }
        return result

    if sc.type == BOOL:
        result['value'] = {
            'value': tri_val_str
        }
        return result

    if sc.type == TRISTATE:
        result['value'] = {
            'assignable': sc.assignable,
            'value': tri_val_str
        }
        return result


def serialize_node(node):
    if node.item == UNKNOWN:
        return {}

    if not node.prompt:
        return {}

    prompt, prompt_cond = node.prompt
    result = {
        'prompt': prompt,
        'prompt_cond': expr_value(prompt_cond),
        'choices': False
    }
    if node.item in [MENU, COMMENT]:
        result.update({
            'item': node.item,
        })
    else:
        sc = node.item
        result.update({
            'name': sc.name,
            'type': sc.type,
            'help': node.help,
            'value': value_str(sc)
        })
    if node.list:
        result['choices'] = True
        result['list'] = get_menuconfig_nodes(node.list)
    return result


def get_menuconfig_nodes(node):
    nodes = []
    while node:
        node_dict = serialize_node(node)
        if node_dict:
            nodes.append(node_dict)
        node = node.next
    return nodes


def print_menuconfig(kconf):
    """
    Prints all menu entries for the configuration.
    """
    # Print the expanded mainmenu text at the top. This is the same as
    # kconf.top_node.prompt[0], but with variable references expanded.
    print("\n======== {} ========\n".format(kconf.mainmenu_text))

    result = get_menuconfig_nodes(kconf.top_node.list)
    pprint(result)
    print("")


if __name__ == "__main__":
    sys.setrecursionlimit(1000000)
    faulthandler.enable()
    os.chdir("/mnt/hdd/openwrt")
    # Load Kconfig configuration files
    kconf = Kconfig("Config.in")
    kconf.load_config(".config")
    print_menuconfig(kconf)
