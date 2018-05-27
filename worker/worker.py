import os
import json
import re
import sys
import uuid
import shlex
from collections import defaultdict

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
from terminado.management import PtyWithClients

from kconfig.kconfiglib import Kconfig, Choice, Symbol, MENU, COMMENT, UNKNOWN, STRING, INT, HEX, BOOL, TRISTATE, expr_value

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

    def write_json(self, obj: object) -> None:
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.write(json.dumps(obj))


class SpecificNamedTermManager(NamedTermManager):
    def new_named_terminal(self, *args, **kwargs) -> (str, PtyWithClients):
        name = uuid.uuid4().hex
        command = kwargs.get('shell_command')
        term = self.new_terminal(shell_command=command)
        term.term_name = name
        self.terminals[name] = term
        self.start_reading(term)
        return name, term

    def get_terminal(self, term_name: str) -> PtyWithClients:
        if term_name in self.terminals:
            return self.terminals[term_name]
        raise KeyError(term_name)


class ProcessManager(object):
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.processes = {}
        self.process_output = {}

    def call_subprocess(self, cmd: str, args: list, cb_stdout, cb_stderr, cb_exit) -> int:
        cmdlist = shlex.split("{} {}".format(self.prefix, cmd)) + args
        sub_process = tornado.process.Subprocess(cmdlist, stdout=STREAM, stderr=STREAM)
        pid = sub_process.proc.pid
        sub_process.stdout.read_until_close(streaming_callback=cb_stdout)
        sub_process.stderr.read_until_close(streaming_callback=cb_stderr)
        sub_process.set_exit_callback(cb_exit)
        return pid

    def create_stream(self, cmd: str, args: list) -> int:
        q = tornado.queues.Queue()

        def data_callback_stdout(data: bytes) -> None:
            q.put({
                'type': 'stdout',
                'value': data.decode()
            })

        def data_callback_stderr(data: bytes) -> None:
            q.put({
                'type': 'stderr',
                'value': data.decode()
            })

        def exit_callback(code: int = 0) -> None:
            q.put({
                'type': 'exit',
                'value': code
            })

        pid = self.call_subprocess(cmd, args, data_callback_stdout, data_callback_stderr, exit_callback)
        self.processes[pid] = q
        return pid

    def start(self, path: str, args: list = None) -> tornado.gen.Future:
        if args is None:
            args = []
        sub_process = tornado.process.Subprocess(shlex.split(path) + args, stdout=STREAM)
        return tornado.gen.Task(sub_process.stdout.read_until_close)

    def start_stream(self, path: str, args: list = None) -> int:
        if args is None:
            args = []
        pid = self.create_stream(path, args)
        return pid

    def kill(self, pid: int) -> None:
        self.processes[int(pid)].proc.kill()

    @tornado.gen.coroutine
    def get_output(self, pid) -> tornado.gen.Future:
        result = []
        q = self.processes[int(pid)]
        while not q.empty():
            result.append(q.get())
        data = yield result
        return data


class ProcessHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(ProcessHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self._process_manager = kwargs.get('process_manager')

    @property
    def process_manager(self) -> ProcessManager:
        return self._process_manager


class ProcessAccessHandler(ProcessHandler):
    @tornado.gen.coroutine
    def get(self, pid: str) -> None:
        try:
            result = yield self.process_manager.get_output(pid)
            self.write_json(result)
        except KeyError:
            raise tornado.web.HTTPError(404)

    def post(self):
        pid = self.get_body_argument("pid")
        self.process_manager.kill(pid)
        return {}


class KconfigManager(object):
    def __init__(self, kconfig_filename: str):
        self.kconfig_filename = kconfig_filename
        self.kconfig = Kconfig(kconfig_filename, warn_to_stderr=False, logger=tornado.log.app_log)

    @staticmethod
    def serialize_node_value(sc):
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

        if sc.type in [BOOL, TRISTATE]:
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
        prompt_cond_evaluated = expr_value(prompt_cond)
        if not prompt_cond_evaluated:
            return result

        result.update({
            'prompt': prompt,
            'prompt_cond': prompt_cond_evaluated,
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
                'visibility': sc.visibility,
                'help': node.help,
                'value': self.serialize_node_value(sc),
                'choice': False
            })
            if isinstance(sc, Choice):
                result['choice'] = True
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
        sequence_names = []
        current_node = self.kconfig.top_node
        if not sequence or sequence[0] != 0:
            sequence = [0] + sequence
        for index in sequence:
            node_dict, nodes = self.get_menuconfig_nodes(current_node, index)
            last_sequence = sequence_names[-1]['sequence'].split(",") if sequence_names else []
            sequence_str = ",".join(last_sequence + [str(index)])
            node_name = nodes[index].prompt[0].split("..")[0]
            sequence_names.append({'sequence': sequence_str, 'node_name': node_name})
            current_node = nodes[index].list
        node_dicts, _ = self.get_menuconfig_nodes(current_node)
        current_node_dict = self.serialize_node(current_node, 0)
        return node_dicts, sequence_names, current_node_dict


class KconfigHandler(BaseHandler):
    def initialize(self, **kwargs):
        self._kconfig_manager = kwargs.get("kconfig_manager")

    @property
    def kconfig_manager(self) -> KconfigManager:
        return self._kconfig_manager

    def get(self, *args, **kwargs):
        sequence = self.get_query_argument("sequence", "")
        if sequence:
            sequence_list = [int(x) for x in sequence.split(",")]
        else:
            sequence_list = []
        node_dicts, sequence_names, current_node_dict = self.kconfig_manager.get_menuconfig_menu(sequence_list)
        print(sequence_names)
        self.write_json({
            'node_dicts': node_dicts,
            'sequence_names': sequence_names,
            'current_node_dict': current_node_dict
        })


class RepositoryManager(object):
    def __init__(self, pm: ProcessManager, km: KconfigManager):
        self.pm = pm
        self.km = km

    @property
    def current_arch(self):
        arch_list, _, _ = self.km.get_menuconfig_menu([90])
        for symbol in arch_list:
            if symbol['value']['value']['selected']:
                return symbol['prompt'], symbol['name']

    @property
    def current_subtarget(self):
        arch_list, _, _ = self.km.get_menuconfig_menu([91])
        for symbol in arch_list:
            if symbol['value']['value']['selected']:
                return symbol['prompt']

    @property
    @tornado.gen.coroutine
    def current_kernel_version(self):
        arch = self.current_arch
        arch_name = arch[1][7:]
        f = open("target/linux/{arch_name}/Makefile".format(arch_name=arch_name))
        data = f.read()
        r = re.compile(r"KERNEL_PATCHVER:=(\d[.]\d)")
        result = r.findall(data)
        kernel_version = result[0]
        lede_kernel_versions = yield self.lede_kernel_version
        for v in lede_kernel_versions.keys():
            if v.startswith(kernel_version):
                return v
        return kernel_version

    @property
    @tornado.gen.coroutine
    def serialize(self) -> dict:
        result = yield {
            'branch': self.branch,
            'tag': self.tag,
            'head_commit_id': self.head_commit_id,
            'lede_version': self.lede_version,
            'current_arch': tornado.gen.maybe_future(self.current_arch[0]),
            'current_subtarget': tornado.gen.maybe_future(self.current_subtarget),
            'current_kernel_version': tornado.gen.maybe_future(self.current_kernel_version)
        }
        return result

    @property
    @tornado.gen.coroutine
    def branch(self) -> tornado.gen.Future:
        result = yield self.pm.start('git rev-parse --abbrev-ref HEAD')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def tag(self) -> tornado.gen.Future:
        result = yield self.pm.start('git describe --tags')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def head_commit_id(self) -> tornado.gen.Future:
        result = yield self.pm.start('git rev-parse HEAD')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def lede_version(self) -> tornado.gen.Future:
        result = yield self.pm.start('./scripts/getver.sh')
        return str(result.decode()).split('\n')[0]

    @property
    @tornado.gen.coroutine
    def lede_kernel_version(self) -> tornado.gen.Future:
        result = yield self.pm.start('bash -c "cat include/kernel-version.mk | grep LINUX_KERNEL_HASH- | grep ."')
        version_lines = str(result.decode())
        versions = {}
        for version_line in version_lines.split('\n'):
            try:
                version = version_line.split('LINUX_KERNEL_HASH-')[1].split('=')
                versions[version[0].strip()] = version[1].strip()
            except:
                pass
        return versions

    def amend_customizations(self) -> int:
        pid = self.pm.start_stream("git commit -a --amend --no-edit")
        return pid

    def update_code(self) -> int:
        pid = self.pm.start_stream("git pull --rebase")
        return pid


class RepositoryHandler(BaseHandler):
    def initialize(self, **kwargs):
        self._rm = kwargs['rm']

    @property
    def rm(self) -> RepositoryManager:
        return self._rm

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        result = yield self.rm.serialize
        self.write_json(result)

    def post(self, *args, **kwargs):
        operations = {
            'update_code': self.rm.update_code,
            'amend_customizations': self.rm.amend_customizations
        }
        operation = self.get_body_argument("operation")
        pid = operations[operation]()
        self.write_json({'pid': pid})


class PackageManager(object):
    def __init__(self, pm: ProcessManager):
        self.pm = pm

    @tornado.gen.coroutine
    def lede_packages(self, keyword=None):
        if keyword:
            command = './scripts/feeds search %s' % keyword
        else:
            command = './scripts/feeds list'
        result = yield self.pm.start(command)
        package_lines = str(result.decode())
        packages = {}
        for package_line in package_lines.split('\n'):
            try:
                package_detail = package_line.split('\t', maxsplit=1)
                packages[package_detail[0].strip()] = package_detail[1].strip()
            except:
                pass
        return packages

    def update_feeds(self):
        pid = self.pm.start_stream("./scripts/feeds update -a")
        return pid

    def install_feeds(self):
        pid = self.pm.start_stream("./scripts/feeds install -a")
        return pid


class PackageHandler(BaseHandler):
    def initialize(self, **kwargs):
        self._pm = kwargs['pm']

    @property
    def pm(self) -> PackageManager:
        return self._pm

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        keyword = self.get_query_argument("keyword", None)
        result = yield self.pm.lede_packages(keyword)
        self.write_json(result)

    def post(self, *args, **kwargs):
        operations = {
            'update_feeds': self.pm.update_feeds,
            'install_feeds': self.pm.install_feeds
        }
        operation = self.get_body_argument("operation")
        pid = operations[operation]()
        self.write_json({'pid': pid})


class BuildManager(object):
    def __init__(self, pm: ProcessManager):
        self.pm = pm

    def make(self, args):
        pid = self.pm.start_stream("make %s" % args)
        return pid

    def defconfig(self):
        pid = self.pm.start_stream("make defconfig")
        return pid

    def clean(self):
        pid = self.pm.start_stream("make clean")
        return pid

    def dirclean(self):
        pid = self.pm.start_stream("make dirclean")
        return pid


class BuildHandler(BaseHandler):
    def initialize(self, **kwargs):
        self._bm = kwargs['bm']

    @property
    def bm(self) -> BuildManager:
        return self._bm

    def get(self, *args, **kwargs):
        self.write_json({})

    def post(self, *args, **kwargs):
        operations = {
            'defconfig': self.bm.defconfig,
            'clean': self.bm.clean,
            'dirclean': self.bm.dirclean,
            'make': self.bm.make
        }
        operation = self.get_body_argument("operation")
        args = self.get_body_argument("args", "")
        pid = operations[operation](args)
        self.write_json({'pid': pid})


class TerminalManager(object):
    def __init__(self, tm: SpecificNamedTermManager, command_prefix: str):
        self.tm = tm
        self.command_prefix = command_prefix
        self.terminal_commands = defaultdict(dict)

    def create(self, command: str, terminal_type: str = "default"):
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
        self._terminal_manager = kwargs.get('terminal')

    @property
    def terminal_manager(self) -> TerminalManager:
        return self._terminal_manager


class TerminalAccessHandler(TerminalHandler):
    def get(self, terminal_name: str):
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
    def __init__(self, terminal: TerminalManager):
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
        self._testenv_manager = kwargs.get('testenv')

    @property
    def testenv_manager(self) -> TestEnvManager:
        return self._testenv_manager

    def get(self):
        self.write_json(self.testenv_manager.test_env_cmdline)

    def post(self):
        data = tornado.escape.json_decode(self.request.body or "{}")
        image_file = data.get("image_file")
        image_config = data.get("image_config", "if=virtio")
        name = self.testenv_manager.create(image_file=image_file, image_config=image_config)
        self.write_json({"name": name})


def create_app():
    term_manager = SpecificNamedTermManager(shell_command=["nologin"])
    terminal = TerminalManager(term_manager, "")
    testenv = TestEnvManager(terminal)
    process_manager = ProcessManager("")
    kconfig_manager = KconfigManager("Config.in")
    kconfig_manager.load_config(".config")
    repository_manager = RepositoryManager(process_manager, kconfig_manager)
    package_manager = PackageManager(process_manager)
    build_manager = BuildManager(process_manager)
    handlers = [
        (r"/", RepositoryHandler, {'rm': repository_manager}),
        (r"/build/", BuildHandler, {'bm': build_manager}),
        (r"/package/", PackageHandler, {'pm': package_manager}),
        (r"/terminal/", TerminalManageHandler, {'terminal': terminal}),
        (r"/terminal/(\w+)", TerminalAccessHandler, {'terminal': terminal}),
        (r"/terminal/ws/(\w+)", TermSocket, {'term_manager': term_manager}),
        (r"/testenv/", TestEnvHandler, {'testenv': testenv}),
        (r"/kconfig/", KconfigHandler, {'kconfig_manager': kconfig_manager}),
        (r"/process/(\d+)", ProcessAccessHandler, {'process_manager': process_manager}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "static")}),
    ]

    return tornado.web.Application(handlers)


def start_server(repo_dir, host, port):
    tornado.log.app_log.info("Starting LEDEForge Worker")
    os.chdir(repo_dir)
    tornado.log.app_log.info("Setting Repository Path to {}".format(repo_dir))
    create_app().listen(port, host)

    loop = tornado.ioloop.IOLoop.instance()
    tornado.log.app_log.info(LEDEForge)
    tornado.log.app_log.info("LEDEForge Worker, running on port {}".format(port))
    try:
        loop.start()
    except KeyboardInterrupt:
        tornado.log.app_log.info("Shutting down on SIGINT")
    finally:
        loop.close()


configurations = {}

if __name__ == '__main__':
    sys.setrecursionlimit(16000)
    tornado.options.parse_command_line()
    start_server("/home/pi/openwrt", "0.0.0.0", 8765)
