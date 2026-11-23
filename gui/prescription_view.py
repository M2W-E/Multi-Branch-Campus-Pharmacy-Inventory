"""gui/prescription_view.py: the 'Prescriptions' screen (create, dispense, cancel)."""
import tkinter as tk
from tkinter import ttk, messagebox

from gui.common import (Prescription, PrescriptionLine, add_field, run_action,
                        make_table, fill_table)


class PrescriptionView(ttk.Frame):
    def __init__(self, parent, pharmacy, on_change):
        super().__init__(parent)
        self.pharmacy = pharmacy
        self.on_change = on_change
        self.lines = []             # lines of the prescription being built (not saved yet)

        self.patient = add_field(self, "Patient ID (fictional)", 0)
        ttk.Label(self, text="Branch").grid(row=1, column=0, sticky="w", padx=5)
        self.branch_box = ttk.Combobox(self, state="readonly", width=22)
        self.branch_box.grid(row=1, column=1)
        self.prescriber = add_field(self, "Prescriber code", 2)
        self.code = add_field(self, "Medicine code", 3)
        self.qty = add_field(self, "Quantity", 4)
        ttk.Button(self, text="Add line", command=self.add_line).grid(row=3, column=2)
        ttk.Button(self, text="Save prescription", command=self.save).grid(row=4, column=2)
        ttk.Button(self, text="Clear lines", command=self.clear_lines).grid(row=5, column=2)

        self.lines_box = tk.Listbox(self, height=3, width=30)
        self.lines_box.grid(row=5, column=1, pady=4)

        self.table = make_table(self, ("id", "patient", "branch", "prescriber", "status"),
                                ["ID", "Patient", "Branch", "Prescriber", "Status"], height=7)
        self.table.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

        ttk.Button(self, text="Dispense selected", command=self.dispense).grid(row=7, column=0)
        ttk.Button(self, text="Cancel selected", command=self.cancel).grid(row=7, column=1)

    # building a prescription

    def add_line(self):
        def action():
            line = PrescriptionLine(self.code.get(), self.qty.get())   # validates
            self.lines.append(line)
            self.lines_box.insert("end", f"{line.medicine_code} x {line.quantity}")
        run_action(action)

    def clear_lines(self):
        self.lines = []
        self.lines_box.delete(0, "end")

    def save(self):
        def action():
            rx = Prescription(self.patient.get(), self.branch_box.get(),
                              self.prescriber.get(), self.lines)
            self.pharmacy.create_prescription(rx)
        if run_action(action):
            self.clear_lines()          # start a fresh prescription
            self.on_change()

    # acting on a prescription chosen in the table

    def selected_id(self):
        chosen = self.table.selection()
        if not chosen:
            messagebox.showwarning("Select one", "Click a prescription in the table first.")
            return None
        return int(self.table.item(chosen[0])["values"][0])

    def dispense(self):
        rx_id = self.selected_id()
        if rx_id is not None:
            if run_action(lambda: self.pharmacy.dispense(rx_id)):
                messagebox.showinfo("Done", f"Prescription {rx_id} dispensed.")
            self.on_change()    # refresh even on failure (shows it is still pending)

    def cancel(self):
        rx_id = self.selected_id()
        if rx_id is not None:
            if run_action(lambda: self.pharmacy.cancel_prescription(rx_id)):
                messagebox.showinfo("Done", f"Prescription {rx_id} cancelled.")
            self.on_change()

    def refresh(self):
        self.branch_box["values"] = self.pharmacy.list_branches()
        fill_table(self.table, self.pharmacy.list_prescriptions())
