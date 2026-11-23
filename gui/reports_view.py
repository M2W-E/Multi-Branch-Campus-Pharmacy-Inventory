"""gui/reports_view.py: the 'Low stock' report screen."""
from tkinter import ttk

from gui.common import make_table, fill_table


class ReportsView(ttk.Frame):
    def __init__(self, parent, pharmacy, on_change):
        super().__init__(parent)
        self.pharmacy = pharmacy

        self.table = make_table(self, ("branch", "code", "name", "qty", "reorder"),
                                ["Branch", "Code", "Medicine", "Quantity", "Reorder level"],
                                height=15, width=130)
        self.table.pack(padx=5, pady=5)
        ttk.Button(self, text="Refresh", command=on_change).pack()

    def refresh(self):
        fill_table(self.table, self.pharmacy.low_stock())
