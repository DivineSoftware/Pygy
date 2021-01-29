#!/usr/bin/env python
#from rich import pretty
#pretty.install()
from asyncio import Future, ensure_future
import subprocess, datetime, threading, json #PyInstaller.__main__
from pygments.lexers.html import HtmlLexer
from prompt_toolkit.shortcuts import prompt, button_dialog
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit import formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import PathCompleter, WordCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from pygments.lexers.basic import BlitzMaxLexer, QBasicLexer
from pygments.lexers.python import Python3Lexer
from pygments.lexers.c_like import CharmciLexer
from pygments.lexers.shell import BashLexer
from pygments.lexers.dotnet import CSharpAspxLexer
from pygments.lexers.asm import NasmLexer
from pygments.lexers.jvm import JavaLexer
from pygments.lexers.javascript import JavascriptLexer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer, pygments
from prompt_toolkit.search import start_search
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import (
    Button,
    Dialog,
    Label,
    MenuContainer,
    MenuItem,
    SearchToolbar,
    TextArea,
)


class ApplicationState:
    show_status_bar = True
    current_path = None


def get_statusbar_text():
    return " Press Ctrl-C to open menu. "


def get_statusbar_right_text():
    return " {}:{}  ".format(
        text_field.document.cursor_position_row + 1,
        text_field.document.cursor_position_col + 1,
    )


try:
    with open("config.json", "r") as conf:
        configuration = json.loads(conf.read())
        lines = configuration['lines']
        scrollbar = configuration['scrollbar']
        if configuration['completer'] != "": completer = configuration['completer']
except:
    lines = False
    scrollbar = False


#code_completer = WordCompleter(['<html>', '<body>', '<head>', '<title>'])
#class AutoComplete
file_name = None
result = None
search_toolbar = SearchToolbar()
text_field = TextArea(
    #lexer=PygmentsLexer(BlitzMaxLexer),#DynamicLexer(
        #lambda: PygmentsLexer.from_filename(
            #ApplicationState.current_path or ".txt", sync_from_start=False
        #)
    #),
    #completer=completer,
    scrollbar=scrollbar,
    line_numbers=lines,
    search_field=search_toolbar,
)


def run_script(cmd, arg):
    return subprocess.Popen([cmd, arg])

