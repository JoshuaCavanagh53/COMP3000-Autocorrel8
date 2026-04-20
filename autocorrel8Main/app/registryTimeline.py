from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from themes import THEME


# Change type colours
COLOR_ADDED = "#27ae60"
COLOR_MODIFIED = "#7C3AED"
COLOR_DELETED = "#c0392b"
COLOR_UNCHANGED = "#3a3a4a"

# Lane types
LANE_BASELINE = "baseline"
LANE_SNAPSHOT = "snapshot"

# Spacing constants
LABEL_WIDTH = 100
DOT_RADIUS = 6
DOT_SPACING = 22
GROUP_PADDING = 30


# Represents one dot on the registry timeline
class RegistryDot:
    def __init__(self, x, y, entry, lane_type):
        self.x = x
        self.y = y
        self.entry = entry
        self.lane_type = lane_type


# One horizontal lane, either baseline or snapshot
class RegistryLane(QWidget):
    def __init__(self, lane_type, entries, key_groups, group_positions, parent=None):
        super().__init__(parent)
        self.lane_type = lane_type
        self.entries = entries
        self.key_groups = key_groups
        self.group_positions = group_positions
        self.dots = []
        self.hovered_dot = None
        self.highlighted_entry = None
        self.registry_table_ref = None

        self.setFixedHeight(80)
        self.setMouseTracking(True)
        self._compute_dots()

    def set_registry_table(self, table_ref):
        self.registry_table_ref = table_ref

    def highlight_entry(self, entry):
        self.highlighted_entry = entry
        self.update()

    def clear_highlight(self):
        self.highlighted_entry = None
        self.update()

    def _get_dot_color(self, entry):
        change_type = entry.get("change_type", "")
        if change_type == "added":
            return COLOR_ADDED
        if change_type == "modified":
            return COLOR_MODIFIED
        if change_type == "deleted":
            return COLOR_DELETED
        return COLOR_UNCHANGED

    def _compute_dots(self):
        self.dots = []
        tl_y = self.height() // 2 if self.height() > 0 else 40

        for key_path, group_x in self.group_positions.items():
            # Get entries for this key path that belong in this lane
            lane_entries = [
                e for e in self.entries
                if e.get("key_path") == key_path and self._entry_belongs_in_lane(e)
            ]

            # Space dots within the group
            for i, entry in enumerate(lane_entries):
                x = group_x + (i * DOT_SPACING)
                self.dots.append(RegistryDot(x, tl_y, entry, self.lane_type))

    def _entry_belongs_in_lane(self, entry):
        change_type = entry.get("change_type", "")
        if self.lane_type == LANE_BASELINE:
            # Baseline shows what was there before, deleted and modified entries
            return change_type in ("deleted", "modified")
        if self.lane_type == LANE_SNAPSHOT:
            # Snapshot shows what is there after, added and modified entries
            return change_type in ("added", "modified")
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._compute_dots()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg = QColor(THEME["timeline_bg"])
        if self.lane_type == LANE_SNAPSHOT:
            bg = bg.darker(108)
        painter.fillRect(self.rect(), bg)

        # Sidebar label zone with divider
        painter.fillRect(0, 0, LABEL_WIDTH, self.height(), QColor(THEME["surface"]))
        painter.setPen(QPen(QColor(THEME["border"]), 1))
        painter.drawLine(LABEL_WIDTH, 0, LABEL_WIDTH, self.height())

        tl_y = self.height() // 2

        # Lane label
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(THEME["text_primary"]))
        label = "Before" if self.lane_type == LANE_BASELINE else "After"
        painter.drawText(QRect(10, 0, LABEL_WIDTH - 10, self.height()),
                         Qt.AlignVCenter | Qt.AlignLeft, label)

        # Thicker accent-tinted track
        track = QColor(THEME["accent"]); track.setAlpha(90)
        painter.setPen(QPen(track, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(LABEL_WIDTH + 5, tl_y, self.width() - 20, tl_y)

        # Draw dots
        for dot in self.dots:
            color = self._get_dot_color(dot.entry)
            is_hovered = dot is self.hovered_dot
            is_highlighted = (
                self.highlighted_entry is not None and
                dot.entry.get("value_name") == self.highlighted_entry.get("value_name") and
                dot.entry.get("key_path") == self.highlighted_entry.get("key_path")
            )

            if is_highlighted:
                painter.setBrush(QBrush(QColor("#ffdd00")))
                painter.setPen(QPen(QColor("#ffdd00").darker(130), 2))
                painter.drawEllipse(dot.x - 8, dot.y - 8, 16, 16)
            elif is_hovered:
                painter.setBrush(QBrush(QColor(color).lighter(140)))
                painter.setPen(QPen(QColor(color), 2))
                painter.drawEllipse(dot.x - 8, dot.y - 8, 16, 16)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(140), 1))
                painter.drawEllipse(dot.x - DOT_RADIUS, dot.y - DOT_RADIUS, DOT_RADIUS * 2, DOT_RADIUS * 2)

        # Draw tooltip for hovered dot
        if self.hovered_dot:
            self._draw_tooltip(painter, self.hovered_dot)

    def _draw_tooltip(self, painter, dot):
        entry = dot.entry
        lines = [
            entry.get("value_name", "Unknown"),
            f"Key: {entry.get('key_path', '').split(chr(92))[-1]}",
            f"Change: {entry.get('change_type', '').capitalize()}",
        ]

        if entry.get("old_data"):
            old = str(entry.get("old_data", ""))
            lines.append(f"Before: {old[:30]}..." if len(old) > 30 else f"Before: {old}")
        if entry.get("new_data"):
            new = str(entry.get("new_data", ""))
            lines.append(f"After: {new[:30]}..." if len(new) > 30 else f"After: {new}")

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        m = painter.fontMetrics()
        max_width = max(m.horizontalAdvance(l) for l in lines)
        line_height = m.height()
        tooltip_w = max_width + 20
        tooltip_h = line_height * len(lines) + 12

        tx = max(LABEL_WIDTH + 5, min(dot.x - tooltip_w // 2, self.width() - tooltip_w - 5))
        ty = 4

        color = self._get_dot_color(dot.entry)
        painter.setBrush(QBrush(QColor(THEME["surface_elevated"])))
        painter.setPen(QPen(QColor(color), 1))
        painter.drawRoundedRect(tx, ty, tooltip_w, tooltip_h, 4, 4)

        painter.setPen(QColor(THEME["text_primary"]))
        y_offset = ty + line_height
        for line in lines:
            painter.drawText(QRect(tx + 10, y_offset - line_height + 4, tooltip_w - 20, line_height),
                             Qt.AlignVCenter | Qt.AlignLeft, line)
            y_offset += line_height

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

        # Select matching row in the registry table
        if self.registry_table_ref and hasattr(self.registry_table_ref, "_table"):
            table = self.registry_table_ref._table
            domain_col = getattr(self.registry_table_ref, "_COL_KEY", 1)
            for row in range(table.rowCount()):
                item = table.item(row, domain_col)
                if item and item.text() == entry.get("key_path", ""):
                    value_col = getattr(self.registry_table_ref, "_COL_VALUE", 2)
                    value_item = table.item(row, value_col)
                    if value_item and value_item.text() == entry.get("value_name", ""):
                        table.selectRow(row)
                        table.scrollToItem(item)
                        break

        event.accept()


# X axis showing key path group labels
class RegistryKeyAxis(QWidget):
    def __init__(self, key_groups, group_positions):
        super().__init__()
        self.key_groups = key_groups
        self.group_positions = group_positions
        self.setFixedHeight(36)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME["timeline_bg"]))

        painter.fillRect(0, 0, LABEL_WIDTH, self.height(), QColor(THEME["surface"]))
        painter.setPen(QPen(QColor(THEME["border"]), 1))
        painter.drawLine(LABEL_WIDTH, 0, LABEL_WIDTH, self.height())

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        for key_path, x in self.group_positions.items():
            # Just show the last part of the path
            short_label = key_path.split("\\")[-1]

            tick_col = QColor(THEME["border"]); tick_col.setAlpha(120)
            painter.setPen(QPen(tick_col, 1))
            painter.drawLine(x, 0, x, 8)

            painter.setPen(QColor(THEME["text_secondary"]))
            painter.drawText(QRect(x - 50, 10, 100, 22), Qt.AlignCenter, short_label)


