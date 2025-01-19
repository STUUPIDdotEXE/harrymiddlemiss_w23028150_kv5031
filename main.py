import sys
import json
from collections import defaultdict, deque
from datetime import datetime

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QHBoxLayout, QFormLayout, QLineEdit, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QFileDialog,
    QDialog, QDialogButtonBox, QDateTimeEdit
)
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QCategoryAxis
)

###############################################################################
# 0. Global "User Database" dict
###############################################################################
USER_DB = {
    "admin": ("password", "Admin"),
    "worker1": ("w123", "ProductionWorker"),
    "manager1": ("m123", "InventoryManager"),
    "sales1": ("s123", "Sales")
}

###############################################################################
# 1. Global Data Models (Inventory, Orders, Production, etc.)
###############################################################################

# Bike parts usage for each model
BIKE_TYPE_PARTS = {
    "Sport": {
        "Tubular Steel": 2,
        "Wheels": 2,
        "Seats": 1,
        "Gears": 1,
        "Brakes": 1,
        "Lights": 1
    },
    "Tour": {
        "Tubular Steel": 3,
        "Wheels": 2,
        "Seats": 1,
        "Gears": 2,
        "Brakes": 2,
        "Lights": 1
    },
    "Commute": {
        "Tubular Steel": 2,
        "Wheels": 2,
        "Seats": 1,
        "Gears": 1,
        "Brakes": 1,
        "Lights": 1
    },
    "Electric": {
        "Tubular Steel": 2,
        "Wheels": 2,
        "Seats": 1,
        "Gears": 1,
        "Brakes": 1,
        "Lights": 1,
        "Motors": 1
    },
    "Offroad": {
        "Tubular Steel": 3,
        "Wheels": 2,
        "Seats": 1,
        "Gears": 2,
        "Brakes": 2,
        "Lights": 1,
        "Shock Absorbers": 2
    }
}

# Example expanded inventory to handle all possible parts
INVENTORY_DATA = {
    "Tubular Steel": 20,
    "Wheels": 20,
    "Seats": 10,
    "Gears": 15,
    "Brakes": 15,
    "Lights": 10,
    "Motors": 5,             # For Electric bikes
    "Shock Absorbers": 5     # For Offroad bikes
}

# The "fully built bikes" on hand.
BIKE_INVENTORY = {
    "Sport": 0,
    "Tour": 0,
    "Commute": 0,
    "Electric": 0,
    "Offroad": 0
}

ORDERS = []

PRODUCTION_STATUS = {
    "FrameWelded": 0,
    "ForkWelded": 0,
    "FrontForkAssembly": 0,
    "Painting": 0,
    "PedalAddition": 0,
    "WheelAddition": 0,
    "ChainGear": 0,
    "BrakeAddition": 0,
    "LightAddition": 0,
    "SeatInstallation": 0
}

STATION_REQUIREMENTS = {
    "FrameWelded": {"Tubular Steel": 2},
    "ForkWelded":  {"Tubular Steel": 1},
    "FrontForkAssembly": {"FrameWelded": 1, "ForkWelded": 1},
    "Painting": {"FrontForkAssembly": 1},
    "PedalAddition": {"Painting": 1},
    "WheelAddition": {"PedalAddition": 1},
    "ChainGear": {"WheelAddition": 1},
    "BrakeAddition": {"ChainGear": 1},
    "LightAddition": {"BrakeAddition": 1},
    "SeatInstallation": {"LightAddition": 1}
}

MAINTENANCE_RECORDS = deque()
SHIFTS = []
SCHEDULE = []

###############################################################################
# 2. Login Dialog (Checks USER_DB)
###############################################################################
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login (Role‐Based)")

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "ProductionWorker", "InventoryManager", "Sales"])

        form_layout.addRow("Username:", self.username_edit)
        form_layout.addRow("Password:", self.password_edit)
        form_layout.addRow("Role:", self.role_combo)
        layout.addLayout(form_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.attempt_login)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)
        self.resize(350, 150)
        self.selected_role = None

    def attempt_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        selected_role = self.role_combo.currentText()

        if username in USER_DB:
            stored_password, stored_role = USER_DB[username]
            if password == stored_password and selected_role == stored_role:
                self.selected_role = stored_role
                self.accept()
                return

        QMessageBox.warning(self, "Login Failed", "Invalid credentials or role mismatch.")


