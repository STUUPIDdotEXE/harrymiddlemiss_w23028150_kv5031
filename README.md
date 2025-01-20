Bike Factory Management System

A PySide6 program for managing a small bike factory:

    Login with role‐based permissions.
    Station pipeline that tracks partially completed items at each production stage.
    Raw parts inventory and Bike assembly for building complete bikes.
    Order system where “Pending” orders require a pre‐assembled bike to complete.

Setup

    Install Python 3.9+ and run:

    pip install PySide6

    Clone or download this project.
    Execute python bike_factory.py.

Usage

    Login (e.g., admin/password with role Admin).
    Dashboard: see pipeline counts, station buttons, and order/assembly summaries.
    Parts Inventory: view and replenish raw parts.
    Bike Assembly: use raw parts to build bikes (added to BIKE_INVENTORY).
    Order Entry: create new orders.
    Pending Orders: complete an order if an assembled bike of that model is available.
    Reports: see charts on parts and orders.
    Maintenance / Schedule / Shifts: log tasks, track schedules, manage employees.
    User Management (Admin/Manager only): create or remove user accounts.

Data Handling

    File > Save/Load stores/loads data as JSON.
    Global dicts track users, inventory, orders, station pipeline, etc.

Roles

    Admin: full access, including user management.
    ProductionWorker: complete station tasks, assemble bikes, complete orders.
    InventoryManager: replenish parts, manage maintenance, can also manage users.
    Sales: create new orders only.

Contact

Feel free to adapt or extend the code for your needs.
