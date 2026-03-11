from PyQt5.QtWidgets import (
    QFrame, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from themes import THEME

from database import toggle_bookmark as db_toggle_bookmark, get_bookmarked_gaps as db_get_bookmarked_gaps, get_bookmarks_for_case


class _TabBar(QWidget):
    tabChanged = pyqtSignal(int)  # emits 0 = All, 1 = Bookmarked

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

        self.all_btn = QPushButton("All Events")
        self.bm_btn  = QPushButton("Bookmarked")

        for i, btn in enumerate((self.all_btn, self.bm_btn)):
            btn.setCheckable(True)
            btn.setStyleSheet(style)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
            self._group.addButton(btn, i)

        self.all_btn.setChecked(True)
        self._group.idClicked.connect(self.tabChanged)
        layout.addStretch()


class IncognitoGapWidget(QFrame):
  

    # Signal emitted when a row is clicked, with the full gap dict as argument
    eventSelected = pyqtSignal(dict)
    
    # Columns 
    _COLS       = ["Domain", "Count", "Category", "First Seen", "Last Seen", "Duration", "★"]
    _COL_DOMAIN = 0
    _COL_COUNT  = 1
    _COL_CAT    = 2
    _COL_FIRST  = 3
    _COL_LAST   = 4
    _COL_DUR    = 5
    _COL_BM     = 6

    def __init__(self):
        super().__init__()

        self._all_gaps: list[dict] = []
        self._bookmarks: set[str]  = set()   # bookmarked domain strings

        # Set after case is loaded
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

        title_row = QHBoxLayout()
        title = QLabel("Potential Incognito Gaps Detected")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            font-weight: bold;
        """)
        title_row.addWidget(title)
        title_row.addStretch()

        self._count_label = QLabel("0 gaps")
        self._count_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        title_row.addWidget(self._count_label)
        root.addLayout(title_row)

        # Tabs 
        self._tabs = _TabBar()
        self._tabs.tabChanged.connect(self._apply_tab)
        root.addWidget(self._tabs)

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
            QTableWidget::item {{
                padding: 5px;
            }}
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

        self._table.setColumnWidth(self._COL_DOMAIN, 300)
        self._table.setColumnWidth(self._COL_COUNT,   55)
        self._table.setColumnWidth(self._COL_CAT,    200)
        self._table.setColumnWidth(self._COL_FIRST,  250)
        self._table.setColumnWidth(self._COL_LAST,   250)
        self._table.setColumnWidth(self._COL_DUR,     70)
        self._table.setColumnWidth(self._COL_BM,      35)
        self._table.horizontalHeader().setStretchLastSection(False)

       

        self._table.itemSelectionChanged.connect(self._on_row_selected)
        root.addWidget(self._table)

    def load_gaps(self, gap_data: list[dict]):
        
        # Replace the table contents with a fresh list of grouped gaps
        self._all_gaps = gap_data or []
        self._apply_tab(self._tabs._group.checkedId())
        self._count_label.setText(f"{len(self._all_gaps)} gap{'s' if len(self._all_gaps) != 1 else ''}")

    def set_case_id(self, case_id: int):
        # Called once when the dashboard opens - restores bookmarks for this case
        self.case_id = case_id
        self._bookmarks = get_bookmarks_for_case(case_id)
        self._apply_tab(self._tabs._group.checkedId())

    def get_bookmarked_gaps(self) -> list[dict]:
        return [g for g in self._all_gaps if g['domain'] in self._bookmarks]

    # Internal methods
    def _apply_tab(self, tab_id: int):
        
        # Repopulate the table for the active tab (0=All, 1=Bookmarked)
        gaps = self._all_gaps if tab_id == 0 else self.get_bookmarked_gaps()
        self._populate(gaps)

    def _populate(self, gaps: list[dict]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        if not gaps:
            self._table.setRowCount(1)
            placeholder = QTableWidgetItem("No gaps to display")
            placeholder.setTextAlignment(Qt.AlignCenter)
            placeholder.setForeground(QColor(THEME['text_secondary']))
            self._table.setItem(0, 0, placeholder)
            self._table.setSpan(0, 0, 1, len(self._COLS))
            return

        self._table.setRowCount(len(gaps))

        for row, gap in enumerate(gaps):
            is_bookmarked = gap['domain'] in self._bookmarks

            # Domain
            domain_item = QTableWidgetItem(gap['domain'])
            domain_item.setData(Qt.UserRole, gap)   # stash full dict for retrieval
            self._table.setItem(row, self._COL_DOMAIN, domain_item)

            # Count 
            count_item = QTableWidgetItem(str(gap['count']))
            count_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._table.setItem(row, self._COL_COUNT, count_item)

            # Category
            self._table.setItem(row, self._COL_CAT, QTableWidgetItem(gap['category']))

            # First / Last Seen

            self._table.setItem(row, self._COL_FIRST,
                QTableWidgetItem(gap['first_seen'].strftime('%Y-%m-%d %H:%M:%S')))
            self._table.setItem(row, self._COL_LAST,
                QTableWidgetItem(gap['last_seen'].strftime('%Y-%m-%d %H:%M:%S')))

            # Duration 
            self._table.setItem(row, self._COL_DUR,
                QTableWidgetItem(self._fmt_duration(gap['last_seen'] - gap['first_seen'])))

            # Bookmark toggle button
            bm_btn = QPushButton("★" if is_bookmarked else "☆")
            bm_btn.setToolTip("Remove bookmark" if is_bookmarked else "Bookmark this domain")
            bm_btn.setFixedSize(28, 24)
            bm_btn.setCursor(Qt.PointingHandCursor)
            bm_btn.setProperty("domain", gap['domain'])
            bm_btn.setStyleSheet(self._bm_style(is_bookmarked))
            bm_btn.clicked.connect(lambda _, d=gap['domain']: self._toggle_bookmark(d))

            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.addWidget(bm_btn)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.setContentsMargins(2, 1, 2, 1)
            self._table.setCellWidget(row, self._COL_BM, cell)

            # Gold highlight for bookmarked rows 
            if is_bookmarked:
                gold = QColor("#7a6000")
                for col in range(self._COL_BM):
                    item = self._table.item(row, col)
                    if item:
                        item.setBackground(gold)

        self._table.setSortingEnabled(True)

    def _toggle_bookmark(self, domain: str):
        if domain in self._bookmarks:
            self._bookmarks.discard(domain)
            bookmarked = False
        else:
            self._bookmarks.add(domain)
            bookmarked = True
        if self.case_id is not None:
            db_toggle_bookmark(self.case_id, domain, bookmarked)
        self._apply_tab(self._tabs._group.checkedId())

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        item = self._table.item(rows[0].row(), self._COL_DOMAIN)
        if item:
            gap = item.data(Qt.UserRole)
            if gap:
                self.eventSelected.emit(gap)

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
            return f"""
                QPushButton {{
                    background-color: #7a6000;
                    color: #FFD700;
                    border: 1px solid #FFD700;
                    border-radius: 3px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #5a4800; }}
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