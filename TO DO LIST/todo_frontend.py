"""Desktop frontend for the unchanged TO_DO_list.py (Python 3.9+)."""
import argparse
import ast
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

OPTION = 'Enter option (1 or 2 or 3 or or 4 or QUIT): '
ADD = 'Enter a task: '
REMOVE = 'Enter the task you want to remove exactly as you mentioned above: '


class BackendAdapter:
    """One persistent interpreter; call methods from a single worker thread."""
    def __init__(self, path, timeout=8):
        self.timeout = timeout
        self.output = queue.Queue()
        self.tasks = []
        self.closed = False
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
        self.process = subprocess.Popen(
            [sys.executable, '-u', str(Path(path).resolve())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, bufsize=0,
        )
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self._until(OPTION)
        except Exception:
            self.close()
            raise

    def _read(self):
        import codecs
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        try:
            while True:
                chunk = self.process.stdout.read(1024)
                if not chunk:
                    break
                self.output.put(decoder.decode(chunk))
            tail = decoder.decode(b'', final=True)
            if tail:
                self.output.put(tail)
        finally:
            self.output.put(None)

    def _until(self, prompt):
        result = ''
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('Backend stopped responding. Close and reopen the app.\n' + result[-1500:])
            try:
                chunk = self.output.get(timeout=remaining)
            except queue.Empty:
                raise RuntimeError('Timed out waiting for the backend. Close and reopen the app.')
            if chunk is None:
                raise RuntimeError('Backend exited unexpectedly.\n' + result[-1500:])
            result += chunk
            if result.endswith(prompt):
                return result[:-len(prompt)]

    def _send(self, value):
        if self.closed or self.process.poll() is not None:
            raise RuntimeError('Backend is no longer running.')
        if '\n' in value or '\r' in value:
            raise ValueError('Tasks must fit on one line.')
        self.process.stdin.write((value + '\n').encode('utf-8'))
        self.process.stdin.flush()

    def change(self, operation, task):
        if operation not in ('1', '2'):
            raise ValueError('Unsupported operation')
        if '\n' in task or '\r' in task:
            raise ValueError('Tasks must fit on one line.')
        self._send(operation)
        before = self._until(ADD if operation == '1' else REMOVE)
        self._send(task)
        response = self._until(OPTION)
        # add_task/rm_task both print Python's list representation. Literal
        # parsing preserves quotes, duplicates, whitespace and Unicode safely.
        for line in reversed(response.splitlines()):
            try:
                value = ast.literal_eval(line)
            except (ValueError, SyntaxError):
                continue
            if isinstance(value, list) and all(isinstance(x, str) for x in value):
                self.tasks = value
                return list(value), before + response
        raise RuntimeError('Could not read the task list from the backend.\n' + response)

    def view(self):
        self._send('3')
        return list(self.tasks), self._until(OPTION)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.process.poll() is None:
                self.process.stdin.write(b'QUIT\n')
                self.process.stdin.flush()
                self.process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()


def run_gui(backend):
    try:
        import customtkinter as ctk
        from tkinter import messagebox
    except ImportError as exc:
        raise SystemExit('Install CustomTkinter with: python -m pip install customtkinter\n'
                         'Your Python installation must also include Tkinter.') from exc

    ctk.set_appearance_mode('dark')
    app = ctk.CTk()
    app.title('Tasks')
    app.geometry('960x820')
    app.minsize(680, 660)
    app.configure(fg_color='#080D18')
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(2, weight=1)
    font = 'Helvetica Neue' if sys.platform == 'darwin' else 'Segoe UI'
    ink, muted, blue = '#F5F7FC', '#A4B1C8', '#79BDFF'
    glass, edge, tile = '#172235', '#3D506B', '#202E43'

    nav = ctk.CTkFrame(app, fg_color='#101A2B', corner_radius=0, height=62,
                       border_width=1, border_color='#293B55')
    nav.grid(row=0, column=0, sticky='ew')
    nav.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(nav, text='Tasks', text_color=ink,
                 font=(font, 21, 'bold')).grid(row=0, column=0, padx=36, pady=16, sticky='w')
    ctk.CTkLabel(nav, text='A little focus. A lot of possibility.',
                 text_color=muted, font=(font, 12)).grid(row=0, column=1, padx=36)

    hero = ctk.CTkFrame(app, fg_color='transparent')
    hero.grid(row=1, column=0, padx=40, pady=(30, 24), sticky='ew')
    hero.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(hero, text='MAKE ROOM FOR WHAT MATTERS', text_color=muted,
                 font=(font, 11, 'bold')).grid(row=0, column=0, sticky='w')
    ctk.CTkLabel(hero, text='Less noise. More done.', text_color=ink,
                 font=(font, 38, 'bold')).grid(row=1, column=0, pady=(8, 4), sticky='w')
    ctk.CTkLabel(hero, text='One task at a time. All in one place.', text_color=muted,
                 font=(font, 16)).grid(row=2, column=0, sticky='w')

    # Layered opaque tints and a light-catching rim simulate glass without
    # platform-specific blur APIs or transparent text surfaces.
    shell = ctk.CTkFrame(app, fg_color='#101C30', corner_radius=30,
                         border_width=1, border_color='#284363')
    shell.grid(row=2, column=0, padx=32, sticky='nsew')
    shell.grid_columnconfigure(0, weight=1)
    shell.grid_rowconfigure(0, weight=1)
    panel = ctk.CTkFrame(shell, fg_color=glass, corner_radius=26,
                         border_width=1, border_color=edge)
    panel.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
    # A restrained upper highlight gives the surface a reflective edge.
    sheen = ctk.CTkFrame(panel, height=2, corner_radius=1, fg_color='#7693B8')
    sheen.place(relx=0.18, rely=0, relwidth=0.64, y=1)
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(2, weight=1)
    heading = ctk.CTkFrame(panel, fg_color='transparent')
    heading.grid(row=0, column=0, padx=24, pady=(20, 12), sticky='ew')
    heading.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(heading, text='Your tasks', text_color=ink,
                 font=(font, 21, 'bold')).grid(row=0, column=0, sticky='w')
    count = ctk.CTkLabel(heading, text='0 tasks', text_color='#C5DFFF', font=(font, 13),
                          fg_color='#263C57', corner_radius=12, width=78, height=28)
    count.grid(row=0, column=1)
    bar = ctk.CTkFrame(panel, fg_color='transparent')
    bar.grid(row=1, column=0, padx=24, pady=(0, 12), sticky='ew')
    bar.grid_columnconfigure(0, weight=1)
    entry = ctk.CTkEntry(bar, placeholder_text='What would you like to get done?',
                         height=48, corner_radius=12, border_width=1,
                         border_color='#465C79', fg_color='#0E192A',
                         placeholder_text_color='#9BAAC1',
                         text_color=ink, font=(font, 14))
    entry.grid(row=0, column=0, sticky='ew', padx=(0, 12))
    task_area = ctk.CTkScrollableFrame(panel, fg_color='transparent',
                                      scrollbar_button_color='#405776',
                                      scrollbar_button_hover_color='#6282A9')
    task_area.grid(row=2, column=0, padx=16, pady=(0, 8), sticky='nsew')
    task_area.grid_columnconfigure(0, weight=1)
    actions = ctk.CTkFrame(panel, fg_color='transparent')
    actions.grid(row=3, column=0, padx=24, pady=(6, 20), sticky='ew')
    actions.grid_columnconfigure(0, weight=1)
    selection_label = ctk.CTkLabel(actions, text='Select a task to manage it.',
                                   text_color=muted, font=(font, 12))
    selection_label.grid(row=0, column=0, sticky='w')
    status = ctk.CTkLabel(app, text='Getting things ready…', text_color=muted,
                          font=(font, 12), anchor='w')
    status.grid(row=3, column=0, padx=40, pady=(12, 0), sticky='ew')
    ctk.CTkLabel(app, text='A fresh start each session. Tasks are kept until you close the app.',
                 text_color=muted, font=(font, 11)).grid(row=4, column=0, pady=(4, 18))
    current_tasks = []
    selected_index = None
    row_buttons = []

    def select_task(index):
        nonlocal selected_index
        if busy or not ready:
            return
        selected_index = index
        for i, button in enumerate(row_buttons):
            button.configure(fg_color='#29486B' if i == index else tile,
                             border_color=blue if i == index else '#3A4E69')
        selection_label.configure(text='1 task selected')
        set_controls(True)

    def render_tasks(data):
        nonlocal current_tasks, selected_index
        current_tasks = list(data)
        selected_index = None
        row_buttons.clear()
        for child in task_area.winfo_children():
            child.destroy()
        count.configure(text=f'{len(data)} task' + ('' if len(data) == 1 else 's'))
        selection_label.configure(text='Select a task to manage it.')
        if not data:
            ctk.CTkLabel(task_area, text='A clear space. A fresh start.', text_color=ink,
                         font=(font, 22, 'bold')).grid(row=0, column=0, pady=(34, 4))
            ctk.CTkLabel(task_area, text='Add your first task above and take it from there.',
                         text_color=muted, font=(font, 14)).grid(row=1, column=0, pady=(0, 30))
        for index, task in enumerate(data):
            button = ctk.CTkButton(task_area, text=task, anchor='w', height=54,
                                   corner_radius=16, border_width=1, border_color='#3A4E69',
                                   fg_color=tile, hover_color='#2B3E59',
                                   text_color_disabled='#7D8DA7',
                                   text_color=ink, font=(font, 15),
                                   command=lambda i=index: select_task(i))
            button.grid(row=index, column=0, padx=4, pady=4, sticky='ew')
            row_buttons.append(button)
    render_tasks([])
    commands, results = queue.Queue(), queue.Queue()
    stopping = threading.Event()
    ready = False
    busy = True

    def worker():
        adapter = None
        try:
            adapter = BackendAdapter(backend)
            results.put(('ok', [], 'Backend ready.', False))
            while not stopping.is_set():
                command = commands.get()
                if command is None:
                    break
                operation, value = command
                data, transcript = adapter.view() if operation == '3' else adapter.change(operation, value)
                results.put(('ok', data, transcript, operation == '1'))
        except Exception as exc:
            results.put(('error', [], str(exc), False))
        finally:
            if adapter:
                adapter.close()
            results.put(('stopped', [], '', False))

    def submit(operation):
        nonlocal busy
        if busy or not ready:
            return
        value = entry.get()
        if operation == '1' and not value.strip():
            messagebox.showinfo('Add a task', 'Enter a task first.', parent=app)
            return
        if operation == '2':
            if selected_index is None:
                messagebox.showinfo('Remove a task', 'Select a task first.', parent=app)
                return
            value = current_tasks[selected_index]
        if '\r' in value or '\n' in value:
            messagebox.showerror('One line per task', 'Remove line breaks from the task.', parent=app)
            return
        busy = True
        set_controls(False)
        status.configure(text='Working…')
        commands.put((operation, value))

    add_button = ctk.CTkButton(bar, text='Add task', width=112, height=48,
                               corner_radius=24, fg_color='#A3D2FF', hover_color='#C0E1FF',
                               text_color='#08213D', border_width=1, border_color='#DAEDFF',
                               text_color_disabled='#71839B',
                               font=(font, 14), command=lambda: submit('1'))
    add_button.grid(row=0, column=1)
    remove_button = ctk.CTkButton(actions, text='Remove', width=90, height=34,
                                  corner_radius=17, fg_color='#392936', text_color='#FFB7BF',
                                  border_width=1, border_color='#67404D',
                                  text_color_disabled='#8E7380', hover_color='#513342', command=lambda: submit('2'))
    remove_button.grid(row=0, column=1, padx=(12, 8))
    view_button = ctk.CTkButton(actions, text='Refresh', width=90, height=34,
                                corner_radius=17, fg_color='#263A53', text_color='#C5E2FF',
                                border_width=1, border_color='#4A6585',
                                text_color_disabled='#798AA3', hover_color='#354E6D', command=lambda: submit('3'))
    view_button.grid(row=0, column=2)
    entry.bind('<Return>', lambda event: submit('1'))

    def set_controls(enabled):
        for button in (add_button, view_button):
            button.configure(state='normal' if enabled else 'disabled')
        remove_button.configure(state='normal' if enabled and selected_index is not None else 'disabled')
        for button in row_buttons:
            button.configure(state='normal' if enabled else 'disabled')

    def poll():
        nonlocal busy, ready
        try:
            while True:
                kind, data, transcript, clear = results.get_nowait()
                if kind == 'ok':
                    ready, busy = True, False
                    render_tasks(data)
                    if clear:
                        entry.delete(0, 'end')
                    status.configure(text='All up to date.')
                    set_controls(True)
                elif kind == 'error':
                    ready, busy = False, False
                    set_controls(False)
                    status.configure(text='Backend error — close and reopen the app')
                    messagebox.showerror('Backend error', transcript, parent=app)
                elif kind == 'stopped':
                    ready = False
                    set_controls(False)
        except queue.Empty:
            pass
        if not stopping.is_set():
            app.after(75, poll)

    def close():
        stopping.set()
        commands.put(None)
        set_controls(False)
        status.configure(text='Closing backend…')
        def finish():
            if thread.is_alive():
                app.after(75, finish)
            else:
                app.destroy()
        finish()

    app.protocol('WM_DELETE_WINDOW', close)
    set_controls(False)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    poll()
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, default=Path(__file__).resolve().with_name('TO_DO_list.py'))
    args = parser.parse_args()
    if not args.backend.is_file():
        parser.error(f'Backend file not found: {args.backend}. Put TO_DO_list.py beside this file or use --backend PATH.')
    run_gui(args.backend)


if __name__ == '__main__':
    main()