###############################################################################
# 3. MainWindow
###############################################################################
class MainWindow(QMainWindow):
    def __init__(self, user_role):
        super().__init__()
        self.user_role = user_role
        self.setWindowTitle(f"Bike Factory Management System ({self.user_role})")
        self.resize(1600, 800)

        self._create_menus()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create each tab/screen
        self.dashboard_tab = DashboardTab(self, user_role=self.user_role)
        self.inventory_tab = InventoryTab(self, user_role=self.user_role)
        self.assembly_tab = BikeAssemblyTab(self, user_role=self.user_role)  # NEW TAB
        self.order_tab = OrderEntryTab(self, user_role=self.user_role)
        self.pending_orders_tab = PendingOrdersTab(self, user_role=self.user_role)
        self.reports_tab = ReportsTab(self, user_role=self.user_role)
        self.maintenance_tab = MaintenanceTab(self, user_role=self.user_role)
        self.schedule_tab = ProductionScheduleTab(self, user_role=self.user_role)
        self.shift_tab = ShiftManagementTab(self, user_role=self.user_role)
        self.user_management_tab = UserManagementTab(self, user_role=self.user_role)

        self.order_tab.set_pending_orders_tab(self.pending_orders_tab)

        # Add the tabs
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.inventory_tab, "Inventory")
        self.tabs.addTab(self.assembly_tab, "Bike Assembly")  # Add new Bike Assembly tab
        self.tabs.addTab(self.order_tab, "Order Entry")
        self.tabs.addTab(self.pending_orders_tab, "Pending Orders")
        self.tabs.addTab(self.reports_tab, "Reports")
        self.tabs.addTab(self.maintenance_tab, "Maintenance")
        self.tabs.addTab(self.schedule_tab, "Schedule")
        self.tabs.addTab(self.shift_tab, "Shifts")

        if self.user_role in ["Admin", "InventoryManager"]:
            self.tabs.addTab(self.user_management_tab, "User Management")

        self.refresh_all_tabs()

    def _create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        save_action = QAction("Save Data", self)
        save_action.triggered.connect(self._save_data)
        file_menu.addAction(save_action)

        load_action = QAction("Load Data", self)
        load_action.triggered.connect(self._load_data)
        file_menu.addAction(load_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def refresh_all_tabs(self):
        self.dashboard_tab.update_status_label()
        self.inventory_tab.populate_table()
        self.assembly_tab.update_bike_inventory_table()
        self.pending_orders_tab.refresh_table()
        self.reports_tab.refresh_charts()
        self.maintenance_tab.refresh_maintenance_view()
        self.schedule_tab.refresh_schedule_view()
        self.shift_tab.refresh_shift_view()

        if self.user_role in ["Admin", "InventoryManager"]:
            self.user_management_tab.refresh_user_table()

    def _save_data(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "JSON Files (*.json)")
        if not filename:
            return
        data_to_save = {
            "users": {k: [v[0], v[1]] for k, v in USER_DB.items()},
            "inventory": INVENTORY_DATA,
            "bike_inventory": BIKE_INVENTORY,  # NEW
            "orders": ORDERS,
            "production": PRODUCTION_STATUS,
            "maintenance": list(MAINTENANCE_RECORDS),
            "shifts": SHIFTS,
            "schedule": SCHEDULE
        }
        try:
            with open(filename, "w") as f:
                json.dump(data_to_save, f, indent=2)
            QMessageBox.information(self, "Save Successful", f"Data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving", str(e))

    def _load_data(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Data", "", "JSON Files (*.json)")
        if not filename:
            return
        try:
            with open(filename, "r") as f:
                loaded_data = json.load(f)

            if "users" in loaded_data:
                USER_DB.clear()
                for username, (password, role) in loaded_data["users"].items():
                    USER_DB[username] = (password, role)

            INVENTORY_DATA.clear()
            INVENTORY_DATA.update(loaded_data.get("inventory", {}))

            # Load the completed bike inventory
            if "bike_inventory" in loaded_data:
                BIKE_INVENTORY.clear()
                BIKE_INVENTORY.update(loaded_data["bike_inventory"])

            ORDERS.clear()
            ORDERS.extend(loaded_data.get("orders", []))

            PRODUCTION_STATUS.clear()
            PRODUCTION_STATUS.update(loaded_data.get("production", {}))

            MAINTENANCE_RECORDS.clear()
            for rec in loaded_data.get("maintenance", []):
                MAINTENANCE_RECORDS.append(tuple(rec))

            SHIFTS.clear()
            SHIFTS.extend(loaded_data.get("shifts", []))

            SCHEDULE.clear()
            SCHEDULE.extend(loaded_data.get("schedule", []))

            self.refresh_all_tabs()
            QMessageBox.information(self, "Load Successful", f"Data loaded from {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading", str(e))

    def _show_about_dialog(self):
        QMessageBox.information(
            self,
            "About",
            "Bike Factory Management System\n\n"
            "Now includes a Bike Assembly tab and a separate Bike Inventory,\n"
            "plus usage of pre‐built bikes for fulfilling orders."
        )


###############################################################################
# 4. Dashboard Tab
###############################################################################
class DashboardTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Production Workflow + System Overview")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Production Buttons (only if Admin or ProductionWorker)
        if self.user_role in ["Admin", "ProductionWorker"]:
            station_title = QLabel("Station Completion Buttons:")
            station_title.setStyleSheet("font-weight: bold;")
            layout.addWidget(station_title)
            self._create_station_buttons(layout)

        # A label to show “Production Status” + “Orders” + “Bike Inventory”
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _create_station_buttons(self, parent_layout):
        station_list = [
            ("Frame Welding", "FrameWelded"),
            ("Fork Welding", "ForkWelded"),
            ("Front Fork Assembly", "FrontForkAssembly"),
            ("Painting", "Painting"),
            ("Pedal Addition", "PedalAddition"),
            ("Wheel Addition", "WheelAddition"),
            ("Chain/Gear Installation", "ChainGear"),
            ("Brake Addition", "BrakeAddition"),
            ("Light Addition", "LightAddition"),
            ("Seat Installation", "SeatInstallation")
        ]
        for station_text, station_key in station_list:
            row_layout = QHBoxLayout()
            label = QLabel(station_text + ":")
            btn = QPushButton(f"Complete {station_text}")
            btn.clicked.connect(lambda _, key=station_key: self.record_station_completion(key))
            row_layout.addWidget(label)
            row_layout.addWidget(btn)
            parent_layout.addLayout(row_layout)

    def record_station_completion(self, station_key):
        """
        Deducts resources or prior station completions from STATION_REQUIREMENTS,
        updates PRODUCTION_STATUS, then refreshes the entire UI.
        """
        from PySide6.QtWidgets import QMessageBox
        requirements = STATION_REQUIREMENTS.get(station_key, {})

        # Check requirements
        for req_key, req_amount in requirements.items():
            if req_key in INVENTORY_DATA:
                if INVENTORY_DATA[req_key] < req_amount:
                    QMessageBox.warning(
                        self, "Not Enough Inventory",
                        f"Station '{station_key}' requires {req_amount} of '{req_key}'. "
                        f"Only {INVENTORY_DATA[req_key]} available."
                    )
                    return
            elif req_key in PRODUCTION_STATUS:
                if PRODUCTION_STATUS[req_key] < req_amount:
                    QMessageBox.warning(
                        self, "Not Enough Components",
                        f"Station '{station_key}' requires {req_amount} from prior station '{req_key}'. "
                        f"Only {PRODUCTION_STATUS[req_key]} available."
                    )
                    return
            else:
                QMessageBox.warning(
                    self, "Unknown Requirement",
                    f"Could not find resource or station '{req_key}' in this system."
                )
                return

        # Deduct them
        for req_key, req_amount in requirements.items():
            if req_key in INVENTORY_DATA:
                INVENTORY_DATA[req_key] -= req_amount
            else:
                PRODUCTION_STATUS[req_key] -= req_amount

        PRODUCTION_STATUS[station_key] += 1

        # Refresh everything, including the Dashboard
        self.main_window.refresh_all_tabs()

    def update_status_label(self):
        """
        Called by refresh_all_tabs(). We’ll build a multi-section string showing:
         - Production station counts
         - Orders (pending vs completed)
         - Assembled bikes in BIKE_INVENTORY
        """
        # Production status lines
        prod_lines = ["Production Station Counts:"]
        for station, count in PRODUCTION_STATUS.items():
            prod_lines.append(f"  - {station}: {count}")

        # Orders summary
        total_orders = len(ORDERS)
        pending = sum(1 for o in ORDERS if o.get("status") == "Pending")
        completed = sum(1 for o in ORDERS if o.get("status") == "Completed")
        order_lines = [
            "\nOrder Summary:",
            f"  - Total Orders: {total_orders}",
            f"  - Pending: {pending}",
            f"  - Completed: {completed}"
        ]

        # Bike inventory summary
        bike_inv_lines = ["\nAssembled Bikes in Inventory:"]
        for model, qty in BIKE_INVENTORY.items():
            bike_inv_lines.append(f"  - {model}: {qty}")

        # Combine them
        final_text = "\n".join(prod_lines + order_lines + bike_inv_lines)
        self.status_label.setText(final_text)


###############################################################################
# 5. Inventory Tab
###############################################################################
class InventoryTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role

        main_layout = QVBoxLayout()

        table_label = QLabel("Current Inventory (Parts)")
        table_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Component", "Quantity"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(self.table)

        # If manager or admin, allow replenishing
        if self.user_role in ["Admin", "InventoryManager"]:
            replenish_layout = QHBoxLayout()
            self.component_combo = QComboBox()
            for comp in INVENTORY_DATA:
                self.component_combo.addItem(comp)
            self.replenish_spin = QSpinBox()
            self.replenish_spin.setRange(1, 1000)
            self.add_stock_button = QPushButton("Add/Replenish Stock")
            self.add_stock_button.clicked.connect(self.replenish_stock)
            replenish_layout.addWidget(QLabel("Component:"))
            replenish_layout.addWidget(self.component_combo)
            replenish_layout.addWidget(QLabel("Amount:"))
            replenish_layout.addWidget(self.replenish_spin)
            replenish_layout.addWidget(self.add_stock_button)
            main_layout.addLayout(replenish_layout)

        self.setLayout(main_layout)

    def populate_table(self):
        self.table.setRowCount(len(INVENTORY_DATA))
        for row, (comp, qty) in enumerate(INVENTORY_DATA.items()):
            comp_item = QTableWidgetItem(comp)
            qty_item = QTableWidgetItem(str(qty))
            if qty <= 3:
                comp_item.setBackground(Qt.red)
                qty_item.setBackground(Qt.red)
            self.table.setItem(row, 0, comp_item)
            self.table.setItem(row, 1, qty_item)

        self.table.resizeColumnsToContents()

    def replenish_stock(self):
        comp = self.component_combo.currentText()
        amount = self.replenish_spin.value()
        INVENTORY_DATA[comp] += amount
        self.main_window.refresh_all_tabs()


###############################################################################
# NEW 5A. Bike Assembly Tab
###############################################################################
class BikeAssemblyTab(QWidget):
    """
    Lets user build (assemble) bikes from parts, storing them in BIKE_INVENTORY.
    If there's enough parts to build that model, we deduct from INVENTORY_DATA
    and increment BIKE_INVENTORY.
    """
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role

        layout = QVBoxLayout()

        lbl_header = QLabel("Bike Assembly")
        lbl_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl_header)

        # Table that shows how many fully built bikes we have for each model
        self.bike_table = QTableWidget()
        self.bike_table.setColumnCount(2)
        self.bike_table.setHorizontalHeaderLabels(["Bike Model", "Quantity"])
        self.bike_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.bike_table)

        # If manager or admin or production worker want to build bikes?
        # Let's say only ProductionWorker or Admin can physically assemble bikes
        if self.user_role in ["Admin", "ProductionWorker"]:
            assembly_layout = QHBoxLayout()
            self.assemble_model_combo = QComboBox()
            for bike_type in BIKE_TYPE_PARTS.keys():
                self.assemble_model_combo.addItem(bike_type)

            self.assemble_button = QPushButton("Assemble Bike")
            self.assemble_button.clicked.connect(self.assemble_bike)

            assembly_layout.addWidget(QLabel("Bike Model:"))
            assembly_layout.addWidget(self.assemble_model_combo)
            assembly_layout.addWidget(self.assemble_button)

            layout.addLayout(assembly_layout)
        else:
            layout.addWidget(QLabel("Assembly disabled for your role."))

        self.setLayout(layout)

    def update_bike_inventory_table(self):
        """
        Show how many of each bike type are in BIKE_INVENTORY.
        """
        self.bike_table.setRowCount(len(BIKE_INVENTORY))
        row = 0
        for model, qty in BIKE_INVENTORY.items():
            model_item = QTableWidgetItem(model)
            qty_item = QTableWidgetItem(str(qty))
            self.bike_table.setItem(row, 0, model_item)
            self.bike_table.setItem(row, 1, qty_item)
            row += 1
        self.bike_table.resizeColumnsToContents()

    def assemble_bike(self):
        """
        Use parts from INVENTORY_DATA (based on BIKE_TYPE_PARTS) to assemble
        one bike of the chosen model, if possible. If successful, increment
        BIKE_INVENTORY for that model by 1.
        """
        model = self.assemble_model_combo.currentText()
        if model not in BIKE_TYPE_PARTS:
            QMessageBox.warning(self, "Error", f"No parts recipe found for {model}")
            return

        # Check parts availability
        recipe = BIKE_TYPE_PARTS[model]
        for part, needed in recipe.items():
            have = INVENTORY_DATA.get(part, 0)
            if have < needed:
                QMessageBox.warning(self, "Not Enough Parts",
                                    f"Need {needed} of '{part}' for {model}, only {have} available.")
                return

        # Deduct the parts
        for part, needed in recipe.items():
            INVENTORY_DATA[part] -= needed

        # Add to the BIKE_INVENTORY
        BIKE_INVENTORY[model] += 1

        QMessageBox.information(self, "Assembled",
                                f"One '{model}' bike assembled and added to bike inventory.")

        self.main_window.refresh_all_tabs()


