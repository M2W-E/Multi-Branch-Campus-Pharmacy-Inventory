"""
app.py: starts the program and puts the four screens into tabs.
Run with:  python app.py

The screens live in the gui/ folder. They only show things and pass clicks to
the backend; no business rules are written here or in gui/.
"""
import tkinter as tk
from tkinter import ttk

from gui.common import Pharmacy
from gui.medicine_view import MedicineView
from gui.stock_view import StockView
from gui.prescription_view import PrescriptionView
from gui.reports_view import ReportsView


class App(tk.Tk):
    def __init__(self, pharmacy):
        super().__init__()
        self.title("UCU Campus Pharmacy")
        self.geometry("760x520")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)

        # Every screen gets the backend and a 'refresh everything' callback.
        self.views = [
            (MedicineView(tabs, pharmacy, self.refresh_all), "Register medicine"),
            (StockView(tabs, pharmacy, self.refresh_all), "Branches & stock"),
            (PrescriptionView(tabs, pharmacy, self.refresh_all), "Prescriptions"),
            (ReportsView(tabs, pharmacy, self.refresh_all), "Low stock"),
        ]
        for view, title in self.views:
            tabs.add(view, text=title)
        self.refresh_all()

    def refresh_all(self):
        """Reload every screen from the database."""
        for view, _ in self.views:
            view.refresh()


if __name__ == "__main__":
    pharmacy = Pharmacy("pharmacy.db")
    pharmacy.seed_sample_data()      # only fills the database if it is empty
    App(pharmacy).mainloop()
