# Member 1 domain-model design

Project: **Multi-Branch Campus Pharmacy Inventory, Dispensing and Reporting
System**, CSC2105 Object-Oriented Programming examination project.

## 1. Scope and ownership

Member 1 supplies medicine and prescription domain models, their unit tests,
the UML class diagram, and these design notes. This branch implements no GUI,
SQL repository, inventory service, stock deductions, report, or dispensing
transaction. Those operations belong to the relevant group members.

The initial branch already contained medicine models and 34 passing tests.
This stage completes prescriptions, reviews medicine edge cases, and records
integration evidence. Other members' code is read from Git objects and is not
copied into production modules, checked out, merged, or modified.

| File | Responsibility |
|---|---|
| `medicine.py` | Abstract medicine contract, validated properties, ordinary and controlled policies |
| `prescription.py` | Status enumeration, immutable line values, prescription composition and lifecycle |
| `tests/test_medicine.py` | Medicine validation, authorization and OOP regression tests |
| `tests/test_prescription.py` | Line, construction, duplicate-code and lifecycle tests |
| `tests/test_integration_contracts.py` | Member 1 checks against reviewed database and GUI snapshots |
| `docs/uml_diagram.md` | UML matching the implemented classes |
| `docs/member1_design.md` | Design rationale, contracts, evidence and traceability |

## 2. Functional requirements and architecture

Medicines have a non-blank code/name, a positive finite Decimal price, a
non-negative integer reorder threshold, and a fixed ordinary/controlled type.
Ordinary medicines need no prescriber authorization. Controlled medicines
require an exact code in a supplied simulated allow-list.

A prescription has explicit prescription/patient/branch identifiers, an
optional prescriber code, at least one immutable medicine/quantity line, and
a valid lifecycle status. Duplicate medicine codes are consolidated. Pending
prescriptions may become dispensed or cancelled; terminal prescriptions cannot
undergo another lifecycle action.

The intended dependency direction is:

```text
GUI/form mapping -> application/dispensing service -> domain models
                                             -> Member 2 repositories
                                             -> SQLite
```

The domain imports only the Python standard library. It performs no I/O and
does not import repositories or GUI modules. A line references a medicine by
its code; the application resolves the actual medicine and branch stock.

## 3. Classes and public interfaces

`PriceInput = Decimal | int | float | str` accepts supported monetary inputs
and always exposes a `Decimal` through `unit_price`.

```python
Medicine.__init__(
    self, medicine_code: str, name: str, unit_price: PriceInput,
    reorder_level: int, medicine_type: str,
) -> None

OrdinaryMedicine.__init__(
    self, medicine_code: str, name: str, unit_price: PriceInput,
    reorder_level: int,
) -> None

ControlledMedicine.__init__(
    self, medicine_code: str, name: str, unit_price: PriceInput,
    reorder_level: int,
) -> None

# Identical signature on the parent and both concrete subclasses:
can_dispense(
    self, prescriber_code: str | None = None,
    authorised_prescribers: Collection[str] | None = None,
) -> bool

PrescriptionLine(medicine_code: str, quantity: int)

Prescription.__init__(
    self, prescription_id: str, patient_id: str, branch_id: str, *,
    lines: Iterable[PrescriptionLine],
    prescriber_code: str | None = None,
    status: PrescriptionStatus | str = PrescriptionStatus.PENDING,
) -> None

Prescription.mark_dispensed(self) -> None
Prescription.cancel(self) -> None
```

`Medicine` is abstract. `OrdinaryMedicine` always uses `ordinary` and returns
True from `can_dispense()`. `ControlledMedicine` always uses `controlled` and
overrides that method with allow-list checks. Neither method deducts stock.

Medicine's `medicine_code`, `name`, `unit_price`, and `reorder_level` properties
are writable and validated; `medicine_type` is read-only.

`PrescriptionLine` is a frozen, slotted dataclass. Its generated constructor
calls `__post_init__()` to validate `medicine_code` and `quantity`. Dataclasses
also supply value equality and hashing. Both fields are immutable through
normal attribute access.