###############################################################################
# 6. Order Entry Tab
###############################################################################
class OrderEntryTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role
        self.pending_orders_tab = None

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.customer_name_input = QLineEdit()
        self.contact_info_input = QLineEdit()
        self.delivery_address_input = QLineEdit()

        self.bike_model_combo = QComboBox()
        self.bike_model_combo.addItems(BIKE_TYPE_PARTS.keys())

        self.bike_size_combo = QComboBox()
        self.bike_size_combo.addItems(["Small", "Medium", "Large", "Extra Large"])

        self.bike_color_combo = QComboBox()
        self.bike_color_combo.addItems(["Red", "Blue", "Green", "Black", "White", "Yellow"])

        self.bike_wheels_combo = QComboBox()
        self.bike_wheels_combo.addItems(["26 inches", "27.5 inches", "29 inches"])

        self.gears_combo = QComboBox()
        self.gears_combo.addItems(["Standard Gears", "Premium Gears"])

        self.brakes_combo = QComboBox()
        self.brakes_combo.addItems(["Disc Brakes", "Rim Brakes"])

        self.lights_combo = QComboBox()
        self.lights_combo.addItems(["LED Lights", "Standard Lights"])

        form_layout.addRow("Customer Name:", self.customer_name_input)
        form_layout.addRow("Contact Info:", self.contact_info_input)
        form_layout.addRow("Delivery Address:", self.delivery_address_input)
        form_layout.addRow("Bike Model:", self.bike_model_combo)
        form_layout.addRow("Bike Size:", self.bike_size_combo)
        form_layout.addRow("Bike Color:", self.bike_color_combo)
        form_layout.addRow("Wheel Size:", self.bike_wheels_combo)
        form_layout.addRow("Gears:", self.gears_combo)
        form_layout.addRow("Brakes:", self.brakes_combo)
        form_layout.addRow("Lights:", self.lights_combo)

        layout.addLayout(form_layout)

        if self.user_role in ["Admin", "Sales"]:
            self.submit_button = QPushButton("Submit Order")
            self.submit_button.clicked.connect(self.submit_order)
            layout.addWidget(self.submit_button)
        else:
            layout.addWidget(QLabel("Order submission disabled for your role."))

        self.setLayout(layout)

    def set_pending_orders_tab(self, pending_tab):
        self.pending_orders_tab = pending_tab

    def submit_order(self):
        new_order = {
            "customer_name": self.customer_name_input.text(),
            "contact_info": self.contact_info_input.text(),
            "delivery_address": self.delivery_address_input.text(),
            "bike_model": self.bike_model_combo.currentText(),
            "bike_size": self.bike_size_combo.currentText(),
            "bike_color": self.bike_color_combo.currentText(),
            "wheel_size": self.bike_wheels_combo.currentText(),
            "gears": self.gears_combo.currentText(),
            "brakes": self.brakes_combo.currentText(),
            "lights": self.lights_combo.currentText(),
            "status": "Pending"
        }
        ORDERS.append(new_order)

        self.customer_name_input.clear()
        self.contact_info_input.clear()
        self.delivery_address_input.clear()

        QMessageBox.information(self, "Order Submitted", "Order has been recorded.")

        if self.pending_orders_tab:
            self.pending_orders_tab.refresh_table()

        self.main_window.refresh_all_tabs()


