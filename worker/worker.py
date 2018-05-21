import os
import json
import sys
import uuid
import shlex
from collections import defaultdict
from functools import partial
from pprint import pprint

import tornado.gen
import tornado.log
import tornado.web
import tornado.wsgi
import tornado.queues
import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.autoreload

from terminado import TermSocket, NamedTermManager


from tornado.gen import coroutine, Task, Return
from tornado.process import Subprocess


LEDEForge = """                                                               
 #      #####  #####     #####  #####                                
 #      #      #    ##   #      #                                    
 #      #      #     #   #      #                                    
 #      #      #      #  #      #       ####   # ##   ## #   ###     
 #      #####  #      #  #####  #####   #  ##  ##    #  ##   #  #    
 #      #      #      #  #      #      #    #  #    #    #  #   #    
 #      #      #      #  #      #      #    #  #    #    #  #####    
 #      #      #     #   #      #      #    #  #    #    #  #        
 #      #      #    ##   #      #      ##  #   #    ##  ##  ##  #    
 ###### #####  #####     #####  #       ####   #     ### #   ###     
                                                         #           
                                                     #  #            
                                                      ###                   
"""


from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value


class SpecificNamedTermManager(NamedTermManager):
    def new_named_terminal(self, *args, **kwargs):
        name = uuid.uuid4().hex
        command = kwargs.get('shell_command')
        term = self.new_terminal(shell_command=command)
        term.term_name = name
        self.terminals[name] = term
        self.start_reading(term)
        return name, term

    def get_terminal(self, term_name):
        if term_name in self.terminals:
            return self.terminals[term_name]
        raise KeyError(term_name)


class BaseHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        super(BaseHandler, self).data_received(chunk)

    def write_json(self, obj):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(obj))