Every `Prescription` property is read-only: `prescription_id: str`,
`patient_id: str`, `branch_id: str`, `prescriber_code: str | None`,
`lines: tuple[PrescriptionLine, ...]`, and `status: PrescriptionStatus`.
The internal `_require_pending()` method guards lifecycle changes.

`PrescriptionStatus` is a string-valued Enum with members `PENDING`,
`DISPENSED`, and `CANCELLED`. Construction accepts a member or its exact string
value. Persist `.value`; do not rely on `str(enum_member)` for serialization.

## 4. OOP principles

| Principle | Concrete demonstration |
|---|---|
| Abstraction | `Medicine(ABC)` declares the shared `can_dispense()` contract and cannot be instantiated directly |
| Encapsulation | Non-public storage, validated medicine setters, read-only prescription properties, frozen lines and guarded status changes |
| Inheritance | Both concrete medicine classes inherit common validation and properties from `Medicine` |
| Method overriding | Both subclasses implement the parent's abstract `can_dispense()` method |
| Polymorphism | A `list[Medicine]` can be processed with identical calls while each subclass applies its own authorization policy |
| Composition | `Prescription` builds and owns a tuple of immutable `PrescriptionLine` values |

Single underscores are Python encapsulation conventions, not security barriers.
The design avoids public setters that could turn a controlled medicine into an
ordinary one or bypass a prescription's lifecycle guard.

## 5. Invariants and validation

| Input or state | Rule |
|---|---|
| Medicine code/name; prescription, patient, branch and line medicine identifiers | Must be strings containing non-whitespace text |
| Non-blank identifiers | Preserved exactly; no silent case folding or trimming |
| Medicine price | Supported input type, numeric, finite and strictly positive; stored as Decimal |
| Price conversion | `Decimal(str(value))` for non-Decimal inputs; no imposed rounding or currency scale |
| Reorder level | Non-negative `int`, excluding `bool`; floats and numeric strings are rejected |
| Line quantity | Positive `int`, excluding `bool`; strings must be parsed before domain construction |
| Optional prescriber | `None` or string; blank strings normalize to `None`; non-blank strings are preserved |
| Medicine type | Exactly `ordinary` or `controlled`, fixed by concrete class |
| Prescription lines | Iterable of actual `PrescriptionLine` values, non-empty after consumption |
| Repeated medicine codes | Quantities summed exactly; first-seen order retained; case/whitespace differences remain distinct codes |
| Prescription status | Exact valid Enum/string on construction; no direct public assignment |
| Failed medicine property updates | Previous valid value remains unchanged |

Prescription construction consumes a supplied iterable once and creates its
own tuple of consolidated line values. Later changes to the input list cannot
change that prescription. There is no partially built, empty public
prescription; GUI forms can build their temporary list before construction.

## 6. Lifecycle and reconstruction

| Start | Action | Result |
|---|---|---|
| `pending` | `mark_dispensed()` | `dispensed` |
| `pending` | `cancel()` | `cancelled` |
| `dispensed` or `cancelled` | Either method | `ValueError`; status unchanged |

The default is pending. Any valid persisted status may be passed to the
constructor. This supports loading history and does not authorize dispensing
or reopen terminal prescriptions. Reconstruction is a trusted application
operation; an untrusted GUI must not choose historical statuses freely.

`mark_dispensed()` records an already validated service operation. It is not a
substitute for stock checks, authorization, transaction control, or an atomic
persistent pending-state guard.

## 7. Controlled-medicine authorization

`ControlledMedicine.can_dispense(code, allowed_codes)` returns False for a
missing, blank, invalid-type, or unknown code, or a missing/empty allow-list.
Codes must match exactly, including case and non-blank surrounding whitespace,
consistent with the reviewed SQLite lookup. No allow-list is hard-coded.

The allow-list must be a collection of non-blank strings. A single string or
bytes value raises TypeError, preventing substring-based authorization.
Malformed entries raise TypeError/ValueError. A freshly supplied or modified
allow-list is checked on each call; authorization is not cached.