###############################################################################
# 7. Pending Orders Tab
###############################################################################
class PendingOrdersTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role

        self.layout = QVBoxLayout()

        self.title_label = QLabel("Pending Orders")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Customer", "Model", "Size", "Color", "Status", "Action"])
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.refresh_table()

    def refresh_table(self):
        pending_orders = [o for o in ORDERS if o.get("status") == "Pending"]
        self.table.setRowCount(len(pending_orders))
        for row, order in enumerate(pending_orders):
            c_item = QTableWidgetItem(order.get("customer_name", ""))
            m_item = QTableWidgetItem(order.get("bike_model", ""))
            s_item = QTableWidgetItem(order.get("bike_size", ""))
            c2_item = QTableWidgetItem(order.get("bike_color", ""))
            st_item = QTableWidgetItem(order.get("status", ""))

            self.table.setItem(row, 0, c_item)
            self.table.setItem(row, 1, m_item)
            self.table.setItem(row, 2, s_item)
            self.table.setItem(row, 3, c2_item)
            self.table.setItem(row, 4, st_item)

            if self.user_role in ["Admin", "ProductionWorker"]:
                complete_btn = QPushButton("Complete")
                complete_btn.clicked.connect(lambda checked, r=row: self.mark_completed(r))
                self.table.setCellWidget(row, 5, complete_btn)
            else:
                self.table.setCellWidget(row, 5, QLabel("No permission"))

        self.table.resizeColumnsToContents()

    def mark_completed(self, row_index):
        """
        Mark a pending order as completed, but first check if there's a
        pre-assembled bike in BIKE_INVENTORY for that model.
        If not, we can't complete the order.
        """
        pending_orders = [o for o in ORDERS if o.get("status") == "Pending"]
        if row_index < len(pending_orders):
            order = pending_orders[row_index]
            model = order["bike_model"]
            have = BIKE_INVENTORY.get(model, 0)
            if have < 1:
                QMessageBox.warning(
                    self, "No Pre‐Assembled Bikes",
                    f"No assembled '{model}' bikes available in Bike Inventory.\n"
                    f"Assemble more in the Bike Assembly tab."
                )
                return
            # Otherwise, we have at least 1 bike of that type -> remove it
            BIKE_INVENTORY[model] -= 1
            order["status"] = "Completed"
            QMessageBox.information(
                self, "Order Completed",
                f"Order for {order.get('customer_name','')} is now Completed.\n"
                f"One '{model}' bike removed from Bike Inventory."
            )
            self.main_window.refresh_all_tabs()


