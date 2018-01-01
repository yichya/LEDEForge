import os
import uuid
from django.views import View
from terminado import NamedTermManager
from django.shortcuts import render_to_response


class SpecificNamedTermManager(NamedTermManager):
    def new_named_terminal(self, *args, **kwargs):
        name = uuid.uuid4().hex
        term = self.new_terminal(shell_command=kwargs.get('shell_command'))
        term.term_name = name
        self.terminals[name] = term
        self.start_reading(term)
        return name, term

    def get_terminal(self, term_name):
        if term_name in self.terminals:
            return self.terminals[term_name]
        raise KeyError(term_name)


container_terminal_manager = SpecificNamedTermManager(shell_command=['nologin'])
source_terminal_manager = SpecificNamedTermManager(shell_command=['nologin'])
virtual_machine_terminal_manager = SpecificNamedTermManager(shell_command=['nologin'])


def default_context():
    return {
        "os": os.name
    }


class IndexView(View):
    def get(self, request):
        return render_to_response("frame.html", default_context())


class TerminalView(View):
    def get(self, request, terminal_type, terminal_name):
        return render_to_response("terminal.html", {
            'terminal_type': terminal_type,
            'terminal_name': terminal_name
        })
