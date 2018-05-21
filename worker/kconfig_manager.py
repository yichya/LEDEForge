# coding=utf8
import os
import sys
import faulthandler
from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, Choice, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, \
    expr_value


# Add help description to output
WITH_HELP_DESC = False


def indent_print(s, indent):
    print(" "*indent + s)

def value_str(sc):
    """
    Returns the value part ("[*]", "<M>", "(foo)" etc.) of a menu entry.
    sc: Symbol or Choice.
    """
    if sc.type in (STRING, INT, HEX):
        return "({})".format(sc.str_value)

    # BOOL or TRISTATE

    # The choice mode is an upper bound on the visibility of choice symbols, so
    # we can check the choice symbols' own visibility to see if the choice is
    # in y mode
    if isinstance(sc, Symbol) and sc.choice and sc.visibility == 2:
        # For choices in y mode, print '-->' next to the selected symbol
        return "-->" if sc.choice.selection is sc else "   "

    tri_val_str = (" ", "M", "*")[sc.tri_value]

    if len(sc.assignable) == 1:
        # Pinned to a single value
        return "-{}-".format(tri_val_str)

    if sc.type == BOOL:
        return "[{}]".format(tri_val_str)

    if sc.type == TRISTATE:
        if sc.assignable == (1, 2):
            # m and y available
            return "{" + tri_val_str + "}"  # Gets a bit confusing with .format()
        return "<{}>".format(tri_val_str)

def node_str(node):
    """
    Returns the complete menu entry text for a menu node, or "" for invisible
    menu nodes. Invisible menu nodes are those that lack a prompt or that do
    not have a satisfied prompt condition.
    Example return value: "[*] Bool symbol (BOOL)"
    The symbol name is printed in parentheses to the right of the prompt.
    """
    if not node.prompt:
        return ""

    # Even for menu nodes for symbols and choices, it's wrong to check
    # Symbol.visibility / Choice.visibility here. The reason is that a symbol
    # (and a choice, in theory) can be defined in multiple locations, giving it
    # multiple menu nodes, which do not necessarily all have the same prompt
    # visibility. Symbol.visibility / Choice.visibility is calculated as the OR
    # of the visibility of all the prompts.
    prompt, prompt_cond = node.prompt
    if not expr_value(prompt_cond):
        return ""

    if node.item == MENU:
        return "    " + prompt

    if node.item == COMMENT:
        return "    *** {} ***".format(prompt)

    # Symbol or Choice

    sc = node.item

    if sc.type == UNKNOWN:
        # Skip symbols defined without a type (these are obscure and generate
        # a warning)
        return ""

    # Add help text
    if WITH_HELP_DESC:
        prompt += ' - ' + str(node.help).replace('\n', ' ').replace('\r', '')

    # {:3} sets the field width to three. Gives nice alignment for empty string
    # values.
    res = "{:3} {}".format(value_str(sc), prompt)

    # Don't print the name for unnamed choices (the normal kind)
    if sc.name is not None:
        res += " ({})".format(sc.name)

    return res


def print_menuconfig_nodes(node, indent):
    """
    Prints a tree with all the menu entries rooted at 'node'. Child menu
    entries are indented.
    """
    while node:
        string = node_str(node)
        if string:
            indent_print(string, indent)

        if node.list:
            print_menuconfig_nodes(node.list, indent + 8)

        node = node.next


def print_menuconfig(kconf):
    """
    Prints all menu entries for the configuration.
    """
    # Print the expanded mainmenu text at the top. This is the same as
    # kconf.top_node.prompt[0], but with variable references expanded.
    print("\n======== {} ========\n".format(kconf.mainmenu_text))

    print_menuconfig_nodes(kconf.top_node.list, 0)
    print("")


if __name__ == "__main__":
    sys.setrecursionlimit(1000000)
    faulthandler.enable()
    os.chdir("/mnt/hdd/openwrt")
    # Load Kconfig configuration files
    kconf = Kconfig("Config.in")
    kconf.load_config(".config")
    print_menuconfig(kconf)