###############################################################################
# 8. Reports Tab
###############################################################################
class ReportsTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role
        self.layout = QVBoxLayout()

        title = QLabel("Reports and Production Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title)

        self.inventory_chart_view = None
        self.orders_chart_view = None

        self.setLayout(self.layout)
        self.refresh_charts()

    def refresh_charts(self):
        if self.inventory_chart_view:
            self.layout.removeWidget(self.inventory_chart_view)
            self.inventory_chart_view.deleteLater()

        if self.orders_chart_view:
            self.layout.removeWidget(self.orders_chart_view)
            self.orders_chart_view.deleteLater()

        self.inventory_chart_view = self.create_inventory_pie_chart()
        self.orders_chart_view = self.create_orders_bar_chart()

        self.layout.addWidget(self.inventory_chart_view)
        self.layout.addWidget(self.orders_chart_view)

    def create_inventory_pie_chart(self):
        from PySide6.QtCharts import QPieSeries, QChart, QChartView

        series = QPieSeries()
        for component, qty in INVENTORY_DATA.items():
            series.append(f"{component} ({qty})", qty)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Current Parts Inventory Distribution")

        chart_view = QChartView(chart)
        return chart_view

    def create_orders_bar_chart(self):
        from PySide6.QtCharts import QBarSeries, QBarSet, QChart, QChartView, QCategoryAxis
        model_counts = defaultdict(int)
        for order in ORDERS:
            model_counts[order["bike_model"]] += 1

        set_orders = QBarSet("Orders by Model")
        categories = []
        for model, count in model_counts.items():
            set_orders.append(count)
            categories.append(model)

        series = QBarSeries()
        series.append(set_orders)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Orders by Bike Model")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QCategoryAxis()
        for i, cat in enumerate(categories):
            axisX.append(cat, i)
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)

        chart_view = QChartView(chart)
        return chart_view


