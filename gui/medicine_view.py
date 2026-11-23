"""gui/medicine_view.py: the 'Register medicine' screen."""
import tkinter as tk
from tkinter import ttk, messagebox

from gui.common import (Medicine, ControlledMedicine, add_field, run_action,
                        make_table, fill_table)


class MedicineView(ttk.Frame):
    def __init__(self, parent, pharmacy, on_change):
        super().__init__(parent)
        self.pharmacy = pharmacy
        self.on_change = on_change      # called after a save so every screen refreshes

        self.code = add_field(self, "Code", 0)
        self.name = add_field(self, "Name", 1)
        self.price = add_field(self, "Unit price (UGX)", 2)
        self.reorder = add_field(self, "Reorder level", 3)
        self.controlled = tk.BooleanVar()
        ttk.Checkbutton(self, text="Controlled medicine",
                        variable=self.controlled).grid(row=4, column=1, sticky="w")
        ttk.Button(self, text="Save medicine", command=self.save).grid(row=5, column=1, pady=8)

        self.table = make_table(self, ("code", "name", "price", "reorder", "type"),
                                ["Code", "Name", "Price", "Reorder", "Type"], height=10)
        self.table.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

    def save(self):
        def action():
            # The tick box decides the class; the class itself checks price etc.
            kind = ControlledMedicine if self.controlled.get() else Medicine
            medicine = kind(self.code.get(), self.name.get(),
                            self.price.get(), self.reorder.get())
            self.pharmacy.add_medicine(medicine)
        if run_action(action):
            messagebox.showinfo("Saved", "Medicine registered.")
            self.on_change()

    def refresh(self):
        fill_table(self.table, [(m.code, m.name, m.price, m.reorder_level,
                                 "Controlled" if m.needs_authorisation() else "Ordinary")
                                for m in self.pharmacy.list_medicines()])
