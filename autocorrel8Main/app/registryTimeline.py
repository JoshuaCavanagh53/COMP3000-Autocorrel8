from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics

from themes import THEME


# Colours 
COLOR_ADDED    = "#27ae60"
COLOR_MODIFIED = "#7C3AED"
COLOR_DELETED  = "#c0392b"

# Layout constants 
LABEL_WIDTH   = 110  
DOT_RADIUS    = 6     
DOT_SPACING   = 22    
GROUP_PADDING = 40    
LANE_HEIGHT   = 80    
CONNECTOR_ZONE = 30   


def _change_color(change_type: str) -> str:
    return {
        "added":    COLOR_ADDED,
        "modified": COLOR_MODIFIED,
        "deleted":  COLOR_DELETED,
    }.get(change_type, THEME["text_secondary"])


# Category grouping 
TACTIC_ORDER = [
    "Persistence",
    "COM Hijack",
    "Network",
    "Security",
    "Activity",
    "System",
    "Other",
]

def _tactic_for(category: str) -> str:
    """Return the broad tactic bucket for a category label."""
    for tactic in TACTIC_ORDER:
        if category.startswith(tactic):
            return tactic
    return "Other"


# Data helpers 
class _Dot:
    __slots__ = ("x", "y", "entry", "lane")

    def __init__(self, x, y, entry, lane):
        self.x     = x
        self.y     = y
        self.entry = entry
        self.lane  = lane  