###############################################################################
# 9. Maintenance Tab
###############################################################################
class MaintenanceTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role

        layout = QVBoxLayout()
        title = QLabel("Maintenance Tracking")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Station", "Date/Time", "Description"])
        layout.addWidget(self.table)

        if self.user_role in ["Admin", "InventoryManager"]:
            form_layout = QFormLayout()
            self.station_combo = QComboBox()
            self.station_combo.addItems(["Frame Welding", "Fork Welding", "Painting", "AssemblyLine", "Other"])
            self.maint_datetime = QDateTimeEdit()
            self.maint_datetime.setDateTime(QDateTime.currentDateTime())
            self.maint_desc = QLineEdit()

            form_layout.addRow("Station:", self.station_combo)
            form_layout.addRow("Date/Time:", self.maint_datetime)
            form_layout.addRow("Description:", self.maint_desc)

            layout.addLayout(form_layout)

            btn = QPushButton("Add Maintenance Record")
            btn.clicked.connect(self.add_record)
            layout.addWidget(btn)

        self.setLayout(layout)
        self.refresh_maintenance_view()

    def refresh_maintenance_view(self):
        self.table.setRowCount(len(MAINTENANCE_RECORDS))
        for row, (station, date_str, desc) in enumerate(MAINTENANCE_RECORDS):
            self.table.setItem(row, 0, QTableWidgetItem(station))
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            self.table.setItem(row, 2, QTableWidgetItem(desc))
        self.table.resizeColumnsToContents()

    def add_record(self):
        station = self.station_combo.currentText()
        date_str = self.maint_datetime.dateTime().toString(Qt.DefaultLocaleShortDate)
        desc = self.maint_desc.text().strip()
        MAINTENANCE_RECORDS.append((station, date_str, desc))
        QMessageBox.information(self, "Record Added", "Maintenance record added.")
        self.maint_desc.clear()
        self.main_window.refresh_all_tabs()