class RunningDialog:
    def __init__(self, title="Running", label_text="", completer=None):
        self.future = Future()

        def wait():
            self.future.set_result(None)

        def terminate():
            self.future.set_result("terminate")

        wait_button = Button(text="Wait", handler=wait)
        terminate_button = Button(text="Terminate", handler=terminate)

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=label_text)]),
            buttons=[wait_button, terminate_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog
        
        
class TextInputDialog:
    def __init__(self, title="", label_text="", completer=None):
        self.future = Future()

        def accept_text(buf):
            get_app().layout.focus(ok_button)
            buf.complete_state = None
            return True

        def accept():
            self.future.set_result(self.text_area.text)

        def cancel():
            self.future.set_result(None)

        self.text_area = TextArea(
            completer=completer,
            multiline=False,
            width=D(preferred=40),
            accept_handler=accept_text,
        )

        ok_button = Button(text="Ok", handler=accept)
        cancel_button = Button(text="Cancel", handler=cancel)

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=label_text), self.text_area]),
            buttons=[ok_button, cancel_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class MessageDialog:
    def __init__(self, title="", text=""):
        self.future = Future()

        def set_done():
            self.future.set_result(None)

        ok_button = Button(text="Ok", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class CompileDialog:
    def __init__(self, title="Compile", text=""):
        self.future = Future()
        if file_name == None:
            self.future.set_result(None)
            show_message("Error", "Save/Open the file first")

        def set_done():
            self.future.set_result(None)

        def python_compiler():
            result = subprocess.getoutput('PyInstaller ' + file_name) #PyInstaller.__main__.run([file_name])
            self.future.set_result(None)
            show_message("Compiler", result)

        def csharp_compiler():
            result = subprocess.getoutput('mcs ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        def c_compiler():
            result = subprocess.getoutput('gcc ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        def node_compiler():
            result = subprocess.getoutput('nexe ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)
            #https://github.com/nexe/nexe

        def java_compiler():
            result = subprocess.getoutput('javac ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        py_button = Button(text="Python", handler=python_compiler)
        c_button = Button(text="C/C++", handler=c_compiler)
        cs_button = Button(text="C#", handler=csharp_compiler)
        js_button = Button(text="Node.js", handler=node_compiler)
        jv_button = Button(text="Java", handler=java_compiler)
        ok_button = Button(text="Cancel", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[py_button, c_button, cs_button, jv_button, js_button, ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class RunDialog:
    def __init__(self, title="Run", text=""):
        self.future = Future()
        global result
        #result = None
        if file_name == None:
            self.future.set_result(None)
            show_message("Error", "Save/Open the file first")

        def set_done():
            self.future.set_result(None)

        def python_runner():
            result = subprocess.getoutput('python ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)
            """
            result = subprocess.Popen(['python', file_name])#run_script('python ' + file_name)#subprocess.getoutput('python ' + file_name)
            #self.future.set_result(None)
            try:
                if result.stdout.readline()==None: pass
                self.future.set_result(None)
                show_message("Compiler", result.stdout.readline())
            except:
                async def coroutine():
                    dialog = RunningDialog()
                    action = await show_dialog_as_float(dialog)
                    if action == "terminate":
                        result.terminate()
                    else:
                        self.future.set_result(None)
                ensure_future(coroutine())
            """
            
        def csharp_runner():
            result = subprocess.getoutput('mono ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        def c_runner():
            subprocess.run('chmod 777 ' + title)
            result = subprocess.getoutput('./' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        def node_runner():
            result = subprocess.getoutput('node ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        def java_runner():
            result = subprocess.getoutput('java ' + file_name)
            self.future.set_result(None)
            show_message("Compiler", result)

        py_button = Button(text="Python", handler=python_runner)
        c_button = Button(text="C/C++", handler=c_runner)
        cs_button = Button(text="C#", handler=csharp_runner)
        js_button = Button(text="Node.js", handler=node_runner)
        jv_button = Button(text="Java", handler=java_runner)
        ok_button = Button(text="Cancel", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[py_button, c_button, cs_button, jv_button, js_button, ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class SyntaxHighDialog:
    def __init__(self, title="Syntax Highlighting", text=""):
        self.future = Future()

        def set_done():
            self.future.set_result(None)

        def def_syntax():
            text_field.lexer = None
            #text_field.lexer = PygmentsLexer(BlitzMaxLexer)
            self.future.set_result(None)

        def py_syntax():
            text_field.lexer = PygmentsLexer(Python3Lexer)
            self.future.set_result(None)

        def html_syntax():
            text_field.lexer = PygmentsLexer(HtmlLexer)
            self.future.set_result(None)

        def dotnet_syntax():
            text_field.lexer = PygmentsLexer(CSharpAspxLexer)
            self.future.set_result(None)

        def java_syntax():
            text_field.lexer = PygmentsLexer(JavaLexer)
            self.future.set_result(None)

        def bash_syntax():
            text_field.lexer = PygmentsLexer(BashLexer)
            self.future.set_result(None)

        def basic_syntax():
            text_field.lexer = PygmentsLexer(QBasicLexer)
            self.future.set_result(None)

        default_button = Button(text='Default', handler=def_syntax)
        basic_button = Button(text='Basic', handler=basic_syntax)
        bash_button = Button(text='Bash', handler=bash_syntax)
        python_button = Button(text='Python3', handler=py_syntax)
        dotnet_button = Button(text='DotNet', handler=dotnet_syntax)
        java_button = Button(text='Java', handler=java_syntax)
        cancel_button = Button(text="Cancel", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[default_button, bash_button,
                     python_button, dotnet_button, java_button, cancel_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class SyntaxLowDialog:
    def __init__(self, title="Syntax Highlighting", text=""):
        self.future = Future()

        def set_done():
            self.future.set_result(None)

        def def_syntax():
            text_field.lexer = None
            #text_field.lexer = PygmentsLexer(BlitzMaxLexer)
            self.future.set_result(None)

        def c_syntax():
            text_field.lexer = PygmentsLexer(CharmciLexer)
            self.future.set_result(None)
            
        def basic_syntax():
            text_field.lexer = PygmentsLexer(QBasicLexer)
            self.future.set_result(None)

        def nasm_syntax():
            text_field.lexer = PygmentsLexer(NasmLexer)
            self.future.set_result(None)

        default_button = Button(text='Default', handler=def_syntax)
        basic_button = Button(text='Basic', handler=basic_syntax)
        clike_button = Button(text='C like', handler=c_syntax)
        asm_button = Button(text='NASM', handler=nasm_syntax)
        cancel_button = Button(text="Cancel", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[default_button, basic_button, clike_button, asm_button, cancel_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog
        
        
class SyntaxWebDialog:
    def __init__(self, title="Syntax Highlighting", text=""):
        self.future = Future()

        def set_done():
            self.future.set_result(None)

        def def_syntax():
            text_field.lexer = None
            #text_field.lexer = PygmentsLexer(BlitzMaxLexer)
            self.future.set_result(None)

        def js_syntax():
            text_field.lexer = PygmentsLexer(JavascriptLexer)
            self.future.set_result(None)

        def html_syntax():
            text_field.lexer = PygmentsLexer(HtmlLexer)
            self.future.set_result(None)

        def basic_syntax():
            text_field.lexer = PygmentsLexer(QBasicLexer)
            self.future.set_result(None)

        def nasm_syntax():
            text_field.lexer = PygmentsLexer(NasmLexer)
            self.future.set_result(None)

        default_button = Button(text='Default', handler=def_syntax)
        basic_button = Button(text='Basic', handler=basic_syntax)
        javascript_button = Button(text='Javascript', handler=js_syntax)
        html_button = Button(text='HTML', handler=html_syntax)
        cancel_button = Button(text="Cancel", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[default_button, basic_button, javascript_button, html_button, cancel_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


body = HSplit(
    [
        text_field,
        search_toolbar,
        ConditionalContainer(
            content=VSplit(
                [
                    Window(
                        FormattedTextControl(get_statusbar_text), style="class:status"
                    ),
                    Window(
                        FormattedTextControl(get_statusbar_right_text),
                        style="class:status.right",
                        width=9,
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=Condition(lambda: ApplicationState.show_status_bar),
        ),
    ]
)


bindings = KeyBindings()


@bindings.add("c-c")
def _(event):
    event.app.layout.focus(root_container.window)


def do_open_file():
    async def coroutine():
        open_dialog = TextInputDialog(
            title="Open file",
            label_text="Enter the path of a file:",
            completer=PathCompleter(),
        )

        path = await show_dialog_as_float(open_dialog)
        ApplicationState.current_path = path

        if path is not None:
            try:
                with open(path, "rb") as f:
                    text_field.text = f.read().decode("utf-8", errors="ignore")
                global file_name
                file_name = path
            except IOError as e:
                show_message("Error", "{}".format(e))

    ensure_future(coroutine())


def do_exec_cmd():
    async def coroutine():
        open_dialog = TextInputDialog(
            title="Execute command",
            label_text="Enter the command:"
        )

        cmd = await show_dialog_as_float(open_dialog)
        res = subprocess.getoutput(cmd)
        show_message("Result", res)
        
    ensure_future(coroutine())


def do_about():
    show_message("About", "Text editor sample created by Jonathan Slenders\nand advanced options and features by TheDebianGuy")


def show_message(title, text):
    async def coroutine():
        dialog = MessageDialog(title, text)
        await show_dialog_as_float(dialog)

    ensure_future(coroutine())


async def show_dialog_as_float(dialog):
    float_ = Float(content=dialog)
    root_container.floats.insert(0, float_)

    app = get_app()

    focused_before = app.layout.current_window
    app.layout.focus(dialog)
    result = await dialog.future
    app.layout.focus(focused_before)

    if float_ in root_container.floats:
        root_container.floats.remove(float_)

    return result


def do_new_file():
    text_field.text = ""


def do_exit():
    get_app().exit()


def do_time_date():
    text = datetime.datetime.now().isoformat()
    text_field.buffer.insert_text(text)


def do_go_to():
    async def coroutine():
        dialog = TextInputDialog(title="Go to line", label_text="Line number:")

        line_number = await show_dialog_as_float(dialog)

        try:
            line_number = int(line_number)
        except ValueError:
            show_message("Error", "Invalid line number")
        else:
            text_field.buffer.cursor_position = (
                text_field.buffer.document.translate_row_col_to_index(
                    line_number - 1, 0
                )
            )

    ensure_future(coroutine())


def do_undo():
    text_field.buffer.undo()


def do_cut():
    data = text_field.buffer.cut_selection()
    get_app().clipboard.set_data(data)


def do_copy():
    data = text_field.buffer.copy_selection()
    get_app().clipboard.set_data(data)


def do_delete():
    text_field.buffer.cut_selection()


def do_find():
    start_search(text_field.control)


def do_find_next():
    search_state = get_app().current_search_state

    cursor_position = text_field.buffer.get_search_position(
        search_state, include_current_position=False
    )
    text_field.buffer.cursor_position = cursor_position


def do_paste():
    text_field.buffer.paste_clipboard_data(get_app().clipboard.get_data())


def do_select_all():
    text_field.buffer.cursor_position = 0
    text_field.buffer.start_selection()
    text_field.buffer.cursor_position = len(text_field.buffer.text)


def do_status_bar():
    ApplicationState.show_status_bar = not ApplicationState.show_status_bar

def add_note():
    ApplicationState.show_status_bar = not ApplicationState.show_status_bar


def save_file():
    async def coroutine():
        data = text_field.text
        if file_name != None:
            with open(file_name, "wb") as f:
                f.write(data.encode("utf-8", errors="ignore"))
        else:
            dialog = MessageDialog("Error", "File not found")
            await show_dialog_as_float(dialog)

    ensure_future(coroutine())


def save_as_file():
    async def coroutine():
        dialog = TextInputDialog(
            title="Save as",
            label_text="Enter the file name:"
        )
        global file_name
        file_name = await show_dialog_as_float(dialog)
        data = text_field.text
        with open(file_name, "wb") as f:
            f.write(data.encode("utf-8", errors="ignore"))

    ensure_future(coroutine())


def run_menu():
    async def coroutine():
        dialog = RunDialog()
        runner = await show_dialog_as_float(dialog)

    ensure_future(coroutine())


def compile_menu():
    async def coroutine():
        dialog = CompileDialog()
        compiler = await show_dialog_as_float(dialog)

    ensure_future(coroutine())


def syntax_high():
    async def coroutine():
        dialog = SyntaxHighDialog()
        syntax = await show_dialog_as_float(dialog)

    ensure_future(coroutine())
    
def syntax_low():
    async def coroutine():
        dialog = SyntaxLowDialog()
        syntax = await show_dialog_as_float(dialog)

    ensure_future(coroutine())

def syntax_web():
    async def coroutine():
        dialog = SyntaxWebDialog()
        syntax = await show_dialog_as_float(dialog)

    ensure_future(coroutine())


root_container = MenuContainer(
    body=body,
    menu_items=[
        MenuItem(
            "File",
            children=[
                MenuItem("New...", handler=do_new_file),
                MenuItem("Open...", handler=do_open_file),
                MenuItem("Save", handler=save_file),
                MenuItem("Save as...", handler=save_as_file),
                MenuItem("Run", handler=run_menu),
                MenuItem("Compile", handler=compile_menu),
                MenuItem("Execute", handler=do_exec_cmd),
                MenuItem("-", disabled=True),
                MenuItem("Exit", handler=do_exit),
            ],
        ),
        MenuItem(
            "Edit",
            children=[
                MenuItem("Undo", handler=do_undo),
                MenuItem("Cut", handler=do_cut),
                MenuItem("Copy", handler=do_copy),
                MenuItem("Paste", handler=do_paste),
                MenuItem("Delete", handler=do_delete),
                MenuItem("-", disabled=True),
                MenuItem("Find", handler=do_find),
                MenuItem("Find next", handler=do_find_next),
                MenuItem("Replace"),
                MenuItem("Go To", handler=do_go_to),
                MenuItem("Select All", handler=do_select_all),
                MenuItem("Time/Date", handler=do_time_date),
            ],
        ),
        MenuItem(
            "View",
            children=[
                MenuItem("Status Bar", handler=do_status_bar),
                #MenuItem("Add Note", handler=add_note), todo
                MenuItem("Syntax-High", handler=syntax_high),
                MenuItem("Syntax-Low", handler=syntax_low),
                MenuItem("Syntax-Web", handler=syntax_web),
                #MenuItem("Completion", handler=complete_menu),
                      ],
        ),
        MenuItem(
            "Info",
            children=[MenuItem("About", handler=do_about)],
        ),
    ],
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1),
        ),
    ],
    key_bindings=bindings,
)


style = Style.from_dict(
    {
        "status": "reverse",
        "shadow": "bg:#00ff00",
    }
)


layout = Layout(root_container, focused_element=text_field)


application = Application(
    layout=layout,
    enable_page_navigation_bindings=True,
    style=style,
    mouse_support=True,
    full_screen=True,
)


def run():
    application.run()

if __name__ == "__main__":
    run()