Ordinary medicine returns True regardless of authorization inputs. The caller
must still enforce prescription status, sufficient stock and other dispensing
workflow rules. An optional code being present on a prescription proves no
authorization by itself.

## 8. Exception handling

| Exception | Meaning |
|---|---|
| `TypeError` | Unsupported input type, including Boolean numeric inputs or malformed collections |
| `ValueError` | Supported type with invalid content, invalid status, empty lines or forbidden lifecycle action |
| `AttributeError` | Attempt to assign a read-only property |
| `dataclasses.FrozenInstanceError` | Attempt to change/delete a frozen line field; also an AttributeError subclass |

Malformed decimal parsing errors are translated into a field-specific
ValueError. Missing controlled authorization is an ordinary False result,
not an exception. Database exceptions remain in the persistence layer.

## 9. Member 2 database compatibility

Reviewed commit: `08fda12c1c259f98832f48cf0d87df1b54298b77` on
`member2-database-persistence`. GitHub's branch reference matched this commit
when inspected for this stage.

| Database contract | Domain mapping |
|---|---|
| `Medicines` fields | `medicine_code`, `name`, `unit_price`, `reorder_level`, `medicine_type` |
| Type vocabulary | `ordinary`, `controlled` |
| `Prescriptions` fields | `prescription_id`, `patient_id`, `branch_id`, `prescriber_code`, `status.value` |
| Status vocabulary | `pending`, `dispensed`, `cancelled` |
| `Prescription_Lines` fields | `medicine_code`, `quantity`; repository owns generated `line_id` |
| `Authorised_Prescribers` | Extract `prescriber_code` strings from `get_all_prescribers()` records |
| Foreign keys | Application must supply existing branch and medicine codes; the domain has no database lookup |

Medicine attribute names and prescription values match the schema. Pass lines
as dictionaries or `(medicine_code, quantity)` pairs, not raw dataclass
instances: `PrescriptionRepository.save_prescription()` supports those record
formats. On retrieval, reconstruct each line and pass the persisted status.

Confirmed issues requiring Member 2/application agreement:

1. The repository binds its `unit_price` argument unchanged; sqlite3 rejects
   `Decimal` with ProgrammingError. Its annotation accepts only `float | int`.
   `str(price)` works at runtime for tested ordinary values, but is outside
   that annotation and does not solve numeric storage precision.
2. SQLite NUMERIC storage rounds long decimals. `1E-1000` underflows to zero
   and fails the price check; `1E+1000` is stored as infinity under the reviewed
   schema and cannot be reconstructed as a valid domain price.
3. Python integers are unbounded. SQLite bindings accept signed 64-bit
   integers; larger reorder levels or aggregate quantities require an explicit
   persistence-boundary range policy. Do not silently truncate them.
4. The schema permits repeated prescription medicine rows. Domain
   reconstruction combines them. Services must use consolidated totals.
5. `update_prescription_status()` validates status vocabulary through SQL but
   does not enforce pending-only transitions. A stale domain object is not a
   concurrency guard.

The group must agree on exact monetary storage and a range/scale policy before
claiming lossless persistence. Scaled integer monetary units or an explicit
decimal representation would require coordinated persistence changes.
No global sqlite3 adapters are registered by the domain models.

## 10. Member 4 service handoff

An application service should:

1. Obtain/generate an explicit prescription ID and construct with named fields.
2. Begin a transaction using Member 2's caller-owned `conn` interface.
3. Read current persisted status and branch stock inside that transaction.
4. Resolve each consolidated medicine code; check authorization for controlled
   medicines against the simulated allow-list.
5. Check each **total** requested quantity against stock and deduct atomically.
6. Persist the terminal state with a guarded pending-only update and commit.
7. Reflect success in the in-memory model with `mark_dispensed()`; on failure,
   roll back and discard/reload stale domain objects.