###############################################################################
# 10. Schedule Tab
###############################################################################
class ProductionScheduleTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role
        layout = QVBoxLayout()

        title = QLabel("Production Schedule")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Date/Time", "Task", "Notes"])
        layout.addWidget(self.table)

        if self.user_role in ["Admin", "ProductionWorker"]:
            form_layout = QFormLayout()
            self.dt_edit = QDateTimeEdit()
            self.dt_edit.setDateTime(QDateTime.currentDateTime())
            self.task_edit = QLineEdit()
            self.notes_edit = QLineEdit()

            form_layout.addRow("Date/Time:", self.dt_edit)
            form_layout.addRow("Task:", self.task_edit)
            form_layout.addRow("Notes:", self.notes_edit)
            layout.addLayout(form_layout)

            add_btn = QPushButton("Add Scheduled Task")
            add_btn.clicked.connect(self.add_schedule_task)
            layout.addWidget(add_btn)

        self.setLayout(layout)
        self.refresh_schedule_view()

    def refresh_schedule_view(self):
        self.table.setRowCount(len(SCHEDULE))
        for row, item in enumerate(SCHEDULE):
            dt_str = item.get("datetime", "")
            task_str = item.get("task", "")
            notes_str = item.get("notes", "")
            self.table.setItem(row, 0, QTableWidgetItem(dt_str))
            self.table.setItem(row, 1, QTableWidgetItem(task_str))
            self.table.setItem(row, 2, QTableWidgetItem(notes_str))
        self.table.resizeColumnsToContents()

    def add_schedule_task(self):
        dt_str = self.dt_edit.dateTime().toString(Qt.DefaultLocaleShortDate)
        task_str = self.task_edit.text().strip()
        notes_str = self.notes_edit.text().strip()

        SCHEDULE.append({"datetime": dt_str, "task": task_str, "notes": notes_str})
        QMessageBox.information(self, "Scheduled Task Added", "Task has been scheduled.")
        self.task_edit.clear()
        self.notes_edit.clear()
        self.main_window.refresh_all_tabs()


