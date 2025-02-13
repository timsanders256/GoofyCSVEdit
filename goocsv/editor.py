import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
from datetime import datetime

class AddRowDialog:
    def __init__(self, parent, max_rows):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Row")
        self.dialog.geometry("300x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
       
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()/2 - 150,
            parent.winfo_rooty() + parent.winfo_height()/2 - 75))
        
        # Add explanation label
        ttk.Label(self.dialog, text=f"Select where to insert the new row: 0 - {max_rows}",
                 wraplength=250).pack(pady=10)
        
        # Add spinbox for row selection
        self.row_var = tk.StringVar(value="0")
        self.spin = ttk.Spinbox(self.dialog, from_=0, to=max_rows, 
                               textvariable=self.row_var)
        self.spin.pack(pady=10)
        
        # Add explanation text
        ttk.Label(self.dialog, text="(Insert after your number)\n", 
                 wraplength=250).pack(pady=5)
        
        # Add buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.dialog.bind("<Return>", lambda e: self.ok())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
    def ok(self):
        try:
            self.result = int(self.spin.get())
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
            
    def cancel(self):
        self.dialog.destroy()

class CSVEditorApp:
    def __init__(self, master):
        self.master = master
        self.filename = None
        self.current_row = 0
        self.headers = []
        self.rows = []
        self.column_visibility = []
        self.modified = False
        self.main_frame = None
        self.current_row_values = []
        self.texts = []
        self.search_popup_on = False
        
        # Configure style
        self.style = ttk.Style()
        #self.style.theme_use('clam')
        self.style.configure('TButton', padding=5)
        self.style.configure('Header.TCheckbutton', background='#f0f0f0')
        
        self.master.title("GoofyCSVEdit")
        self.master.geometry("800x600")
        
        # Create sample data
        self.create_sample_data()
        self.create_widgets()
        self.update_data_display()

        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="Select All", command=self.menu_select_all)
        self.context_menu.add_command(label="Search", command=self.menu_search)
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cut", command=self.menu_cut)
        self.context_menu.add_command(label="Copy", command=self.menu_copy)
        self.context_menu.add_command(label="Paste", command=self.menu_paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Undo", command=self.menu_undo)
        self.context_menu.add_command(label="Delete", command=self.menu_delete)

        # Bind left-click on master to hide the context menu
        self.master.bind("<Button-1>", lambda e: self.context_menu.unpost())
   
        # When window lost focus, hide the context menu
        self.master.bind("<FocusOut>", lambda e: self.context_menu.unpost())
    
    def on_close(self):
        if self.modified:
            if messagebox.askyesno("Save Changes", "Do you want to save changes to the current file?"):
                self.save_changes()
        self.master.destroy()
    
    def map_visible_idx_to_col_idx(self, col_idx):
        """Map the visible column index to the actual column index in the data."""
        # find the pair from self.column_visibility that is the col_idx+1 th visible
        col_idx_converted = 0
        for i, visible in enumerate(self.column_visibility):
            if visible:
                if col_idx_converted == col_idx:
                    return i
                col_idx_converted += 1
        return -1

    def show_context_menu(self, event):
        """Show the shared context menu at the right-click location."""
        self.current_context_entry = event.widget
        self.context_menu.post(event.x_root, event.y_root)

    def handle_undo(self, event):
        """Revert the text widget to its original value."""
        widget = event.widget
        col_idx = widget.col_idx
        original_value = self.current_row_values[self.map_visible_idx_to_col_idx(col_idx)]
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, original_value)

    def menu_select_all(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            self.current_context_entry.tag_add("sel", "1.0", "end-1c")

    def menu_cut(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            self.current_context_entry.event_generate("<<Cut>>")

    def menu_copy(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            self.current_context_entry.event_generate("<<Copy>>")

    def menu_paste(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            # first remove all selected text
            self.current_context_entry.delete("sel.first", "sel.last")
            self.current_context_entry.event_generate("<<Paste>>")

    def menu_search(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            self.current_context_entry.event_generate("<Control-f>")

    def event_paste(self, event):
        # check if there is the sel
        if event.widget.tag_ranges("sel"):
            event.widget.delete("sel.first", "sel.last")
        event.widget.event_generate("<<Paste>>")
        return "break"

    def menu_delete(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            self.current_context_entry.delete("1.0", tk.END)

    def menu_undo(self):
        if hasattr(self, 'current_context_entry') and self.current_context_entry:
            col_idx = self.current_context_entry.col_idx
            original_value = self.current_row_values[self.map_visible_idx_to_col_idx(col_idx)]
            self.current_context_entry.delete("1.0", tk.END)
            self.current_context_entry.insert(tk.END, original_value)

    def create_sample_data(self):
        self.headers = ["Name", "Age", "City", "Occupation"]
        self.rows = [
            ["John Doe", "30", "New York", "Engineer"],
            ["Jane Smith", "28", "San Francisco", "Designer"],
            ["Bob Johnson", "35", "Chicago", "Manager"],
            ["Alice Brown", "25", "Boston", "Developer"],
            ["Charlie Wilson", "40", "Seattle", "Architect"]
        ]
        self.column_visibility = [True] * len(self.headers)
        self.filename = "Untitled.csv"
        self.master.title(f"GoofyCSVEdit - {self.filename}")
    
    def add_row(self):
        dialog = AddRowDialog(self.master, len(self.rows))
        self.master.wait_window(dialog.dialog)
        
        if dialog.result is not None:
            new_row = [''] * len(self.headers)
            insert_position = dialog.result
            
            # Insert at the specified position
            if insert_position == 0:
                self.rows.insert(0, new_row)
                self.current_row = 0
            else:
                # Ensure we don't exceed the list bounds
                if insert_position < 0:
                    # warn the user
                    messagebox.showerror("Error", "Please enter a valid number")
                    return
                elif insert_position > len(self.rows):
                    # warn the user
                    messagebox.showerror("Error", "Please enter a valid number")
                    return

                # insert_position = min(insert_position, len(self.rows))
                self.rows.insert(insert_position, new_row)
                self.current_row = insert_position
            
            self.modified = True
            # self.row_spin.config(to=len(self.rows))
            # self.row_spin.delete(0, tk.END)
            # self.row_spin.insert(0, str(self.current_row + 1))
            self.current_row = insert_position
            self.update_data_display()
            # pop up dialog
            messagebox.showinfo("Info", f"You have added row {insert_position + 1}")

    def open_file(self):
        new_filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if new_filename:
            self.filename = new_filename
            self.master.title(f"GoofyCSVEdit - {self.filename}")
            
            # Clear existing interface
            if self.main_frame:
                self.main_frame.destroy()
                self.main_frame = None
            
            # Reset data
            self.current_row = 0
            self.headers = []
            self.rows = []
            self.column_visibility = []
            
            # Load and create new interface
            self.load_csv()
            self.create_widgets()
            self.update_data_display()
    
    def load_csv(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                self.headers = next(reader, [])
                self.rows = list(reader)
                self.column_visibility = [True] * len(self.headers)
        except FileNotFoundError:
            self.headers = ["Column 1"]
            self.rows = []
            self.column_visibility = [True]
            self.modified = True
    
    def create_widgets(self):
        # Main container
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Row controls
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="◀", width=3, 
                 command=lambda: self.change_row(-1)).pack(side=tk.LEFT)
        self.row_label = ttk.Label(control_frame, text=f"Row {self.current_row + 1} of {len(self.rows)}")
        self.row_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="▶", width=3,
                 command=lambda: self.change_row(1)).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Add Row", 
                 command=self.add_row).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(control_frame, text="?", command=self.about, width=2).pack(side=tk.RIGHT)
        ttk.Button(control_frame, text="📂", command=self.open_new_file, width=2).pack(side=tk.RIGHT)
        ttk.Button(control_frame, text="💾", command=self.save_changes, width=2).pack(side=tk.RIGHT)
        
        # Column headers
        column_visibility_frame = ttk.LabelFrame(self.main_frame, text="Column Visibility")
        column_visibility_frame.pack(fill=tk.X, ipady=5, padx=5)

        self.header_canvas = tk.Canvas(column_visibility_frame, height=24)
        self.header_scrollbar = ttk.Scrollbar(column_visibility_frame, orient="horizontal", command=self.header_canvas.xview)

        self.header_canvas.pack(side=tk.TOP, fill=tk.X, pady=5)
        self.header_scrollbar.pack(side=tk.TOP, fill=tk.X, padx=10)


        self.header_canvas.configure(xscrollcommand=self.header_scrollbar.set)
        
        self.header_frame = ttk.Frame(self.header_canvas)
        self.header_window = self.header_canvas.create_window((0, 0), window=self.header_frame, anchor='nw')

        self.header_frame.bind(
            "<Configure>",
            lambda e: self.header_canvas.configure(scrollregion=self.header_canvas.bbox("all"))
        )
        self.update_column_headers()

        # Status bar (packed FIRST to reserve space at the bottom)
        status_bar_frame = ttk.Frame(self.main_frame)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)  # Pack before data frame

        # Data display (packed LAST to take remaining space)
        self.data_frame = ttk.Frame(self.main_frame)
        self.data_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Expand in remaining space

        # Status bar label
        self.status_bar = ttk.Label(status_bar_frame, text="Ready", anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Change row to the first row
        self.change_row(0)

    def open_new_file(self):
        if self.modified:
            if messagebox.askyesno("Save Changes", "Do you want to save changes to the current file?"):
                self.save_changes()
        self.open_file()
    
    def update_column_headers(self):
        # Clear existing widgets
        for widget in self.header_frame.winfo_children():
            widget.destroy()
        # Create new header widgets
        for col, (header, visible) in enumerate(zip(self.headers, self.column_visibility)):
            frame = ttk.Frame(self.header_frame)
            frame.grid(row=0, column=col, padx=5, sticky='w')

            cb_var = tk.BooleanVar(value=visible)
            cb = ttk.Checkbutton(
                frame,
                text=header,
                style='Header.TCheckbutton',
                variable=cb_var,
                command=lambda c=col: self.toggle_column_visibility(c),
                # highlightthickness=0,
                # bd=0
            )
            cb.pack(side=tk.LEFT)


    def select_all(self, event):
        # event.widget.tag_add("sel", "1.0", "end")
        # just simulate a ctrl+/ press for universal a
        # pplication to entry, text
        event.widget.event_generate("<Control-slash>")
        return "break"

    def update_data_display(self):
        for widget in self.data_frame.winfo_children():
            widget.destroy()
        if not self.rows:
            return
        row_data = self.rows[self.current_row]
        visible_cols = [i for i, visible in enumerate(self.column_visibility) if visible]        

        if not visible_cols:
            frame = ttk.Frame(self.data_frame)
            ttk.Label(frame, text="", background="#f0f0f0", style="Centered.TLabel").pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            return

        self.texts = []

        for col_idx, data_col in enumerate(visible_cols):
            col_frame = ttk.LabelFrame(self.data_frame, text=self.headers[data_col])
            col_frame.grid(row=0, column=col_idx, padx=5, pady=5, sticky='nsew', ipadx=5, ipady=5)
            
            scrollbar = ttk.Scrollbar(col_frame, orient=tk.VERTICAL)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            entry = tk.Text(col_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, width=100000)
            entry.insert(tk.END, row_data[data_col])
            entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            entry.col_idx = col_idx

            self.texts.append(entry)

            entry.bind('<FocusIn>', 
                lambda e, idx=col_idx: setattr(self, 'col_idx_now', idx))
            
            # Focus out to clear all highlight by removing the tags search_highlight and current_match
            def remove_highlight_tags(event):
                event.widget.tag_remove("search_highlight", "1.0", tk.END)
                event.widget.tag_remove("current_match", "1.0", tk.END)
                if hasattr(event.widget, 'search_matches'):
                    del event.widget.search_matches
                if hasattr(event.widget, 'current_match'):
                    del event.widget.current_match
            
            entry.bind('<FocusOut>', remove_highlight_tags)

            entry.bind("<Button-3>", 
                lambda event: self.show_context_menu(event))
            
            entry.bind('<Control-a>', self.select_all)
            
            entry.bind('<Control-z>', self.handle_undo)
            # Bind Ctrl+H to show search popup
            entry.bind('<Control-f>', self.show_search_popup)

            scrollbar.config(command=entry.yview)
            entry.bind('<KeyRelease>', 
                lambda e, c=data_col: self.update_cell_data(c, e.widget.get("1.0", "end-1c")))

            self.data_frame.columnconfigure(col_idx, weight=1)
            
        self.data_frame.rowconfigure(0, weight=1)
        self.row_label.config(text=f"Row {self.current_row + 1} of {len(self.rows)}")

    def handle_undo(self, event):
        """Revert the text widget to its original value."""
        widget = event.widget
        col_idx = widget.col_idx
        original_value = self.current_row_values[self.map_visible_idx_to_col_idx(col_idx)]
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, original_value)

    def show_search_popup(self, event):
        if self.search_popup_on:
            return

        self.search_popup_on = True

        # text_widget = event.widget

        popup = tk.Toplevel(self.master)
        popup.title("Search")

        # always on top
        popup.wm_attributes("-topmost", 1)
        
        search_entry = ttk.Entry(popup)
        search_entry.pack(fill=tk.X, padx=5, pady=5)
        search_entry.focus_set()

        # Bind ctrl+a to select all
        search_entry.bind('<Control-a>', self.select_all)
        
        buttons_frame = ttk.Frame(popup)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        prev_button = ttk.Button(buttons_frame, text="Previous",
                    command=lambda: self.search_prev(self.texts[self.col_idx_now], status_label))
        prev_button.pack(side=tk.LEFT, padx=5)
        
        status_label = ttk.Label(buttons_frame, text="Matches: 0")
        status_label.pack(side=tk.LEFT, padx=5)

        next_button = ttk.Button(buttons_frame, text="Next",
                    command=lambda: self.search_next(self.texts[self.col_idx_now], status_label))
        next_button.pack(side=tk.LEFT, padx=5)
        
        search_entry.bind('<KeyRelease>', lambda e: self.update_search(self.texts[self.col_idx_now], search_entry.get(), status_label))
        
        search_entry.bind('<KeyRelease-Return>', lambda e: self.search_next(self.texts[self.col_idx_now], status_label))

        # bind focus out to close
        popup.bind('<FocusOut>', lambda e: on_close())

        # bind close to clear flag
        search_entry.bind('<Destroy>', lambda e: setattr(self, 'search_popup_on', False))

        def on_close():
            self.texts[self.col_idx_now].tag_remove("search_highlight", "1.0", tk.END)
            self.texts[self.col_idx_now].tag_remove("current_match", "1.0", tk.END)
            if hasattr(self.texts[self.col_idx_now], 'search_matches'):
                del self.texts[self.col_idx_now].search_matches
            if hasattr(self.texts[self.col_idx_now], 'current_match'):
                del self.texts[self.col_idx_now].current_match
            self.search_popup_on = False
            popup.destroy()
            
        popup.protocol("WM_DELETE_WINDOW", on_close)

    def update_search(self, text_widget, search_term, status_label):
        text_widget.tag_remove("search_highlight", "1.0", tk.END)
        text_widget.tag_remove("current_match", "1.0", tk.END)
        
        if not search_term:
            status_label.config(text="Matches: 0")
            return
        
        start = "1.0"
        matches = []
        while True:
            pos = text_widget.search(search_term, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(search_term)}c"
            matches.append((pos, end))
            start = end
        
        for pos, end in matches:
            text_widget.tag_add("search_highlight", pos, end)
        text_widget.tag_config("search_highlight", background="yellow")
        
        status_label.config(text=f"Matches: {len(matches)}")
        
        if matches:
            text_widget.search_matches = matches
            text_widget.current_match = 0
            text_widget.tag_add("current_match", matches[0][0], matches[0][1])
            text_widget.tag_config("current_match", background="orange")
            text_widget.mark_set(tk.INSERT, matches[0][0])
            text_widget.see(tk.INSERT)
            status_label.config(text=f"Match 1 of {len(matches)}")
        else:
            text_widget.search_matches = []
            text_widget.current_match = -1

    def search_next(self, text_widget, status_label):
        if not hasattr(text_widget, 'search_matches') or not text_widget.search_matches:
            return
        current = text_widget.current_match
        if current == -1:
            return
        text_widget.tag_remove("current_match", text_widget.search_matches[current][0], text_widget.search_matches[current][1])
        new_current = (current + 1) % len(text_widget.search_matches)
        text_widget.current_match = new_current
        pos, end = text_widget.search_matches[new_current]
        text_widget.tag_add("current_match", pos, end)
        text_widget.mark_set(tk.INSERT, pos)
        text_widget.see(pos)
        status_label.config(text=f"Match {new_current + 1} of {len(text_widget.search_matches)}")

    def search_prev(self, text_widget, status_label):
        if not hasattr(text_widget, 'search_matches') or not text_widget.search_matches:
            return
        current = text_widget.current_match
        if current == -1:
            return
        text_widget.tag_remove("current_match", text_widget.search_matches[current][0], text_widget.search_matches[current][1])
        new_current = (current - 1) % len(text_widget.search_matches)
        text_widget.current_match = new_current
        pos, end = text_widget.search_matches[new_current]
        text_widget.tag_add("current_match", pos, end)
        text_widget.mark_set(tk.INSERT, pos)
        text_widget.see(pos)
        status_label.config(text=f"Match {new_current + 1} of {len(text_widget.search_matches)}")

    def show_menu(self, event, menu):
        menu.post(event.x_root, event.y_root)

    def toggle_column_visibility(self, col):
        self.column_visibility[col] = not self.column_visibility[col]
        self.update_data_display()
    
    def toggle_column_collapse(self, col):
        # error msg if the col is invisible
        if not self.column_visibility[col]:
            messagebox.showerror("Error", "Cannot collapse an invisible column")
            return

        self.update_column_headers()
        self.update_data_display()
    
    def change_row(self, delta):
        """
        Change the current row by delta.
        Update the data display and saved current row original values.
        If delta is 0, update current row values only.
        """
        if 0 <= self.current_row + delta < len(self.rows):
            # check if content is the same
            old_row_content = self.current_row_values
            new_row_content = self.rows[self.current_row]
            diff = False
            for i in range(len(old_row_content)):
                if old_row_content[i] != new_row_content[i]:
                    diff = True
                    break
            if diff and delta != 0:
                val = messagebox.askyesnocancel(
                    "Warning", 
                    f"Confirm to override the current row content and move on?"
                )
                if val == False: # revert values and move on
                    for idx in range(len(self.current_row_values)):
                        self.update_cell_data(idx, self.current_row_values[idx])
                    self.update_data_display()
                elif val == None: # stay
                    return
            
            self.row_label.config(text=f"Row {self.current_row + 1} of {len(self.rows)}")
            self.current_row += delta

            row_data = self.rows[self.current_row]
            self.current_row_values = []

            for data_col in range(len(self.headers)):
                self.current_row_values.append(row_data[data_col])

            self.update_data_display()
        else:
            if self.current_row == 0:
                messagebox.showinfo("Info", "Already at the first row")
            elif self.current_row == len(self.rows) - 1:
                messagebox.showinfo("Info", "Already at the last row")
            else:
                messagebox.showinfo("Info", f"Row {self.current_row + 1} is out of bounds")

    def update_cell_data(self, col, value):
        self.rows[self.current_row][col] = value
        self.modified = True

    def save_changes(self):
        if not self.filename:
            self.filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
        if not self.filename:
            return
            
        try:
            # call change row 0 to update saved row values, so no pop up dialog
            self.change_row(0)
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
                writer.writerows(self.rows)
            self.modified = False
            self.status_bar.config(text=f"File saved successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def about(self):
        messagebox.showinfo(
            "About", 
            "GoofyCSVEditor v0.2\nThis is a goofy CSV editor with row and column management features.\n\n\n" \
            "Author: \nZhaochen Hong(timsanders256@gmail.com)\n",
        )

def main():
    root = tk.Tk()
    app = CSVEditorApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
