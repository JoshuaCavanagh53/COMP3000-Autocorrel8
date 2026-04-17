from PyQt5.QtWidgets import (
    QFrame, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
    QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QButtonGroup, QFileDialog, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

from themes import THEME
from registryTimeline import RegistryTimelineWidget
from database import (
    get_registry_bookmarks_for_case,
    toggle_registry_bookmark,
    update_registry_bookmark_note,
)
from registryParser import RegistryParser



_TAB_ALL = 0
_TAB_ADDED = 1
_TAB_MODIFIED = 2
_TAB_DELETED = 3

TYPE_ADDED = 'added'
TYPE_MODIFIED = 'modified'
TYPE_DELETED = 'deleted'

_TINT_ADDED = QColor("#131f14")
_TINT_MODIFIED = QColor("#13141f")
_TINT_DELETED = QColor("#251515")

_BADGE_ADDED = "#27ae60"
_BADGE_MODIFIED = "#7C3AED"
_BADGE_DELETED = "#c0392b"


class _TabBar(QWidget):
    tabChanged = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        style = f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:checked {{
                background-color: {THEME['button_checked']};
                border: 1px solid {THEME['accent']};
                color: {THEME['accent']};
                font-weight: bold;
            }}
            QPushButton:hover:!checked {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for label, tab_id in [
            ("All Changes", _TAB_ALL),
            ("🟢  Added", _TAB_ADDED),
            ("🔵  Modified", _TAB_MODIFIED),
            ("🔴  Deleted", _TAB_DELETED),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(style)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
            self._group.addButton(btn, tab_id)

        self._group.button(_TAB_ALL).setChecked(True)
        self._group.idClicked.connect(self.tabChanged)
        layout.addStretch()


class RegistryWidget(QFrame):

    entrySelected = pyqtSignal(dict)

    _COLS = ["Change", "Key Path", "Value Name", "Category", "Old Data", "New Data", "★"]
    _COL_CHANGE = 0
    _COL_KEY = 1
    _COL_VALUE = 2
    _COL_CAT = 3
    _COL_OLD = 4
    _COL_NEW = 5
    _COL_BM = 6

    def __init__(self):
        super().__init__()

        self._all_entries: list[dict] = []
        self._baseline_path = None
        self._snapshot_path = None
        self._bookmarks: dict[tuple, str] = {}  
        self.case_id = None

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Registry Comparison")
        title.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 14px; font-weight: bold;"
        )
        title_row.addWidget(title)
        title_row.addStretch()
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        title_row.addWidget(self._count_label)
        root.addLayout(title_row)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(12)
        for colour, text in [
            (_BADGE_ADDED, "Added"),
            (_BADGE_MODIFIED, "Modified"),
            (_BADGE_DELETED, "Deleted"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {colour}; font-size: 14px;")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addWidget(lbl)
        legend.addStretch()
        root.addLayout(legend)

        # File load row
        load_row = QHBoxLayout()
        load_row.setSpacing(6)

        self._baseline_btn = QPushButton("📂  Load Baseline")
        self._snapshot_btn = QPushButton("📂  Load Snapshot")
        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setEnabled(False)

        btn_style = f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border-color: {THEME['accent']};
            }}
            QPushButton:disabled {{
                color: {THEME['text_secondary']};
            }}
        """
        compare_style = f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {THEME['accent_hover']}; }}
            QPushButton:disabled {{ background-color: {THEME['button_bg']}; color: {THEME['text_secondary']}; }}
        """

        self._baseline_btn.setStyleSheet(btn_style)
        self._snapshot_btn.setStyleSheet(btn_style)
        self._compare_btn.setStyleSheet(compare_style)

        self._baseline_lbl = QLabel("No baseline loaded")
        self._snapshot_lbl = QLabel("No snapshot loaded")
        for lbl in (self._baseline_lbl, self._snapshot_lbl):
            lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")

        self._baseline_btn.clicked.connect(self._load_baseline)
        self._snapshot_btn.clicked.connect(self._load_snapshot)
        self._compare_btn.clicked.connect(self._run_comparison)

        file_col = QVBoxLayout()
        for btn, lbl in [(self._baseline_btn, self._baseline_lbl),
                         (self._snapshot_btn, self._snapshot_lbl)]:
            row = QHBoxLayout()
            row.addWidget(btn)
            row.addWidget(lbl)
            row.addStretch()
            file_col.addLayout(row)

        load_row.addLayout(file_col)
        load_row.addStretch()
        load_row.addWidget(self._compare_btn)
        root.addLayout(load_row)

        # Tabs
        self._tabs = _TabBar()
        self._tabs.tabChanged.connect(self._apply_tab)
        root.addWidget(self._tabs)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by key path or value name…")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME['surface']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME['accent']}; }}
        """)
        self._search.textChanged.connect(lambda _: self._apply_tab(self._tabs._group.checkedId()))
        root.addWidget(self._search)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['surface']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                gridline-color: {THEME['border']};
            }}
            QTableWidget::item {{ padding: 5px; }}
            QTableWidget::item:selected {{
                background-color: {THEME['button_checked']};
                color: {THEME['accent']};
            }}
            QHeaderView::section {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                padding: 5px;
                border: 1px solid {THEME['border']};
                font-weight: bold;
            }}
        """)

        self._table.setColumnWidth(self._COL_CHANGE, 80)
        self._table.setColumnWidth(self._COL_VALUE, 120)
        self._table.setColumnWidth(self._COL_CAT, 160)
        self._table.setColumnWidth(self._COL_OLD, 130)
        self._table.setColumnWidth(self._COL_BM, 35)
        self._table.horizontalHeader().setStretchLastSection(False)

   
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(self._COL_KEY, QHeaderView.Stretch)
        header.setSectionResizeMode(self._COL_NEW, QHeaderView.Stretch)
        for col in [self._COL_CHANGE, self._COL_VALUE, self._COL_CAT, self._COL_OLD, self._COL_BM]:
            header.setSectionResizeMode(col, QHeaderView.Fixed)

        self._table.itemSelectionChanged.connect(self._on_row_selected)
        root.addWidget(self._table)

        # Notes panel - shown when a bookmarked row is selected
        self._notes_panel = self._build_notes_panel()
        self._notes_panel.hide()
        root.addWidget(self._notes_panel)

        self._show_placeholder()

    # Public API

    def load_entries(self, entries: list[dict]):
        self._all_entries = entries or []
        n_added = sum(1 for e in entries if e.get('change_type') == TYPE_ADDED)
        n_mod = sum(1 for e in entries if e.get('change_type') == TYPE_MODIFIED)
        n_del = sum(1 for e in entries if e.get('change_type') == TYPE_DELETED)
        self._count_label.setText(
            f"{n_added} added  ·  {n_mod} modified  ·  {n_del} deleted"
        )
  
        self._apply_tab(self._tabs._group.checkedId())

    # Internal

    def set_case_id(self, case_id: int):
        self.case_id = case_id
        self._bookmarks = get_registry_bookmarks_for_case(case_id)
        self._apply_tab(self._tabs._group.checkedId())

    def _load_baseline(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Baseline", "",
            "Registry Files (*.json *.reg *.csv);;All Files (*)"
        )
        if path:
            self._baseline_path = path
            self._baseline_lbl.setText(path.split("/")[-1].split("\\")[-1])
            self._baseline_lbl.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 11px;")
            self._update_compare_btn()

    def _load_snapshot(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Snapshot", "",
            "Registry Files (*.json *.reg *.csv);;All Files (*)"
        )
        if path:
            self._snapshot_path = path
            self._snapshot_lbl.setText(path.split("/")[-1].split("\\")[-1])
            self._snapshot_lbl.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 11px;")
            self._update_compare_btn()

    def _update_compare_btn(self):
        self._compare_btn.setEnabled(
            bool(self._baseline_path and self._snapshot_path)
        )

    def _run_comparison(self):
        try:
            parser = RegistryParser()
            results = parser.compare(
                self._baseline_path,
                self._snapshot_path,
                case_id=self.case_id
            )

            self.load_entries(results)

            b_status = self._hash_badge(parser.baseline_hash_status)
            s_status = self._hash_badge(parser.snapshot_hash_status)
            n_added = sum(1 for e in results if e.get('change_type') == 'added')
            n_mod = sum(1 for e in results if e.get('change_type') == 'modified')
            n_del = sum(1 for e in results if e.get('change_type') == 'deleted')
            self._count_label.setText(
                f"{n_added} added  ·  {n_mod} modified  ·  {n_del} deleted  |  Baseline: {b_status}  Snapshot: {s_status}"
            )

        except Exception as e:
            self._count_label.setText(f"Error: {e}")

    def _hash_badge(self, status: str) -> str:
        return {
            'new': '🔵 Hashed',
            'verified': '🟢 Verified',
            'mismatch': '🔴 HASH MISMATCH',
            'unchecked': '⚪ Unchecked',
        }.get(status, status)

    def _apply_tab(self, tab_id: int):
        if tab_id == _TAB_ALL:
            entries = self._all_entries
        elif tab_id == _TAB_ADDED:
            entries = [e for e in self._all_entries if e.get('change_type') == TYPE_ADDED]
        elif tab_id == _TAB_MODIFIED:
            entries = [e for e in self._all_entries if e.get('change_type') == TYPE_MODIFIED]
        else:
            entries = [e for e in self._all_entries if e.get('change_type') == TYPE_DELETED]

        query = self._search.text().strip().lower()
        if query:
            entries = [e for e in entries
                       if query in e.get('key_path', '').lower()
                       or query in e.get('value_name', '').lower()
                       or query in e.get('category', '').lower()]

        self._populate(entries)

    def _populate(self, entries: list[dict]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._notes_panel.hide()

        if not entries:
            self._show_placeholder()
            return

        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            change = entry.get('change_type', '')
            colour = {
                TYPE_ADDED: _BADGE_ADDED,
                TYPE_MODIFIED: _BADGE_MODIFIED,
                TYPE_DELETED: _BADGE_DELETED,
            }.get(change, THEME['text_secondary'])
            tint = {
                TYPE_ADDED: _TINT_ADDED,
                TYPE_MODIFIED: _TINT_MODIFIED,
                TYPE_DELETED: _TINT_DELETED,
            }.get(change, QColor(THEME['surface']))

            bm_key = (entry.get('key_path', ''), entry.get('value_name', ''))
            is_bookmarked = bm_key in self._bookmarks
            if is_bookmarked:
                tint = QColor("#1e1a09")

            label = {"added": "⬤  Added", "modified": "⬤  Modified", "deleted": "⬤  Deleted"}.get(change, change)
            change_item = QTableWidgetItem(label)
            change_item.setForeground(QColor(colour))
            change_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._table.setItem(row, self._COL_CHANGE, change_item)

            key_item = QTableWidgetItem(entry.get('key_path', ''))
            key_item.setData(Qt.UserRole, entry)
            self._table.setItem(row, self._COL_KEY, key_item)

            self._table.setItem(row, self._COL_VALUE, QTableWidgetItem(entry.get('value_name', '')))
            self._table.setItem(row, self._COL_CAT, QTableWidgetItem(entry.get('category', 'Other')))
            self._table.setItem(row, self._COL_OLD, QTableWidgetItem(str(entry.get('old_data', ''))))
            self._table.setItem(row, self._COL_NEW, QTableWidgetItem(str(entry.get('new_data', ''))))

            # Bookmark button
            bm_btn = QPushButton("★" if is_bookmarked else "☆")
            bm_btn.setFixedSize(28, 24)
            bm_btn.setCursor(Qt.PointingHandCursor)
            bm_btn.setStyleSheet(self._bm_style(is_bookmarked))
            bm_btn.clicked.connect(lambda _, e=entry: self._toggle_bookmark(e))
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.addWidget(bm_btn)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.setContentsMargins(2, 1, 2, 1)
            self._table.setCellWidget(row, self._COL_BM, cell)

            for col in range(self._COL_BM):
                item = self._table.item(row, col)
                if item:
                    item.setBackground(tint)

        self._table.setSortingEnabled(True)

    def _toggle_bookmark(self, entry: dict):
        key = (entry.get('key_path', ''), entry.get('value_name', ''))
        if key in self._bookmarks:
            del self._bookmarks[key]
            bookmarked = False
        else:
            self._bookmarks[key] = ''
            bookmarked = True
        if self.case_id is not None:
            toggle_registry_bookmark(self.case_id, key[0], key[1], bookmarked)
        self._apply_tab(self._tabs._group.checkedId())

    def _save_note(self, key_path: str, value_name: str, note: str):
        key = (key_path, value_name)
        self._bookmarks[key] = note
        if self.case_id is not None:
            update_registry_bookmark_note(self.case_id, key_path, value_name, note)

    def _show_placeholder(self):
        self._table.setRowCount(1)
        msg = "Load a baseline and snapshot, then click Compare" if not self._all_entries else "No entries match the current filter"
        placeholder = QTableWidgetItem(msg)
        placeholder.setTextAlignment(Qt.AlignCenter)
        placeholder.setForeground(QColor(THEME['text_secondary']))
        self._table.setItem(0, 0, placeholder)
        self._table.setSpan(0, 0, 1, len(self._COLS))

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._notes_panel.hide()
            return
        item = self._table.item(rows[0].row(), self._COL_KEY)
        if not item:
            return
        entry = item.data(Qt.UserRole)
        if not entry:
            return

        self.entrySelected.emit(entry)

        # Show notes panel for bookmarked rows
        key = (entry.get('key_path', ''), entry.get('value_name', ''))
        if key in self._bookmarks:
            self._notes_label.setText(f"Notes — {entry.get('value_name', '')}")
            self._notes_editor.blockSignals(True)
            self._notes_editor.setPlainText(self._bookmarks.get(key, ''))
            self._notes_editor.blockSignals(False)
            self._notes_current_key = key
            self._notes_saved_indicator.setText("")
            self._notes_panel.show()
        else:
            self._notes_panel.hide()

    def _build_notes_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedHeight(110)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self._notes_label = QLabel("Notes")
        self._notes_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;")
        header.addWidget(self._notes_label)
        header.addStretch()
        self._notes_saved_indicator = QLabel("")
        self._notes_saved_indicator.setStyleSheet("color: #27ae60; font-size: 10px;")
        header.addWidget(self._notes_saved_indicator)
        layout.addLayout(header)

        self._notes_editor = QTextEdit()
        self._notes_editor.setPlaceholderText("Add investigator notes for this bookmark...")
        self._notes_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {THEME['surface_elevated']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 3px;
                font-size: 12px;
                padding: 4px;
            }}
        """)
        self._notes_current_key = None
        self._notes_save_timer = QTimer()
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.timeout.connect(self._flush_note)
        self._notes_editor.textChanged.connect(self._on_note_changed)
        layout.addWidget(self._notes_editor)

        return panel

    def _on_note_changed(self):
        self._notes_saved_indicator.setText("saving...")
        self._notes_save_timer.start(600)

    def _flush_note(self):
        if self._notes_current_key:
            key_path, value_name = self._notes_current_key
            self._save_note(key_path, value_name, self._notes_editor.toPlainText())
            self._notes_saved_indicator.setText("saved ✓")

    @staticmethod
    def _bm_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #7a6000;
                    color: #FFD700;
                    border: 1px solid #FFD700;
                    border-radius: 3px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #5a4800; }
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 3px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: #FFD700;
                border-color: #FFD700;
            }}
        """