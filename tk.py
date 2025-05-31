import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import os
import re
import compile as c
import mcmd as cmd
import requests
import json
import threading

i = 0

# === Константы для ИИ-агента ===
API_KEY = "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"
MODEL = "google/gemma-3n-e4b-it:free"

def process_content(content):
    """Очистка ответа от служебных маркеров"""
    return content.replace('**', '').replace('**', '').replace('*', '')

class FileTab:
    def __init__(self, name="Безымянный.tcd", content="", path=None):
        self.name = name
        self.content = content
        self.path = path
        self.saved = True

class CodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("T-Code App betta")
        self.geometry("1000x600")
        self.configure(bg="#f0f4f8")
        self.colors = {
            "bg": "#373a3b",
            "editor_bg": "#32393B",
            "editor_fg": "#FFFFFF",
            "line_numbers": "#2C3031",
            "tab_bg": "#7e7f80",
            "tab_active": "#496270",
            "btn_normal": "#8f9ca0",
            "btn_hover": "#373a3b",
            "debugger_bg": "#2c3e50",
            "debugger_fg": "#ecf0f1",
            "cmd_bg": "#141619",
            "cmd_fg": "#b0eaff"
        }
        
        # === Инициализация интерфейса ===
        self.create_widgets()
        
        # === Запуск ИИ-агента ===
        self.init_ai_agent()
        
    def is_code_related(self, question):
        """Проверяет, относится ли вопрос к коду"""
        keywords = [
            'ошибка', 'код', 'исправь', 'почему не работает', 'почему не запускается',
            'error', 'code', 'fix', 'debug', 'баг', 'как сделать', 'почему',
            'объясни', 'что делает', 'функци', 'метод', 'класс', 'синтаксис'
        ]
        question = question.lower()
        return any(kw in question for kw in keywords)
    
    
    def create_widgets(self):
        """Создание основных элементов интерфейса"""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", 
                       font=("Consolas bold", 9, "bold"),
                       padding=[8, 3],
                       background=self.colors["tab_bg"],
                       foreground="#2d3436")
        style.map("TNotebook.Tab", 
                 background=[("selected", self.colors["tab_active"])])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Side.TButton",
                       font=("Consolas", 12),
                       padding=2,
                       relief="flat",
                       background=self.colors["btn_normal"],
                       foreground="#222")
        style.map("Side.TButton",
                 background=[("active", self.colors["btn_hover"])])
        style.configure("TScrollbar", background="#e0e0e0", troughcolor="#f5f5f5")

        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Левая панель с кнопками
        button_frame = ttk.Frame(main_pane, width=38, style="TFrame")
        button_frame.pack_propagate(False)
        main_pane.add(button_frame, weight=0)

        self.new_button = ttk.Button(button_frame, text="＋", style="Side.TButton", width=2, command=self.new_file)
        self.new_button.pack(pady=(10, 4), padx=4)
        self.run_button = ttk.Button(button_frame, text="▶", style="Side.TButton", width=2, command=self.run_code)
        self.run_button.pack(pady=4, padx=4)
        self.save_button = ttk.Button(button_frame, text="💾", style="Side.TButton", width=2, command=self.save_file)
        self.save_button.pack(pady=4, padx=4)
        self.load_button = ttk.Button(button_frame, text="📂", style="Side.TButton", width=2, command=self.load_file)
        self.load_button.pack(pady=4, padx=4)
        self.help_button = ttk.Button(button_frame, text="❓", style="Side.TButton", width=2, command=self.open_help)
        self.help_button.pack(pady=(4, 4), padx=4)
        self.arrow_button = ttk.Button(button_frame, text="⚙️", style="Side.TButton", width=2, command=self.setings)
        self.arrow_button.pack(pady=(4, 10), padx=4)

        # Центральная панель с редактором
        editor_frame = ttk.Frame(main_pane, style="TFrame")
        main_pane.add(editor_frame, weight=3)

        self.file_notebook = ttk.Notebook(editor_frame)
        self.file_notebook.pack(fill=tk.BOTH, expand=True, side=tk.TOP, padx=0, pady=(0, 4))
        self.file_tabs = []
        self.file_editors = []
        self.file_notebook.bind("<<NotebookTabChanged>>", self.switch_file_tab)
        self.file_notebook.enable_traversal()
        self.new_file()

        self.bind_all("<Control-o>", lambda e: self.load_file())
        self.bind_all("<Control-O>", lambda e: self.load_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())
        self.bind_all("<Control-S>", lambda e: self.save_file())
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-Z>", self.undo)
        self.bind("<F5>", lambda e: self.run_code())

        right_frame = ttk.Frame(main_pane, style="TFrame")
        main_pane.add(right_frame, weight=2)

        self.notebook = ttk.Notebook(right_frame, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=2, padx=2)

        # === Добавление вкладок ===
        self.view_frame = tk.Frame(self.notebook, bg="#fff")
        self.notebook.add(self.view_frame, text="View")

        self.debugger = tk.Text(self.notebook, height=6, bg=self.colors["debugger_bg"], 
                              fg=self.colors["debugger_fg"], font=("Consolas", 9),
                              insertbackground=self.colors["debugger_fg"],
                              selectbackground="#3a74b1", bd=0, relief="flat", padx=4, pady=4)
        self.debugger.pack_propagate(False)
        self.debugger.config(state="disabled")
        self.debugger.bind("<1>", lambda event: self.debugger.focus_set())
        self.notebook.add(self.debugger, text="Debugger")

        cmd_frame = tk.Frame(self.notebook, bg=self.colors["cmd_bg"])
        self.notebook.add(cmd_frame, text="CMD")

        self.cmd_output = tk.Text(cmd_frame, height=6, bg=self.colors["cmd_bg"], 
                                fg=self.colors["cmd_fg"], font=("Consolas", 9),
                                insertbackground=self.colors["cmd_fg"],
                                selectbackground="#3a74b1", bd=0, relief="flat", 
                                state="disabled", padx=4, pady=4)
        self.cmd_output.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 30))

        cmd_entry_frame = tk.Frame(cmd_frame, bg=self.colors["cmd_bg"])
        cmd_entry_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=(0, 2))

        self.cmd_entry = tk.Entry(cmd_entry_frame, bg="#23272e", fg=self.colors["cmd_fg"],
                                font=("Consolas", 9), insertbackground=self.colors["cmd_fg"],
                                relief="flat")
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 2))
        self.cmd_entry.bind("<Return>", self.process_cmd)

        global output
        output = self.output
        self._debugger_insert("Programm started.\n")
        self._debugger_insert(f"T-Code ver.0.1 betta by PiCore team in 2025.\n")

    def init_ai_agent(self):
        """Инициализация ИИ-агента"""
        ai_frame = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(ai_frame, text="AI Agent")

        # Область вывода
        self.ai_output = tk.Text(ai_frame, wrap='word',
                               bg=self.colors["debugger_bg"],
                               fg=self.colors["debugger_fg"],
                               font=("Consolas", 10),
                               state="disabled",
                               padx=6, pady=6,
                               height=12)
        self.ai_output.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Поле ввода и кнопка
        input_frame = tk.Frame(ai_frame, bg=self.colors["bg"])
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(0, 6))

        self.ai_input = tk.Entry(input_frame,
                               bg="#23272e",
                               fg=self.colors["cmd_fg"],
                               font=("Consolas", 10),
                               insertbackground=self.colors["cmd_fg"],
                               relief="flat")
        self.ai_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        self.send_button = ttk.Button(input_frame, text="➤", style="Side.TButton",
                                    width=2, command=self.start_ai_query)
        self.send_button.pack(side=tk.RIGHT, padx=(4, 0))

        self.ai_input.bind("<Return>", lambda e: self.start_ai_query())

    def start_ai_query(self):
        """Начало запроса к ИИ"""
        user_input = self.ai_input.get().strip()
        if not user_input:
            return
        
        self.ai_input.delete(0, tk.END)
        self._ai_insert(f"Вы: {user_input}\n")
        
        # Добавляем индикатор обработки
        self._ai_insert("AI: ")
        
        # Запуск в отдельном потоке
        threading.Thread(
            target=self.run_ai_query,
            args=(user_input,),
            daemon=True
        ).start()

    def run_ai_query(self, prompt):
        """Выполнение запроса к ИИ в отдельном потоке"""
        def update_output(text):
            self.ai_output.after(0, self._ai_insert, text)

        try:
            # Получаем текущий код
            try:
                tab, editor, _ = self.get_current_editor()
                current_code = editor.get("1.0", "end-1c").strip()
            except Exception as e:
                current_code = ""
                print(f"Ошибка получения кода: {e}")

            # Формируем финальный промпт
            final_prompt = prompt
            if current_code and self.is_code_related(prompt):
                update_output("\n[Анализирую текущий код...]\n")
                final_prompt = (
                    f"Текущий код пользователя:\n```python\n{current_code}\n```\n\n"
                    f"Вопрос: {prompt}\n\n"
                    "Ответь максимально конкретно, указывая номера строк если возможно. "
                    "Если видишь ошибки - предложи исправленный код."
                )

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t-code-app.com",
                "X-Title": "T-Code App"
            }
            data = {
                "model": MODEL,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.3,
                "stream": True
            }


            with requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                stream=True
            ) as response:
                if response.status_code != 200:
                    error_body = response.text
                    update_output(f"\nОшибка API {response.status_code}: {error_body}\n")
                    return

                full_response = []
                
                for chunk in response.iter_lines():
                    if chunk:
                        try:
                            chunk_str = chunk.decode('utf-8').strip()
                            if not chunk_str:
                                continue
                                
                            if chunk_str.startswith('data: '):
                                chunk_str = chunk_str[6:]
                                
                            if chunk_str == '[DONE]':
                                break

                            chunk_json = json.loads(chunk_str)
                            if "choices" in chunk_json:
                                content = chunk_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    cleaned = process_content(content)
                                    update_output(cleaned)
                                    full_response.append(cleaned)
                        except json.JSONDecodeError as e:
                            print(f"Ошибка декодирования JSON: {e}\nДанные: {chunk_str}")
                            continue
                        except Exception as e:
                            print(f"Ошибка обработки чанка: {e}")
                            continue

                update_output("\n")
        except Exception as e:
            update_output(f"\nОшибка сети: {e}\n")

    def _ai_insert(self, text):
        """Вставка текста в область ИИ"""
        self.ai_output.config(state="normal")
        self.ai_output.insert(tk.END, text)
        self.ai_output.see(tk.END)
        self.ai_output.config(state="disabled")

    # === Остальные методы класса (без изменений) ===
    def setings(self):
        set_window = tk.Tk()
        set_window.title("Settings")
        set_window.geometry("300x400")
        set_window['bg'] = "#7d8285"
        set_window.resizable(False, False)
        frame_top = tk.Frame(set_window, bg="#585a5c", bd=5)
        frame_top.place(relx=0, rely=0, relwidth=1, relheight=1)
        btn = tk.Button(frame_top, text='test', command=None)
        btn.pack()
    
    def insert_spaces(self, event=None):
        widget = event.widget
        widget.insert(tk.INSERT, '    ')
        return "break"
    
    def auto_indent(self, event):
        widget = event.widget
        index = widget.index("insert linestart")
        prev_line = widget.get(f"{index} -1l linestart", f"{index} -1l lineend")
        indent = re.match(r"^(\s*)", prev_line).group(1)
        if prev_line.rstrip().endswith(":"):
            indent += "    "
        widget.insert("insert", f"\n{indent}")
        return "break"
    
    def highlight_syntax(self, event=None):
        try:
            _, input_text, _ = self.get_current_editor()
        except Exception:
            return
        code = input_text.get("1.0", "end-1c")
        for tag in input_text.tag_names():
            input_text.tag_remove(tag, "1.0", "end")
        # Ключевые слова Python
        keywords = r"\b(!|False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b"
        for match in re.finditer(keywords, code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            input_text.tag_add("keyword", start, end)
        input_text.tag_config("keyword", foreground="#d67bd2")
        # Строки
        for match in re.finditer(r'".*?"|\'.*?\'', code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            input_text.tag_add("string", start, end)
        input_text.tag_config("string", foreground="#81b463")
        # Комментарии
        for match in re.finditer(r"#.*", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            input_text.tag_add("comment", start, end)
        input_text.tag_config("comment", foreground="#8490a1")
    
    def new_file(self):
        tab = FileTab()
        frame = ttk.Frame(self.file_notebook)
        line_numbers = tk.Text(frame, width=2, padx=2, takefocus=0, border=0,
                             background=self.colors["line_numbers"], state='disabled', wrap='none',
                             font=("Consolas", 10), fg="#888")
        line_numbers.pack(side=tk.LEFT, fill=tk.Y, pady=2)
        input_text = tk.Text(frame, wrap='none', undo=True, font=("Consolas", 10),
                           background=self.colors["editor_bg"], foreground=self.colors["editor_fg"], 
                           insertbackground="#3a74b1", selectbackground="#e5f2ff",
                           bd=1, relief="flat", padx=4, pady=4)
        input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, 
                             command=lambda *args: (input_text.yview(*args), line_numbers.yview(*args)))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        input_text.config(yscrollcommand=lambda *args: (scroll.set(*args), line_numbers.yview_moveto(args[0])))
        line_numbers.config(yscrollcommand=scroll.set)
        # Привязка событий
        input_text.bind("<Tab>", self.insert_spaces)
        input_text.bind("<Return>", self.auto_indent)
        input_text.bind("<KeyRelease>", lambda e: [self.update_line_numbers_tab(input_text, line_numbers), self.highlight_syntax()])
        input_text.bind("<Button-1>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
        input_text.bind("<Configure>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
        input_text.bind("<FocusIn>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
        input_text.bind("<MouseWheel>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
        line_numbers.bind("<MouseWheel>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
        tab_text = f"{tab.name}  ×"
        self.file_notebook.add(frame, text=tab_text)
        self.file_tabs.append(tab)
        self.file_editors.append((line_numbers, input_text))
        self.file_notebook.select(len(self.file_tabs) - 1)
        self.update_line_numbers_tab(input_text, line_numbers)
    
    def load_file(self):
        filetypes = [
            ("T-Code files", "*.tcd"),
            ("Python files", "*.py"),
            ("All files", "*.*")
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tab = FileTab(name=os.path.basename(filepath), content=content, path=filepath)
            frame = ttk.Frame(self.file_notebook)
            line_numbers = tk.Text(frame, width=2, padx=2, takefocus=0, border=0,
                                 background=self.colors["line_numbers"], state='disabled', wrap='none',
                                 font=("Consolas", 10), fg="#888")
            line_numbers.pack(side=tk.LEFT, fill=tk.Y, pady=2)
            input_text = tk.Text(frame, wrap='none', undo=True, font=("Consolas", 10),
                               background=self.colors["editor_bg"], foreground=self.colors["editor_fg"], 
                               insertbackground="#3a74b1", selectbackground="#e5f2ff",
                               bd=1, relief="flat", padx=4, pady=4)
            input_text.insert("1.0", content)
            input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2)
            scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, 
                                 command=lambda *args: (input_text.yview(*args), line_numbers.yview(*args)))
            scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
            input_text.config(yscrollcommand=lambda *args: (scroll.set(*args), line_numbers.yview_moveto(args[0])))
            line_numbers.config(yscrollcommand=scroll.set)
            # Привязка событий
            input_text.bind("<Tab>", self.insert_spaces)
            input_text.bind("<Return>", self.auto_indent)
            input_text.bind("<KeyRelease>", lambda e: [self.update_line_numbers_tab(input_text, line_numbers), self.highlight_syntax()])
            input_text.bind("<Button-1>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
            input_text.bind("<Configure>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
            input_text.bind("<FocusIn>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
            input_text.bind("<MouseWheel>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
            line_numbers.bind("<MouseWheel>", lambda e: self.update_line_numbers_tab(input_text, line_numbers))
            self.file_notebook.add(frame, text=tab.name + "  ×")
            self.file_tabs.append(tab)
            self.file_editors.append((line_numbers, input_text))
            self.file_notebook.select(len(self.file_tabs) - 1)
            self.update_line_numbers_tab(input_text, line_numbers)
            self.highlight_syntax()
            messagebox.showinfo("Загрузка", f"Файл успешно загружен:\n{filepath}")
    
    def close_tab_event(self, event):
        x, y = event.x, event.y
        for idx, tab_id in enumerate(self.file_notebook.tabs()):
            bbox = self.file_notebook.bbox(tab_id)
            if bbox and bbox[0] <= x <= bbox[0] + bbox[2] and bbox[1] <= y <= bbox[1] + bbox[3]:
                tab_text = self.file_notebook.tab(tab_id, "text")
                if tab_text.endswith("×") and x > bbox[0] + bbox[2] - 20:
                    self.close_file_tab(idx)
                    break
    
    def close_file_tab(self, idx):
        if len(self.file_tabs) == 0:
            return
        if len(self.file_tabs) == 1:
            self.file_notebook.forget(idx)
            del self.file_tabs[idx]
            del self.file_editors[idx]
            self.new_file()
            return
        if idx < len(self.file_tabs):
            self.file_notebook.forget(idx)
            del self.file_tabs[idx]
            del self.file_editors[idx]
    
    def switch_file_tab(self, event=None):
        idx = self.file_notebook.index(self.file_notebook.select())
        line_numbers, input_text = self.file_editors[idx]
        self.update_line_numbers_tab(input_text, line_numbers)
        self.highlight_syntax()
    
    def get_current_editor(self):
        idx = self.file_notebook.index(self.file_notebook.select())
        return self.file_tabs[idx], self.file_editors[idx][1], self.file_editors[idx][0]
    
    def update_line_numbers_tab(self, input_text, line_numbers):
        line_numbers.config(state='normal')
        line_numbers.delete('1.0', tk.END)
        line_count = int(input_text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        line_numbers.insert('1.0', line_numbers_string)
        line_numbers.config(state='disabled')
    
    def update_line_numbers(self, event=None):
        _, input_text, line_numbers = self.get_current_editor()
        self.update_line_numbers_tab(input_text, line_numbers)
    
    def output(self, text):
        self._debugger_insert(str(text) + "\n")
    
    def run_code(self):
        global i
        i += 1
        self._debugger_insert(str("") + "\n")
        self._debugger_insert(f"Output {i} ==========\n")
        _, input_text, _ = self.get_current_editor()
        code = input_text.get("1.0", tk.END).strip()
        if not code:
            self.output("Пустой ввод")
            return
        compiled = c.t_compile(code)
        self.output(compiled)
        self._debugger_insert("\n")
    
    def save_file(self):
        tab, input_text, _ = self.get_current_editor()
        filetypes = [
            ("T-Code files", "*.tcd"),
            ("Python files", "*.py"),
            ("All files", "*.*")
        ]
        if tab.path is None:
            filepath = filedialog.asksaveasfilename(defaultextension=".tcd", filetypes=filetypes)
            if not filepath:
                return
            tab.path = filepath
            tab.name = os.path.basename(filepath)
            self.file_notebook.tab(self.file_notebook.select(), text=tab.name + "  ×")
        else:
            filepath = tab.path
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(input_text.get("1.0", tk.END))
            tab.saved = True
            messagebox.showinfo("Сохранение", f"Файл успешно сохранён:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")
    
    def open_help(self):
        help_path = os.path.join(os.path.dirname(__file__), "documentation", "help.md")
        if os.path.exists(help_path):
            webbrowser.open_new_tab(f"file://{help_path}")
        else:
            messagebox.showerror("Ошибка", "Файл помощи documentation/help.md не найден!")
    
    def process_cmd(self, event=None):
        cmd_text = self.cmd_entry.get().strip()
        if not cmd_text:
            return
        self.cmd_output.config(state="normal")
        self.cmd_output.insert(tk.END, f"> {cmd_text}\n")
        try:
            result = cmd.compile(cmd_text)
        except Exception as e:
            result = f"Ошибка: {e}"
        self.cmd_output.insert(tk.END, str(result) + "\n")
        self.cmd_output.see(tk.END)
        self.cmd_output.config(state="disabled")
        self.cmd_entry.delete(0, tk.END)
    
    def _debugger_insert(self, text):
        self.debugger.config(state="normal")
        self.debugger.insert(tk.END, str(text))
        self.debugger.see(tk.END)
        self.debugger.config(state="disabled")
    
    def undo(self, event=None):
        try:
            _, input_text, _ = self.get_current_editor()
            input_text.edit_undo()
        except Exception:
            pass

if __name__ == "__main__":
    app = CodeApp()
    app.mainloop()