class ProcessManager(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.processes = {}
        self.process_output = {}

    async def call_subprocess_async(self, cmd):
        sub_process = Subprocess(shlex.split(cmd), stdin=None, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
        self.processes[sub_process.proc.pid] = sub_process

        result = Task(sub_process.stdout.read_until_close)
        error = Task(sub_process.stderr.read_until_close)

        result = await result
        error = await error

        return result, error

    def call_subprocess(self, cmd):
        sub_process = Subprocess(shlex.split(cmd), stdin=None, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
        self.processes[sub_process.proc.pid] = sub_process
        tornado.ioloop.IOLoop.instance().add_callback(
            sub_process.stdout.fileno(),
            partial(self.on_subprocess_return, sub_process.proc.pid)
        )

    def on_subprocess_return(self, pid, *args, **kwargs):
        pass

    def start(self, path, stream=False):
        pass

    def kill(self, pid):
        self.processes[pid].proc.kill()

    def get_output(self, pid):
        pass


class ProcessHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(ProcessHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.process_manager = kwargs.get('process')


class ProcessAccessHandler(ProcessHandler):
    def get(self, *args, **kwargs):
        # get output
        pass

    def post(self, *args, **kwargs):
        # kill
        pass


class ProcessManageHandler(ProcessHandler):
    def get(self):
        pass

    def post(self, *args, **kwargs):
        pass


class TerminalManager(object):
    def __init__(self, tm, command_prefix):
        self.tm = tm
        self.command_prefix = command_prefix
        self.terminal_commands = defaultdict(dict)

    def create(self, command, terminal_type="default"):
        full_command = "{prefix} {command}".format(prefix=self.command_prefix, command=command).strip()
        commands = shlex.split(full_command)
        name, term = self.tm.new_named_terminal(shell_command=commands)
        self.terminal_commands[terminal_type][name] = full_command
        return name

    def list(self, terminal_type="default"):
        return [{'name': name, 'command': command} for name, command in self.terminal_commands[terminal_type].items()]

    def delete(self, name):
        pass

    def __del__(self):
        self.tm.shutdown()


class TerminalHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TerminalHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.terminal_manager = kwargs.get('terminal')


class TerminalAccessHandler(TerminalHandler):
    def get(self, terminal_name):
        for t in self.terminal_manager.terminal_commands.values():
            if terminal_name in t.keys():
                self.render("templates/terminal.html", terminal_name=terminal_name)
        raise tornado.web.HTTPError(404)


class TerminalManageHandler(TerminalHandler):
    def post(self, *args, **kwargs):
        data = tornado.escape.json_decode(self.request.body or "{}")
        command = data.get("command", "fish")
        name = self.terminal_manager.create(command=command)
        self.write_json({"name": name})

    def get(self):
        self.write_json(self.terminal_manager.list())


class TestEnvManager(object):
    def __init__(self, terminal):
        self.terminal = terminal
        self.test_env_cmdline = {}

    def create(self, image_file, image_config=None, network_config=None):
        if image_config:
            image_config = "," + image_config
        cmdline = "qemu-system-x86_64 -nographic -serial mon:stdio -boot c -drive file={image_file}{image_config}"
        full_command_line = cmdline.format(image_file=image_file, image_config=image_config)
        name = self.terminal.create(command=full_command_line, terminal_type="testenv")
        self.test_env_cmdline[name] = full_command_line
        return name


class TestEnvHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TestEnvHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.testenv_manager = kwargs.get('testenv')

    def get(self):
        self.write_json(self.testenv_manager.test_env_cmdline)

    def post(self):
        data = tornado.escape.json_decode(self.request.body or "{}")
        image_file = data.get("image_file")
        image_config = data.get("image_config", "if=virtio")
        name = self.testenv_manager.create(image_file=image_file, image_config=image_config)
        self.write_json({"name": name})


class KconfigManager(object):
    def __init__(self, kconfig_filename):
        self.kconfig_filename = kconfig_filename
        self.kconfig = Kconfig(kconfig_filename)

    @staticmethod
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

    def serialize_node(self, node, sequence_id):
        result = {}
        if node.item == UNKNOWN:
            return result

        if not node.prompt:
            return result

        prompt, prompt_cond = node.prompt
        result.update({
            'prompt': prompt,
            'prompt_cond': expr_value(prompt_cond),
            'choices': False
        })
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
                'value': self.value_str(sc)
            })
        if node.list:
            result['sequence_id'] = sequence_id
            result['choices'] = True
        return result

    def get_menuconfig_nodes(self, node, max_nodes=0):
        node_dicts = []
        nodes = []
        sequence_id = 0
        while node:
            if max_nodes > 0:
                if sequence_id > 0:
                    if sequence_id > max_nodes:
                        return node_dicts, nodes
            node_dict = self.serialize_node(node, sequence_id)
            nodes.append(node)
            if node_dict:
                node_dicts.append(node_dict)
            node = node.next
            sequence_id += 1
        return node_dicts, nodes

    def load_config(self, config_file):
        self.kconfig.load_config(config_file)

    def save_config(self, config_file):
        self.kconfig.write_config(config_file)

    def get_menuconfig_menu(self, sequence):
        current_node = self.kconfig.top_node
        for index in [0] + sequence:
            node_dict, nodes = self.get_menuconfig_nodes(current_node, index)
            current_node = nodes[index].list

        node_dicts, _ = self.get_menuconfig_nodes(current_node)
        return node_dicts


class KconfigHandler(BaseHandler):
    def initialize(self, **kwargs):
        self.kconfig_manager = kwargs.get("kconfig_manager")

    def get(self, *args, **kwargs):
        sequence = self.get_query_argument("sequence", "")
        if sequence:
            sequence_list = [int(x) for x in sequence.split(",")]
        else:
            sequence_list = []
        self.write_json(self.kconfig_manager.get_menuconfig_menu(sequence_list))


def create_app():
    term_manager = SpecificNamedTermManager(shell_command=["nologin"])
    terminal = TerminalManager(term_manager, "")
    testenv = TestEnvManager(terminal)
    kconf = KconfigManager("Config.in")
    kconf.load_config(".config")

    handlers = [
        (r"/terminal/", TerminalManageHandler, {'terminal': terminal}),
        (r"/terminal/(\w+)", TerminalAccessHandler, {'terminal': terminal}),
        (r"/terminal/ws/(\w+)", TermSocket, {'term_manager': term_manager}),
        (r"/testenv/", TestEnvHandler, {'testenv': testenv}),
        (r"/kconfig/", KconfigHandler, {'kconfig_manager': kconf}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "static")}),
    ]

    return tornado.web.Application(handlers)


def start_server(host, port):
    print("Starting LEDEForge Worker")
    create_app().listen(port, host)

    loop = tornado.ioloop.IOLoop.instance()
    print(LEDEForge)
    print("LEDEForge Worker, running on port {}".format(port))
    try:
        loop.start()
    except KeyboardInterrupt:
        print("Shutting down on SIGINT")
    finally:
        loop.close()


configurations = {}

if __name__ == '__main__':
    sys.setrecursionlimit(1000000)
    os.chdir("/mnt/hdd/openwrt")
    start_server("0.0.0.0", 8765)


