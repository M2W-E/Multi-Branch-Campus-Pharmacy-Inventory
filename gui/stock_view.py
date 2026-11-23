"""gui/stock_view.py: the 'Branches & stock' screen."""
from tkinter import ttk, messagebox

from gui.common import Branch, add_field, run_action


class StockView(ttk.Frame):
    def __init__(self, parent, pharmacy, on_change):
        super().__init__(parent)
        self.pharmacy = pharmacy
        self.on_change = on_change

        self.branch_name = add_field(self, "New branch name", 0)
        ttk.Button(self, text="Add branch", command=self.add_branch).grid(row=0, column=2)

        ttk.Label(self, text="Branch").grid(row=1, column=0, sticky="w", padx=5, pady=10)
        self.branch_box = ttk.Combobox(self, state="readonly", width=22)
        self.branch_box.grid(row=1, column=1)
        self.code = add_field(self, "Medicine code", 2)
        self.qty = add_field(self, "Quantity received", 3)
        ttk.Button(self, text="Receive stock", command=self.receive).grid(row=4, column=1, pady=8)

        self.result = ttk.Label(self, text="")
        self.result.grid(row=5, column=0, columnspan=3)

    def add_branch(self):
        if run_action(lambda: self.pharmacy.add_branch(Branch(self.branch_name.get()))):
            messagebox.showinfo("Saved", "Branch added.")
            self.branch_name.delete(0, "end")
            self.on_change()

    def receive(self):
        branch, code = self.branch_box.get(), self.code.get()
        if run_action(lambda: self.pharmacy.receive_stock(branch, code, self.qty.get())):
            now = self.pharmacy.get_quantity(branch, code)
            self.result.config(text=f"Stock of {code.strip().upper()} at {branch} is now {now}")
            self.on_change()

    def refresh(self):
        self.branch_box["values"] = self.pharmacy.list_branches()
