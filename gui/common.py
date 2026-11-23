"""
gui/common.py: small helpers shared by every screen.

IMPORTANT: every import from the backend lives in THIS file only.
When the group's backend modules are merged (medicine.py, prescription.py,
database.py ...), this is the ONE place where the import lines change.
The screens themselves do not need to be touched.
"""
import sqlite3
from tkinter import ttk, messagebox

# --- backend imports (edit here when the backend is split into modules) ---
from pharmacy import (Pharmacy, Medicine, ControlledMedicine, Branch,
                      Prescription, PrescriptionLine)


def add_field(parent, label, row, width=25):
    """Put a label and an entry box on one row; return the entry."""
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=3)
    entry = ttk.Entry(parent, width=width)
    entry.grid(row=row, column=1, padx=5, pady=3)
    return entry


def run_action(action):
    """
    Run an action and show any problem in a popup instead of crashing.
    Returns True if it worked, False if it failed.
      ValueError   -> a business rule was broken (clear message from the backend)
      sqlite3.Error -> database problem
      anything else -> unexpected, still no crash
    """
    try:
        action()
        return True
    except ValueError as error:
        messagebox.showerror("Not allowed", str(error))
    except sqlite3.Error as error:
        messagebox.showerror("Database error", f"The database refused this: {error}")
    except Exception as error:
        messagebox.showerror("Unexpected error", f"Something went wrong: {error}")
    return False


def make_table(parent, columns, titles, height, width=110):
    """Create a table (Treeview) with the given column ids and visible titles."""
    table = ttk.Treeview(parent, columns=columns, show="headings", height=height)
    for col, title in zip(columns, titles):
        table.heading(col, text=title)
        table.column(col, width=width)
    return table


def fill_table(table, rows):
    """Clear a table and fill it with fresh rows."""
    table.delete(*table.get_children())
    for row in rows:
        table.insert("", "end", values=row)