# Main registry timeline widget
class RegistryTimelineWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.entries = []
        self.key_groups = []
        self.group_positions = {}
        self.baseline_lane = None
        self.snapshot_lane = None
        self.registry_table_ref = None

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Registry Change Timeline")
        title.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        # Legend
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

        main_layout.addLayout(header)

        # Scroll area for the lanes
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {THEME['border']};
                background-color: {THEME['timeline_bg']};
                border-radius: 4px;
            }}
            QScrollBar:horizontal {{
                height: 10px;
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME['border']};
                border-radius: 5px;
                min-width: 30px;
            }}
        """)

        self.lane_container = QWidget()
        self.lane_container.setStyleSheet(f"background-color: {THEME['timeline_bg']};")
        self.lane_layout = QVBoxLayout(self.lane_container)
        self.lane_layout.setSpacing(0)
        self.lane_layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder shown before any data is loaded
        self.placeholder = QLabel("Load a baseline and snapshot then click Compare to see the registry timeline")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px; padding: 30px;")
        self.lane_layout.addWidget(self.placeholder)

        self.scroll.setWidget(self.lane_container)
        main_layout.addWidget(self.scroll)

    def set_registry_table(self, table_ref):
        self.registry_table_ref = table_ref
        if self.baseline_lane:
            self.baseline_lane.set_registry_table(table_ref)
        if self.snapshot_lane:
            self.snapshot_lane.set_registry_table(table_ref)

    def load_entries(self, entries):
        self.entries = entries or []
        self._build_lanes()

    def highlight_entry(self, entry):
        if self.baseline_lane:
            self.baseline_lane.highlight_entry(entry)
        if self.snapshot_lane:
            self.snapshot_lane.highlight_entry(entry)

    def clear_highlight(self):
        if self.baseline_lane:
            self.baseline_lane.clear_highlight()
        if self.snapshot_lane:
            self.snapshot_lane.clear_highlight()

    def _build_lanes(self):
        # Clear existing lanes
        for i in reversed(range(self.lane_layout.count())):
            w = self.lane_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        self.baseline_lane = None
        self.snapshot_lane = None

        if not self.entries:
            self.placeholder = QLabel("No changes found between snapshots")
            self.placeholder.setAlignment(Qt.AlignCenter)
            self.placeholder.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px; padding: 30px;")
            self.lane_layout.addWidget(self.placeholder)
            return

        # Work out unique key paths and their x positions
        self.key_groups = list(dict.fromkeys(e.get("key_path", "") for e in self.entries))
        self._compute_group_positions()

        # Set container width to fit all groups
        total_width = max(self.group_positions.values()) + GROUP_PADDING * 2 + 100 if self.group_positions else 600
        self.lane_container.setMinimumWidth(max(total_width, self.scroll.viewport().width()))

        # Baseline lane
        self.baseline_lane = RegistryLane(LANE_BASELINE, self.entries, self.key_groups, self.group_positions)
        if self.registry_table_ref:
            self.baseline_lane.set_registry_table(self.registry_table_ref)
        self.lane_layout.addWidget(self.baseline_lane, 1)

        # Key axis divider between lanes
        axis = RegistryKeyAxis(self.key_groups, self.group_positions)
        self.lane_layout.addWidget(axis)

        # Snapshot lane
        self.snapshot_lane = RegistryLane(LANE_SNAPSHOT, self.entries, self.key_groups, self.group_positions)
        if self.registry_table_ref:
            self.snapshot_lane.set_registry_table(self.registry_table_ref)
        self.lane_layout.addWidget(self.snapshot_lane, 1)

    def _compute_group_positions(self):

        self.group_positions = {}
        x = LABEL_WIDTH + GROUP_PADDING

        for key_path in self.key_groups:
            self.group_positions[key_path] = x
            baseline_count = sum(
                1 for e in self.entries
                if e.get("key_path") == key_path and e.get("change_type") in ("deleted", "modified")
            )
            snapshot_count = sum(
                1 for e in self.entries
                if e.get("key_path") == key_path and e.get("change_type") in ("added", "modified")
            )
            max_dots = max(baseline_count, snapshot_count, 1)
            group_width = (max_dots * DOT_SPACING) + GROUP_PADDING
            x += group_width