# Single swimlane pair 
class _SwimlanePair(QWidget):
  
    TOTAL_HEIGHT = LANE_HEIGHT + CONNECTOR_ZONE + LANE_HEIGHT

    def __init__(self, tactic: str, entries: list, group_positions: dict, parent=None):
        super().__init__(parent)
        self.tactic          = tactic
        self.entries         = entries         
        self.group_positions = group_positions  
        self.dots: list[_Dot] = []
        self.hovered_dot: _Dot | None = None
        self.highlighted_entry = None
        self.registry_table_ref = None

        self.setFixedHeight(self.TOTAL_HEIGHT)
        self.setMouseTracking(True)
        self._compute_dots()

    # Public API 

    def set_registry_table(self, ref):
        self.registry_table_ref = ref

    def highlight_entry(self, entry):
        self.highlighted_entry = entry
        self.update()

    def clear_highlight(self):
        self.highlighted_entry = None
        self.update()

    # Dot layout

    def _baseline_y(self) -> int:
        return LANE_HEIGHT // 2

    def _snapshot_y(self) -> int:
        return LANE_HEIGHT + CONNECTOR_ZONE + LANE_HEIGHT // 2

    def _compute_dots(self):
        self.dots = []
        by = self._baseline_y()
        sy = self._snapshot_y()

        for key_path, base_x in self.group_positions.items():
            kp_entries = [e for e in self.entries if e.get("key_path") == key_path]

            baseline_entries  = [e for e in kp_entries if e.get("change_type") in ("deleted", "modified")]
            snapshot_entries  = [e for e in kp_entries if e.get("change_type") in ("added",   "modified")]

            for i, e in enumerate(baseline_entries):
                self.dots.append(_Dot(base_x + i * DOT_SPACING, by, e, "baseline"))
            for i, e in enumerate(snapshot_entries):
                self.dots.append(_Dot(base_x + i * DOT_SPACING, sy, e, "snapshot"))

    # Paint 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        by = self._baseline_y()
        sy = self._snapshot_y()
        connector_top    = LANE_HEIGHT
        connector_bottom = LANE_HEIGHT + CONNECTOR_ZONE

        # Background zones
        bg     = QColor(THEME["timeline_bg"])
        bg_alt = bg.darker(108)
        # Before lane
        painter.fillRect(0, 0, w, LANE_HEIGHT, bg)
        # Connector strip
        painter.fillRect(0, connector_top, w, CONNECTOR_ZONE, QColor(THEME["surface"]))
        # After lane
        painter.fillRect(0, connector_bottom, w, LANE_HEIGHT, bg_alt)

        # Left sidebar 
        sidebar = QColor(THEME["surface"])
        painter.fillRect(0, 0, LABEL_WIDTH, self.TOTAL_HEIGHT, sidebar)
        painter.setPen(QPen(QColor(THEME["border"]), 1))
        painter.drawLine(LABEL_WIDTH, 0, LABEL_WIDTH, self.TOTAL_HEIGHT)

        # Tactic label centred in sidebar
        font = QFont(); font.setPointSize(9); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(THEME["text_primary"]))
        painter.drawText(
            QRect(4, 0, LABEL_WIDTH - 8, self.TOTAL_HEIGHT),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.tactic
        )

        font2 = QFont(); font2.setPointSize(8)
        painter.setFont(font2)
        painter.setPen(QColor(THEME["text_secondary"]))
        painter.drawText(QRect(4, 2, LABEL_WIDTH - 8, 14), Qt.AlignLeft, "Before")
        painter.drawText(QRect(4, connector_bottom + 2, LABEL_WIDTH - 8, 14), Qt.AlignLeft, "After")

        # Horizontal tracks
        track_color = QColor(THEME["accent"]); track_color.setAlpha(70)
        painter.setPen(QPen(track_color, 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(LABEL_WIDTH + 8, by,  w - 10, by)
        painter.drawLine(LABEL_WIDTH + 8, sy,  w - 10, sy)

        # Group separators + count badges 
        for key_path, gx in self.group_positions.items():
            kp_entries = [e for e in self.entries if e.get("key_path") == key_path]
            count = len(kp_entries)
            if count == 0:
                continue

            # Vertical tick in connector zone
            sep_col = QColor(THEME["border"]); sep_col.setAlpha(80)
            painter.setPen(QPen(sep_col, 1, Qt.DashLine))
            painter.drawLine(gx, connector_top + 4, gx, connector_bottom - 4)

            # Count badge
            badge_text = f"×{count}"
            font3 = QFont(); font3.setPointSize(8); font3.setBold(True)
            painter.setFont(font3)
            fm = QFontMetrics(font3)
            bw = fm.horizontalAdvance(badge_text) + 10
            bh = 16
            bx = gx - bw // 2
            badge_y = connector_top + (CONNECTOR_ZONE - bh) // 2

            painter.setBrush(QBrush(QColor(THEME["button_bg"])))
            painter.setPen(QPen(QColor(THEME["border"]), 1))
            painter.drawRoundedRect(bx, badge_y, bw, bh, 4, 4)
            painter.setPen(QColor(THEME["text_primary"]))
            painter.drawText(QRect(bx, badge_y, bw, bh), Qt.AlignCenter, badge_text)

            # Short key path label below badge
            short = key_path.split("\\")[-1]
            font4 = QFont(); font4.setPointSize(7)
            painter.setFont(font4)
            painter.setPen(QColor(THEME["text_secondary"]))
            painter.drawText(
                QRect(gx - 50, badge_y + bh + 1, 100, 10),
                Qt.AlignCenter, short
            )

        # Connector lines between matched modified dots 
        baseline_dots  = {d for d in self.dots if d.lane == "baseline"}
        snapshot_dots  = {d for d in self.dots if d.lane == "snapshot"}

        for bd in baseline_dots:
            if bd.entry.get("change_type") != "modified":
                continue
            # Find matching snapshot dot by key_path + value_name
            match = next(
                (sd for sd in snapshot_dots
                 if sd.entry.get("key_path")    == bd.entry.get("key_path")
                 and sd.entry.get("value_name") == bd.entry.get("value_name")),
                None
            )
            if not match:
                continue

            line_col = QColor(COLOR_MODIFIED); line_col.setAlpha(130)
            painter.setPen(QPen(line_col, 1, Qt.DotLine))
            painter.drawLine(bd.x, bd.y + DOT_RADIUS + 2, match.x, match.y - DOT_RADIUS - 2)

        # Dots 
        for dot in self.dots:
            self._draw_dot(painter, dot)

        # Tooltip for hovered dot
        if self.hovered_dot:
            self._draw_tooltip(painter, self.hovered_dot)

    def _draw_dot(self, painter: QPainter, dot: _Dot):
        color      = _change_color(dot.entry.get("change_type", ""))
        is_hovered = dot is self.hovered_dot
        is_highlighted = (
            self.highlighted_entry is not None
            and dot.entry.get("value_name") == self.highlighted_entry.get("value_name")
            and dot.entry.get("key_path")   == self.highlighted_entry.get("key_path")
        )

        if is_highlighted:
            r = DOT_RADIUS + 4
            painter.setBrush(QBrush(QColor("#ffdd00")))
            painter.setPen(QPen(QColor("#ffdd00").darker(130), 2))
        elif is_hovered:
            r = DOT_RADIUS + 3
            painter.setBrush(QBrush(QColor(color).lighter(140)))
            painter.setPen(QPen(QColor(color), 2))
        else:
            r = DOT_RADIUS
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(color).darker(140), 1))

        painter.drawEllipse(dot.x - r, dot.y - r, r * 2, r * 2)

    def _draw_tooltip(self, painter: QPainter, dot: _Dot):
        entry = dot.entry
        lines = [
            f"  {entry.get('value_name', 'Unknown')}  ",
            f"  Category: {entry.get('category', 'Other')}  ",
            f"  Change: {entry.get('change_type', '').capitalize()}  ",
        ]
        if entry.get("old_data"):
            old = str(entry["old_data"])
            lines.append(f"  Before: {old[:35]}{'…' if len(old)>35 else ''}  ")
        if entry.get("new_data"):
            new = str(entry["new_data"])
            lines.append(f"  After:  {new[:35]}{'…' if len(new)>35 else ''}  ")

        font = QFont(); font.setPointSize(9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        line_h    = fm.height() + 2
        tip_w     = max(fm.horizontalAdvance(l) for l in lines) + 4
        tip_h     = line_h * len(lines) + 10

        ty_above = dot.y - DOT_RADIUS - tip_h - 4
        ty_below = dot.y + DOT_RADIUS + 4
 
        if ty_above >= 2:
            ty = ty_above
        elif ty_below + tip_h <= self.height() - 2:
            ty = ty_below
        else:
            ty = max(2, ty_above)

        tx = max(LABEL_WIDTH + 4, min(dot.x - tip_w // 2, self.width() - tip_w - 4))

        color = _change_color(entry.get("change_type", ""))
        painter.setBrush(QBrush(QColor(THEME["surface_elevated"])))
        painter.setPen(QPen(QColor(color), 1))
        painter.drawRoundedRect(tx, ty, tip_w, tip_h, 5, 5)

        painter.setPen(QColor(THEME["text_primary"]))
        for i, line in enumerate(lines):
            painter.drawText(
                QRect(tx, ty + 5 + i * line_h, tip_w, line_h),
                Qt.AlignVCenter | Qt.AlignLeft, line
            )

    # Mouse interaction 

    def mouseMoveEvent(self, event):
        mx, my = event.x(), event.y()
        prev = self.hovered_dot
        self.hovered_dot = None

        for dot in self.dots:
            if abs(mx - dot.x) <= 10 and abs(my - dot.y) <= 10:
                self.hovered_dot = dot
                self.setCursor(Qt.PointingHandCursor)
                break
        else:
            self.setCursor(Qt.ArrowCursor)

        if self.hovered_dot != prev:
            self.update()

    def leaveEvent(self, event):
        self.hovered_dot = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self.hovered_dot:
            return
        entry = self.hovered_dot.entry
        if self.registry_table_ref and hasattr(self.registry_table_ref, "_table"):
            table   = self.registry_table_ref._table
            key_col = getattr(self.registry_table_ref, "_COL_KEY",   1)
            val_col = getattr(self.registry_table_ref, "_COL_VALUE", 2)
            for row in range(table.rowCount()):
                ki = table.item(row, key_col)
                vi = table.item(row, val_col)
                if (ki and ki.text() == entry.get("key_path", "")
                        and vi and vi.text() == entry.get("value_name", "")):
                    table.selectRow(row)
                    table.scrollToItem(ki)
                    break
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._compute_dots()
        self.update()


# Tactic header bar 
class _TacticHeader(QWidget):
    def __init__(self, tactic: str, count: int):
        super().__init__()
        self.tactic = tactic
        self.count  = count
        self.setFixedHeight(24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        accent = QColor(THEME["accent"]); accent.setAlpha(30)
        painter.fillRect(self.rect(), accent)

        painter.setPen(QPen(QColor(THEME["border"]), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        font = QFont(); font.setPointSize(9); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(THEME["accent"]))
        painter.drawText(
            QRect(LABEL_WIDTH + 8, 0, self.width() - LABEL_WIDTH - 16, self.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            f"{self.tactic}  ({self.count} change{'s' if self.count != 1 else ''})"
        )


# Main public widget 
class RegistryTimelineWidget(QFrame):

    def __init__(self):
        super().__init__()
        self.entries: list[dict]          = []
        self._swimlanes: list[_SwimlanePair] = []
        self.registry_table_ref           = None

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)
        self._init_ui()

    # UI setup

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 12, 15, 12)
        main.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Registry Change Timeline")
        title.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 16px; font-weight: bold;"
        )
        header.addWidget(title)
        header.addStretch()
        for color, label in [
            (COLOR_ADDED, "Added"),
            (COLOR_MODIFIED, "Modified"),
            (COLOR_DELETED, "Deleted"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 13px;")
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
            header.addWidget(dot)
            header.addWidget(lbl)
        main.addLayout(header)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {THEME['border']};
                background-color: {THEME['timeline_bg']};
                border-radius: 4px;
            }}
            QScrollBar:horizontal, QScrollBar:vertical {{
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {{
                background: {THEME['border']};
                border-radius: 5px;
                min-width: 30px; min-height: 30px;
            }}
        """)

        self.lane_container = QWidget()
        self.lane_container.setStyleSheet(
            f"background-color: {THEME['timeline_bg']};"
        )
        self.lane_layout = QVBoxLayout(self.lane_container)
        self.lane_layout.setSpacing(0)
        self.lane_layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel(
            "Load a baseline and snapshot then click Compare to see the registry timeline"
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {THEME['text_secondary']}; font-size: 13px; padding: 40px;"
        )
        self.lane_layout.addWidget(self._placeholder)

        self.scroll.setWidget(self.lane_container)
        main.addWidget(self.scroll)

    # Public API 

    def set_registry_table(self, ref):
        self.registry_table_ref = ref
        for sw in self._swimlanes:
            sw.set_registry_table(ref)

    def load_entries(self, entries: list[dict]):
        self.entries = entries or []
        self._build_swimlanes()

    def highlight_entry(self, entry: dict):
        for sw in self._swimlanes:
            sw.highlight_entry(entry)

    def clear_highlight(self):
        for sw in self._swimlanes:
            sw.clear_highlight()

    # Build 

    def _build_swimlanes(self):
        # Clear previous content
        for i in reversed(range(self.lane_layout.count())):
            w = self.lane_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._swimlanes = []

        if not self.entries:
            ph = QLabel("No changes found between snapshots")
            ph.setAlignment(Qt.AlignCenter)
            ph.setStyleSheet(
                f"color: {THEME['text_secondary']}; font-size: 13px; padding: 40px;"
            )
            self.lane_layout.addWidget(ph)
            return

        # Bucket entries by tactic
        tactic_entries: dict[str, list[dict]] = {t: [] for t in TACTIC_ORDER}
        for entry in self.entries:
            tactic = _tactic_for(entry.get("category", "Other"))
            tactic_entries[tactic].append(entry)

        # Compute the widest swimlane needed for container sizing
        max_width = LABEL_WIDTH + GROUP_PADDING

        for tactic in TACTIC_ORDER:
            t_entries = tactic_entries[tactic]
            if not t_entries:
                continue

            group_positions = self._compute_group_positions(t_entries)
            if group_positions:
                rightmost = max(group_positions.values())
                max_dots  = max(
                    sum(1 for e in t_entries if e.get("key_path") == kp)
                    for kp in group_positions
                )
                lane_width = rightmost + max_dots * DOT_SPACING + GROUP_PADDING
                max_width  = max(max_width, lane_width)

            # Tactic header
            header = _TacticHeader(tactic, len(t_entries))
            self.lane_layout.addWidget(header)

            # Swimlane pair
            sw = _SwimlanePair(tactic, t_entries, group_positions)
            if self.registry_table_ref:
                sw.set_registry_table(self.registry_table_ref)
            self.lane_layout.addWidget(sw)
            self._swimlanes.append(sw)

        self.lane_layout.addStretch()

        # Ensure horizontal scroll works
        vp_w = self.scroll.viewport().width()
        self.lane_container.setMinimumWidth(max(max_width, vp_w))

    def _compute_group_positions(self, entries: list[dict]) -> dict:
        key_paths = list(dict.fromkeys(e.get("key_path", "") for e in entries))
        positions = {}
        x = LABEL_WIDTH + GROUP_PADDING

        for kp in key_paths:
            positions[kp] = x
            kp_entries   = [e for e in entries if e.get("key_path") == kp]
            baseline_n   = sum(1 for e in kp_entries if e.get("change_type") in ("deleted",  "modified"))
            snapshot_n   = sum(1 for e in kp_entries if e.get("change_type") in ("added",    "modified"))
            max_dots     = max(baseline_n, snapshot_n, 1)
            x           += max_dots * DOT_SPACING + GROUP_PADDING

        return positions