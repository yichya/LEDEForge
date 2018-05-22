import os
import json
import sys
import uuid
import shlex
from collections import defaultdict
from functools import partial

import tornado.gen
import tornado.log
import tornado.web
import tornado.wsgi
import tornado.queues
import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.process
from terminado import TermSocket, NamedTermManager
from kconfig.kconfiglib import Kconfig, Symbol, MENU, COMMENT, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value



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
STREAM = tornado.process.Subprocess.STREAM


class BaseHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        super(BaseHandler, self).data_received(chunk)

    def write_json(self, obj):
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.write(json.dumps(obj))


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


class ProcessManager(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.processes = {}
        self.process_output = {}

    def call_subprocess(self, cmd, args, cb_stdout, cb_stderr, cb_exit):
        cmdlist = shlex.split("{} {}".format(self.prefix, cmd)) + args
        sub_process = tornado.process.Subprocess(cmdlist, stdout=STREAM, stderr=STREAM)
        pid = sub_process.proc.pid
        sub_process.stdout.read_until_close(streaming_callback=partial(cb_stdout, pid))
        sub_process.stderr.read_until_close(streaming_callback=partial(cb_stderr, pid))
        sub_process.set_exit_callback(cb_exit)
        return pid

    @tornado.gen.coroutine
    def create_stream(self, cmd, args):
        def data_callback_stdout(pid, data):
            self.processes[pid].put({
                'type': 'stdout',
                'value': data
            })

        def data_callback_stderr(pid, data):
            self.processes[pid].put({
                'type': 'stderr',
                'value': data
            })

        def exit_callback(pid, code):
            self.processes[pid].put({
                'type': 'exit',
                'value': code
            })

        pid = self.call_subprocess(cmd, args, data_callback_stdout, data_callback_stderr, exit_callback)
        q = tornado.queues.Queue()
        self.processes[pid] = q
        return pid

    @tornado.gen.coroutine
    def create_sync(self, cmd, args):
        cmdlist = shlex.split("{} {}".format(self.prefix, cmd)) + args
        sub_process = tornado.process.Subprocess(cmdlist, stdout=STREAM, stderr=STREAM)
        result, error = yield [
            tornado.gen.Task(sub_process.stdout.read_until_close),
            tornado.gen.Task(sub_process.stderr.read_until_close)
        ]
        ret = yield sub_process.wait_for_exit()
        return result, error, ret

    def start(self, path, args, stream=False):
        if stream:
            return self.create_stream(path, args)
        else:
            return self.create_sync(path, args)

    def kill(self, pid):
        self.processes[pid].proc.kill()

    def get_output(self, pid):
        result = []
        q = self.processes[pid]
        while not q.empty():
            result.append(q.get())
        return result


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


class RunWithSubprocessCoroutineMixin(object):
    def __init__(self, pm: ProcessManager):
        self.pm = pm

    def subprocess_stdout_future(self, cmd):
        sub_process = tornado.process.Subprocess(shlex.split(cmd), stdout=STREAM)
        yield tornado.gen.Task(sub_process.stdout.read_until_close)

    def subprocess_in_pm_queue(self, cmd):
        return self.pm.start(cmd, [], True)


class RepositoryManager(RunWithSubprocessCoroutineMixin):
    def __init__(self, pm):
        super(RepositoryManager, self).__init__(pm)
    
    @property
    @tornado.gen.coroutine
    def serialize(self):
        return tornado.gen.maybe_future({
            'branch': self.branch,
            'tag': self.tag,
            'head_commit_id': self.head_commit_id,
            'lede_version': self.lede_version,
            'lede_kernel_version': self.lede_kernel_version
        })

    @property
    @tornado.gen.coroutine
    def branch(self):
        result = yield self.subprocess_stdout_future('git rev-parse --abbrev-ref HEAD')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def tag(self):
        result = yield self.subprocess_stdout_future('git describe --tags')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def head_commit_id(self):
        result = yield self.subprocess_stdout_future('git rev-parse HEAD')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def lede_version(self):
        result = yield self.subprocess_stdout_future('./scripts/getver.sh')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def lede_kernel_version(self):
        result = yield self.subprocess_stdout_future('cat include/kernel-version.mk | grep LINUX_KERNEL_HASH- | grep .')
        version_lines = str(result.decode())
        print(version_lines)
        versions = {}
        for version_line in version_lines.split('\n'):
            try:
                version = version_line.split('LINUX_KERNEL_HASH-')[1].split('=')
                versions[version[0].strip()] = version[1].strip()
            except:
                pass
        return versions

    @tornado.gen.coroutine
    def amend_customizations(self):
        queue_id = yield self.subprocess_in_pm_queue("git commit -a --amend --no-edit")
        return queue_id

    @tornado.gen.coroutine
    def update_code(self):
        queue_id = yield self.subprocess_in_pm_queue("git pull --rebase")
        return queue_id


class RepositoryHandler(BaseHandler):
    def initialize(self, **kwargs):
        self.rm = kwargs['rm']

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        result = yield self.rm.serialize
        print(result.result())
        self.write_json(result)


class PackageManager(RunWithSubprocessCoroutineMixin):
    def __init__(self, pm):
        super(PackageManager, self).__init__(pm)

    @tornado.gen.coroutine
    def lede_packages(self, keyword=None):
        if keyword:
            command = './scripts/feeds search %s' % keyword
        else:
            command = './scripts/feeds list'
        result = yield self.subprocess_stdout_future(command)
        package_lines = str(result.decode())
        packages = {}
        for package_line in package_lines.split('\n'):
            try:
                package_detail = package_line.split('\t', maxsplit=1)
                packages[package_detail[0].strip()] = package_detail[1].strip()
            except:
                pass
        return packages

    @tornado.gen.coroutine
    def update_feeds(self):
        queue_id = yield self.subprocess_in_pm_queue("./scripts/feeds update -a")
        return queue_id

    @tornado.gen.coroutine
    def install_feeds(self):
        queue_id = yield self.subprocess_in_pm_queue("./scripts/feeds install -a")
        return queue_id


class BuildManager(RunWithSubprocessCoroutineMixin):
    def __init__(self, pm):
        super(BuildManager, self).__init__(pm)

    @tornado.gen.coroutine
    def make(self, arguments):
        queue_id = yield self.subprocess_in_pm_queue("make %s" % " ".join(arguments))
        return queue_id

    @tornado.gen.coroutine
    def clean(self):
        queue_id = yield self.subprocess_in_pm_queue("make clean")
        return queue_id

    @tornado.gen.coroutine
    def dirclean(self):
        queue_id = yield self.subprocess_in_pm_queue("make dirclean")
        return queue_id


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
    process_manager = ProcessManager("")
    repository_manager = RepositoryManager(process_manager)
    handlers = [
        (r"/", RepositoryHandler, {'rm': repository_manager}),
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


