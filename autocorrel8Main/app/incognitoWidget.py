from PyQt5.QtWidgets import (
    QFrame, QWidget, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QButtonGroup, QHeaderView, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

from themes import THEME
from database import (
    toggle_bookmark as db_toggle_bookmark,
    get_bookmarks_for_case,
    update_bookmark_note,
)


_TAB_ALL = 0
_TAB_INCOGNITO = 1
_TAB_BOOKMARKED = 2

TYPE_INCOGNITO = 'incognito'
TYPE_NORMAL = 'normal'
 
_TINT_INCOGNITO = QColor("#251515")
_TINT_NORMAL = QColor("#131f14")
_TINT_BOOKMARKED = QColor("#1e1a09")
 
_BADGE_INCOGNITO = "#c0392b"
_BADGE_NORMAL = "#27ae60"


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
            ("All Activity", _TAB_ALL),
            ("Incognito Only", _TAB_INCOGNITO),
            ("★  Bookmarked", _TAB_BOOKMARKED),
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


class _NotesPanel(QFrame):
    
    # Shown below the table when a bookmarked incognito row is selected.
    noteChanged = pyqtSignal(str, str)  

    def __init__(self):
        super().__init__()
        self._domain = None
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._emit_save)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
        """)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self._label = QLabel("Notes")
        self._label.setStyleSheet(
            f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(self._label)
        header.addStretch()
        self._saved_indicator = QLabel("")
        self._saved_indicator.setStyleSheet("color: #27ae60; font-size: 10px;")
        header.addWidget(self._saved_indicator)
        layout.addLayout(header)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Add investigator notes for this bookmark…")
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {THEME['surface_elevated']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 3px;
                font-size: 12px;
                padding: 4px;
            }}
        """)
        self._editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._editor)

    def load(self, domain: str, note: str):
        self._domain = domain
        self._label.setText(f"Notes — {domain}")
        self._saved_indicator.setText("")
        self._editor.blockSignals(True)
        self._editor.setPlainText(note)
        self._editor.blockSignals(False)

    def clear(self):
        self._domain = None
        self._label.setText("Notes")
        self._editor.blockSignals(True)
        self._editor.clear()
        self._editor.blockSignals(False)
        self._saved_indicator.setText("")

    def _on_text_changed(self):
        self._saved_indicator.setText("saving…")
        self._save_timer.start(600)

    def _emit_save(self):
        if self._domain:
            self.noteChanged.emit(self._domain, self._editor.toPlainText())
            self._saved_indicator.setText("saved ✓")