###############################################################################
# 11. Shift Tab
###############################################################################
class ShiftManagementTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role
        layout = QVBoxLayout()

        title = QLabel("Shift Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Employee", "Start", "End", "Role"])
        layout.addWidget(self.table)

        if self.user_role in ["Admin", "InventoryManager"]:
            form_layout = QFormLayout()
            self.emp_name = QLineEdit()
            self.start_edit = QDateTimeEdit()
            self.start_edit.setDateTime(QDateTime.currentDateTime())
            self.end_edit = QDateTimeEdit()
            self.end_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
            self.role_combo = QComboBox()
            self.role_combo.addItems(["ProductionWorker", "InventoryManager", "Sales", "Admin"])

            form_layout.addRow("Employee Name:", self.emp_name)
            form_layout.addRow("Start:", self.start_edit)
            form_layout.addRow("End:", self.end_edit)
            form_layout.addRow("Role:", self.role_combo)
            layout.addLayout(form_layout)

            add_btn = QPushButton("Add Shift")
            add_btn.clicked.connect(self.add_shift)
            layout.addWidget(add_btn)

        self.setLayout(layout)
        self.refresh_shift_view()

    def refresh_shift_view(self):
        self.table.setRowCount(len(SHIFTS))
        for row, shift in enumerate(SHIFTS):
            emp = shift["employee"]
            start = shift["start"]
            end = shift["end"]
            role = shift["role"]

            self.table.setItem(row, 0, QTableWidgetItem(emp))
            self.table.setItem(row, 1, QTableWidgetItem(str(start)))
            self.table.setItem(row, 2, QTableWidgetItem(str(end)))
            self.table.setItem(row, 3, QTableWidgetItem(role))

        self.table.resizeColumnsToContents()

    def add_shift(self):
        emp = self.emp_name.text().strip()
        start_str = self.start_edit.dateTime().toString(Qt.DefaultLocaleShortDate)
        end_str = self.end_edit.dateTime().toString(Qt.DefaultLocaleShortDate)
        role = self.role_combo.currentText()

        SHIFTS.append({"employee": emp, "start": start_str, "end": end_str, "role": role})
        QMessageBox.information(self, "Shift Added", f"Shift for {emp} added.")
        self.emp_name.clear()
        self.main_window.refresh_all_tabs()


###############################################################################
# 12. User Management Tab (Create / Delete Users)
###############################################################################
class UserManagementTab(QWidget):
    def __init__(self, main_window, user_role):
        super().__init__()
        self.main_window = main_window
        self.user_role = user_role

        layout = QVBoxLayout()
        title_label = QLabel("User Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["Username", "Password", "Role", "Action"])
        layout.addWidget(self.user_table)

        form_layout = QFormLayout()
        self.new_username = QLineEdit()
        self.new_password = QLineEdit()
        self.new_role_combo = QComboBox()
        self.new_role_combo.addItems(["Admin", "ProductionWorker", "InventoryManager", "Sales"])
        form_layout.addRow("New Username:", self.new_username)
        form_layout.addRow("New Password:", self.new_password)
        form_layout.addRow("Role:", self.new_role_combo)

        create_btn = QPushButton("Create User")
        create_btn.clicked.connect(self.create_user)
        form_layout.addWidget(create_btn)

        layout.addLayout(form_layout)
        self.setLayout(layout)

        self.refresh_user_table()

    def refresh_user_table(self):
        from __main__ import USER_DB

        self.user_table.setRowCount(len(USER_DB))
        for row, (uname, (pwd, role)) in enumerate(USER_DB.items()):
            uname_item = QTableWidgetItem(uname)
            pwd_item = QTableWidgetItem(pwd)
            role_item = QTableWidgetItem(role)

            self.user_table.setItem(row, 0, uname_item)
            self.user_table.setItem(row, 1, pwd_item)
            self.user_table.setItem(row, 2, role_item)

            btn = QPushButton("Delete")
            btn.clicked.connect(lambda checked, u=uname: self.delete_user(u))
            self.user_table.setCellWidget(row, 3, btn)

        self.user_table.resizeColumnsToContents()

    def create_user(self):
        from __main__ import USER_DB

        uname = self.new_username.text().strip()
        pwd = self.new_password.text().strip()
        role = self.new_role_combo.currentText()

        if not uname:
            QMessageBox.warning(self, "Input Error", "Username cannot be empty.")
            return
        if uname in USER_DB:
            QMessageBox.warning(self, "Duplicate User", "That username already exists.")
            return

        USER_DB[uname] = (pwd, role)
        QMessageBox.information(self, "User Created", f"User '{uname}' with role '{role}' created.")
        self.new_username.clear()
        self.new_password.clear()
        self.main_window.refresh_all_tabs()

    def delete_user(self, uname):
        from __main__ import USER_DB

        if uname not in USER_DB:
            QMessageBox.warning(self, "User Not Found", f"No user named '{uname}' in system.")
            return

        if uname == "admin":
            QMessageBox.warning(self, "Cannot Delete", "You cannot remove the built‐in admin.")
            return

        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete user '{uname}'?"
        )
        if result == QMessageBox.Yes:
            del USER_DB[uname]
            QMessageBox.information(self, "User Deleted", f"User '{uname}' removed.")
            self.main_window.refresh_all_tabs()


###############################################################################
# 13. main() - Entry Point
###############################################################################
def main():
    app = QApplication(sys.argv)

    # Fusion style + dark palette
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: none; }")

    # Show the login dialog first
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.Accepted and login_dialog.selected_role:
        window = MainWindow(user_role=login_dialog.selected_role)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