For example, two requests for quantity 3 cannot each pass a stock check against
5. The constructor exposes a single request for 6. Consolidation alone does
not prevent two concurrent transactions from overselling; Member 4 must handle
the atomic stock and status checks. Cancellation needs a persistent guard too.

The reviewed repository already accepts caller-owned connections and leaves
commit/rollback to the caller. The domain never starts a transaction or calls
repository methods. No Member 4 branch was advertised by the remote during
inspection, so its concrete public service interface could not be verified.

## 11. Member 5 GUI compatibility

Reviewed commit: `10273185e21854f86abaa0f53e7075350fdc5354` on `feature/gui`.
GitHub's branch reference matched this snapshot during inspection.

| Current GUI expectation | Required integration work |
|---|---|
| Imports all backend names from `pharmacy` | Wire the split modules/application facade; `pharmacy.py` is absent in the reviewed GUI snapshot and this branch |
| Constructs ordinary `Medicine(...)` | Select concrete `OrdinaryMedicine` |
| Passes entry text for reorder level/quantity | Parse integer form text before calling domain constructors; keep Boolean rejection |
| Reads medicine `.code`, `.price`, `.needs_authorisation()` | Map to `.medicine_code`, `.unit_price`, and `.medicine_type`, or use a GUI-facing adapter |
| Calls `Prescription(patient, branch, prescriber, lines)` | Supply an explicit prescription ID and named fields, including keyword-only `lines` |
| Converts selected prescription ID with `int(...)` | Preserve the schema's text prescription IDs, such as `RX-DEMO-001` |
| Shows Enum directly | Display/persist `.status.value` |
| Handles ValueError specially; catches TypeError generically | Map form parsing/validation errors to meaningful user feedback |

These issues are reproduced using actual GUI callback ASTs with fake entries
and service objects. The tests do not open Tkinter windows or validate rendered
layouts. GUI import wiring and form mapping remain Member 5/application work.

Example of the agreed domain-facing shape (fictional values):

```python
line = PrescriptionLine("MED-DEMO-001", int("2"))
rx = Prescription(
    prescription_id="RX-DEMO-001",
    patient_id="PAT-DEMO-001",
    branch_id="BR-MAIN",
    lines=[line],
    prescriber_code="PRESC-DEMO-OK",
)

# Application/repository boundary; not a method inside the domain:
line_records = [(line.medicine_code, line.quantity) for line in rx.lines]
status_record = rx.status.value
```

## 12. Verified defect and correction

During this stage, the initial prescription constructor accepted four
positional arguments. Replaying the GUI call mapped `PAT-DEMO-001` into
`prescription_id`, `BR-MAIN` into `patient_id`, and the prescriber into
`branch_id`, while losing the optional prescriber value. Construction succeeded
with incorrect field meanings.

The correction makes `lines` keyword-only. The legacy call now raises
TypeError; `test_ambiguous_legacy_positional_constructor_is_rejected` prevents
regression. This corrects Member 1's ambiguity; it does not complete the GUI
adaptation. The original medicine implementation required no production-code
change during this stage. The database/GUI issues above remain documented
integration findings, not claimed fixes in other members' code.

## 13. Known limitations

- Domain state is local to an object; it cannot enforce database uniqueness,
  foreign-key existence, concurrent dispensing, or durable lifecycle changes.
- Private-attribute manipulation and low-level Python mutation APIs can bypass
  convention-based encapsulation. The intended public API is tested.
- No currency rounding, monetary scale or database numeric bounds are imposed
  without a group agreement. Finite domain Decimals may exceed SQLite range.
- Constructor-supplied statuses support trusted reconstruction; the service
  must distinguish new-record creation from historical loading.
- Prescriber authorization is simulated. No clinical validity, prescription
  authenticity, identity verification or real prescriber registry is checked.
- The supplied line iterable is expected to be finite. Prescriptions are
  immutable in content after construction; edits require a new object.
- Contract tests cover the reviewed commits, not unseen future branch changes.
- Full application/GUI execution and concurrent stock deduction are outside
  Member 1's implementation and remain integration work.
