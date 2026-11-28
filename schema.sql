-- CSC2105 Multi-Branch Campus Pharmacy
-- Member 2: SQLite schema and persistence
--
-- This schema defines the core tables required by the project design.
-- Application business logic belongs in Python modules, not in this file.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Medicines (
    medicine_code TEXT PRIMARY KEY,
    name          TEXT    NOT NULL CHECK (trim(name) <> ''),
    unit_price    NUMERIC NOT NULL CHECK (
                      typeof(unit_price) IN ('integer', 'real')
                      AND unit_price > 0
                  ),
    reorder_level INTEGER NOT NULL CHECK (
                      typeof(reorder_level) = 'integer'
                      AND reorder_level >= 0
                  ),
    medicine_type TEXT    NOT NULL CHECK (
                      medicine_type IN ('ordinary', 'controlled')
                  )
);

CREATE TABLE IF NOT EXISTS Branches (
    branch_id   TEXT PRIMARY KEY,
    branch_name TEXT NOT NULL CHECK (trim(branch_name) <> '')
);

CREATE TABLE IF NOT EXISTS Stock (
    stock_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_code TEXT    NOT NULL,
    branch_id     TEXT    NOT NULL,
    quantity      INTEGER NOT NULL CHECK (
                      typeof(quantity) = 'integer'
                      AND quantity >= 0
                  ),
    FOREIGN KEY (medicine_code) REFERENCES Medicines(medicine_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES Branches(branch_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE (medicine_code, branch_id)
);

CREATE TABLE IF NOT EXISTS Prescriptions (
    prescription_id TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL CHECK (trim(patient_id) <> ''),
    branch_id       TEXT NOT NULL,
    prescriber_code TEXT,
    status          TEXT NOT NULL CHECK (
                        status IN ('pending', 'dispensed', 'cancelled')
                    ),
    FOREIGN KEY (branch_id) REFERENCES Branches(branch_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Prescription_Lines (
    line_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id TEXT    NOT NULL,
    medicine_code   TEXT    NOT NULL,
    quantity        INTEGER NOT NULL CHECK (
                        typeof(quantity) = 'integer'
                        AND quantity > 0
                    ),
    FOREIGN KEY (prescription_id) REFERENCES Prescriptions(prescription_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (medicine_code) REFERENCES Medicines(medicine_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Authorised_Prescribers (
    prescriber_code TEXT PRIMARY KEY CHECK (trim(prescriber_code) <> '')
);