class IncognitoGapWidget(QFrame):
   
    eventSelected = pyqtSignal(dict)

    _COLS = ["Type", "Domain", "Count", "Category", "First Seen", "Last Seen", "Duration", "★"]
    _COL_TYPE = 0
    _COL_DOMAIN = 1
    _COL_COUNT = 2
    _COL_CAT = 3
    _COL_FIRST = 4
    _COL_LAST = 5
    _COL_DUR = 6
    _COL_BM = 7

    def __init__(self):
        super().__init__()

        self._all_entries: list[dict] = []
        self._bookmarks: dict[str, str] = {}   # {domain: note_text}
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
        title = QLabel("Browser Activity")
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
            (_BADGE_INCOGNITO, "Incognito gap"),
            (_BADGE_NORMAL, "Normal history"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {colour}; font-size: 14px;")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addWidget(lbl)
        legend.addStretch()
        root.addLayout(legend)

        # Tabs
        self._tabs = _TabBar()
        self._tabs.tabChanged.connect(self._apply_tab)

        root.addWidget(self._tabs)


        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by domain…")
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
            QLineEdit:focus {{
                border: 1px solid {THEME['accent']};
            }}
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

        self._table.setColumnWidth(self._COL_TYPE, 80)
        self._table.setColumnWidth(self._COL_DOMAIN, 200)
        self._table.setColumnWidth(self._COL_COUNT, 55)
        self._table.setColumnWidth(self._COL_CAT, 130)
        self._table.setColumnWidth(self._COL_FIRST, 140)
        self._table.setColumnWidth(self._COL_LAST, 140)
        self._table.setColumnWidth(self._COL_DUR, 70)
        self._table.setColumnWidth(self._COL_BM, 35)
        self._table.horizontalHeader().setStretchLastSection(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(self._COL_DOMAIN, QHeaderView.Stretch)
        for col in [self._COL_TYPE, self._COL_COUNT, self._COL_CAT,
                    self._COL_FIRST, self._COL_LAST, self._COL_DUR, self._COL_BM]:
            header.setSectionResizeMode(col, QHeaderView.Fixed)

        self._table.itemSelectionChanged.connect(self._on_row_selected)
        root.addWidget(self._table)

        # Notes panel, hidden until a bookmarked incognito row is selected
        self._notes_panel = _NotesPanel()
        self._notes_panel.noteChanged.connect(self._save_note)
        self._notes_panel.hide()
        root.addWidget(self._notes_panel)

    def set_action_button(self, button: QPushButton):
            # Correlation button 
            self._tabs.layout().addWidget(button)

    # Public API
    def load_all_entries(self, gap_data: list[dict], normal_entries: list[dict]):
        gaps = [dict(g, entry_type=TYPE_INCOGNITO) for g in (gap_data or [])]
        normals = [dict(n, entry_type=TYPE_NORMAL) for n in (normal_entries or [])]
        self._all_entries = sorted(gaps + normals, key=lambda x: x['first_seen'])
        n_gaps = len(gaps)
        n_normal = len(normals)
        self._count_label.setText(
            f"{n_gaps} incognito gap{'s' if n_gaps != 1 else ''}  ·  {n_normal} normal entries"
        )
        self._apply_tab(self._tabs._group.checkedId())

    def set_case_id(self, case_id: int):
        self.case_id = case_id
        self._bookmarks = get_bookmarks_for_case(case_id)
        self._apply_tab(self._tabs._group.checkedId())

    def get_bookmarked_gaps(self) -> list[dict]:
        return [e for e in self._all_entries
                if e.get('entry_type') == TYPE_INCOGNITO and e['domain'] in self._bookmarks]

    # Internal
    def _apply_tab(self, tab_id: int):
        if tab_id == _TAB_ALL:
            entries = self._all_entries
        elif tab_id == _TAB_INCOGNITO:
            entries = [e for e in self._all_entries if e.get('entry_type') == TYPE_INCOGNITO]
        else:
            entries = self.get_bookmarked_gaps()
 
        query = self._search.text().strip().lower()
        if query:
            entries = [e for e in entries if query in e['domain'].lower()]
 
        self._populate(entries)

    def _populate(self, entries: list[dict]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._notes_panel.hide()

        if not entries:
            self._table.setRowCount(1)
            placeholder = QTableWidgetItem("No entries to display")
            placeholder.setTextAlignment(Qt.AlignCenter)
            placeholder.setForeground(QColor(THEME['text_secondary']))
            self._table.setItem(0, 0, placeholder)
            self._table.setSpan(0, 0, 1, len(self._COLS))
            return

        self._table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            is_incognito = entry.get('entry_type') == TYPE_INCOGNITO
            is_bookmarked = is_incognito and entry['domain'] in self._bookmarks

            tint = (
                _TINT_BOOKMARKED if is_bookmarked
                else _TINT_INCOGNITO if is_incognito
                else _TINT_NORMAL
            )

            # Type badge
            type_item = QTableWidgetItem("⬤  Gap" if is_incognito else "⬤  Normal")
            type_item.setForeground(QColor(_BADGE_INCOGNITO if is_incognito else _BADGE_NORMAL))
            type_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._table.setItem(row, self._COL_TYPE, type_item)

            # Domain, stash full entry dict for retrieval on click
            domain_item = QTableWidgetItem(entry['domain'])
            domain_item.setData(Qt.UserRole, entry)
            self._table.setItem(row, self._COL_DOMAIN, domain_item)

            # Count
            count_item = QTableWidgetItem(str(entry['count']))
            count_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if is_incognito:
                if entry['count'] >= 50:
                    count_item.setForeground(QColor("#FF4444"))
                elif entry['count'] >= 15:
                    count_item.setForeground(QColor("#FFA500"))
                else:
                    count_item.setForeground(QColor(THEME['accent']))
            self._table.setItem(row, self._COL_COUNT, count_item)

            # Category
            self._table.setItem(row, self._COL_CAT, QTableWidgetItem(entry.get('category', '')))

            # First / Last Seen
            self._table.setItem(row, self._COL_FIRST,
                QTableWidgetItem(entry['first_seen'].strftime('%Y-%m-%d %H:%M:%S')))
            self._table.setItem(row, self._COL_LAST,
                QTableWidgetItem(entry['last_seen'].strftime('%Y-%m-%d %H:%M:%S')))

            # Duration
            self._table.setItem(row, self._COL_DUR,
                QTableWidgetItem(self._fmt_duration(entry['last_seen'] - entry['first_seen'])))

            # Bookmark button, incognito rows only
            if is_incognito:
                bm_btn = QPushButton("★" if is_bookmarked else "☆")
                bm_btn.setFixedSize(28, 24)
                bm_btn.setCursor(Qt.PointingHandCursor)
                bm_btn.setStyleSheet(self._bm_style(is_bookmarked))
                bm_btn.clicked.connect(lambda _, d=entry['domain']: self._toggle_bookmark(d))
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.addWidget(bm_btn)
                cell_layout.setAlignment(Qt.AlignCenter)
                cell_layout.setContentsMargins(2, 1, 2, 1)
                self._table.setCellWidget(row, self._COL_BM, cell)

            # Apply row tint to all text columns
            for col in range(self._COL_BM):
                item = self._table.item(row, col)
                if item:
                    item.setBackground(tint)

        self._table.setSortingEnabled(True)

    def _toggle_bookmark(self, domain: str):
        if domain in self._bookmarks:
            del self._bookmarks[domain]
            bookmarked = False
        else:
            self._bookmarks[domain] = ''
            bookmarked = True
        if self.case_id is not None:
            db_toggle_bookmark(self.case_id, domain, bookmarked)
        self._apply_tab(self._tabs._group.checkedId())

    def _save_note(self, domain: str, note: str):
        self._bookmarks[domain] = note
        if self.case_id is not None:
            update_bookmark_note(self.case_id, domain, note)

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._notes_panel.hide()
            return
        item = self._table.item(rows[0].row(), self._COL_DOMAIN)
        if not item:
            return
        entry = item.data(Qt.UserRole)
        if not entry:
            return

        self.eventSelected.emit(entry)

        # Notes panel only for bookmarked incognito rows
        domain = entry.get('domain', '')
        if entry.get('entry_type') == TYPE_INCOGNITO and domain in self._bookmarks:
            self._notes_panel.load(domain, self._bookmarks.get(domain, ''))
            self._notes_panel.show()
        else:
            self._notes_panel.hide()

    # Helpers

    @staticmethod
    def _fmt_duration(delta) -> str:
        total = int(delta.total_seconds())
        if total == 0:
            return "< 1s"
        if total < 60:
            return f"{total}s"
        if total < 3600:
            m, s = divmod(total, 60)
            return f"{m}m {s}s" if s else f"{m}m"
        h, rem = divmod(total, 3600)
        m = rem // 60
        return f"{h}h {m}m" if m else f"{h}h"

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