from calendar import c

from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QScrollArea, QComboBox, QSlider, QTableWidget, QHeaderView, 
    QTableWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QWheelEvent
from datetime import timedelta
from collections import defaultdict
from correlationVizuals import *

from themes import THEME

# Represents one event in a timeline
class TimelineEvent:
    def __init__(self, timestamp, event_type, value, pcap_name):  
        self.timestamp = timestamp
        self.event_type = event_type
        self.value = value
        self.pcap_name = pcap_name
        self.x_pos = 0
        self.normalized_ts = 0
        self.protocol = None 


# Event cluster for grouping nearby events
class EventCluster:
    def __init__(self, events, x_start, x_end):
        self.events = events
        self.x_start = x_start
        self.x_end = x_end
        self.x_center = (x_start + x_end) // 2
        self.count = len(events)
        self.expanded = False
        # Stored after each paint 
        self._expanded_rect = None   
        self._dot_positions = []    

    def toggle_expansion(self):

        # Toggle between expanded and collapsed state
        self.expanded = not self.expanded
        if not self.expanded:
            # Clear cached geometry so stale rects can't trigger false hits
            self._expanded_rect = None
            self._dot_positions = []
        return self.expanded

    def contains_point(self, x, y, timeline_y, threshold=10):

        # Check if a point is within the cluster bounds
        if not self.expanded:
            # Collapsed: check if click lands on the bar
            return (self.x_start - threshold <= x <= self.x_end + threshold and
                    timeline_y - 15 <= y <= timeline_y + 15)
        else:
            # Expanded: use the actual painted rect so the hit area matches visually
            if self._expanded_rect:
                rx, ry, rw, rh = self._expanded_rect
                return rx <= x <= rx + rw and ry <= y <= ry + rh
            # Fallback before first paint
            return (self.x_start - threshold <= x <= self.x_end + threshold and
                    timeline_y - 60 <= y <= timeline_y + 60)

# Minimap widget showing full timeline overview
class TimelineMinimap(QWidget):
    def __init__(self, start_time, end_time, height=40):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.setFixedHeight(height)
        self.setMinimumWidth(400)
        self.visible_start = 0.0
        self.visible_end = 1.0
        self.dragging = False
        self.drag_start_x = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
    # Get the full visible range of the timeline
    def set_visible_range(self, start_pct, end_pct):
        self.visible_start = max(0.0, min(1.0, start_pct))
        self.visible_end = max(0.0, min(1.0, end_pct))
        self.update()
    
    # Paint the minimap above the timelines
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        # Don't draw anything meaningful until times are set
        if self.start_time is None or self.end_time is None:
            return

        painter.setPen(QPen(QColor(THEME['border']), 1))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)
        
        bar_y = self.height() // 2
        painter.setPen(QPen(QColor(THEME['border']), 2))
        painter.drawLine(10, bar_y, self.width() - 10, bar_y)
        
        bar_width = self.width() - 20
        visible_x1 = 10 + int(bar_width * self.visible_start)
        visible_x2 = 10 + int(bar_width * self.visible_end)
        
        painter.fillRect(visible_x1, bar_y - 8, visible_x2 - visible_x1, 16,
                        QColor(THEME['accent']).lighter(150))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRect(visible_x1, bar_y - 8, visible_x2 - visible_x1, 16)
        
        painter.setPen(QColor(THEME['text_secondary']))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        
        start_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str   = self.end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        painter.drawText(QRect(10, 0, 150, bar_y - 10),
                        Qt.AlignLeft | Qt.AlignBottom, start_str)
        painter.drawText(QRect(self.width() - 160, 0, 150, bar_y - 10),
                        Qt.AlignRight | Qt.AlignBottom, end_str)

# Optimized timeline with clustering
class PCAPTimeline(QWidget):
    def __init__(self, pcap_name, events, start_time, end_time, height=120, pixels_per_second=10):
        super().__init__()
        self.pcap_name = pcap_name
        self.events = events
        self.start_time = start_time
        self.end_time = end_time
        self.timeline_height = height
        self.highlighted_events = []
        self.pixels_per_second = pixels_per_second
        self.hovered_event = None
        self.hovered_cluster = None
        self.clusters = []
        self.use_clustering = True
        self.cluster_threshold = 15  # Events within 15 pixels of each other get clustered
        self.visible_event_set = None  # None = show all; set = only show members
        
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.setMouseTracking(True)

        total_duration = (self.end_time - self.start_time).total_seconds()
        required_width = int(total_duration * self.pixels_per_second) + 200
        self.setMinimumWidth(required_width)

        self._calculate_event_positions()
        self._create_clusters()

    def _calculate_event_positions(self):
        if not self.events:
            return
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        if total_duration == 0:
            return
        
        for event in self.events:
            elapsed = (event.timestamp - self.start_time).total_seconds()
            event.x_pos = 100 + int(elapsed * self.pixels_per_second)

    def _create_clusters(self, source_events=None):
        events = source_events if source_events is not None else self.events
        if not events or not self.use_clustering:
            self.clusters = []
            return
        sorted_events = sorted(events, key=lambda e: e.x_pos)
        self.clusters = []
        current_cluster_events = [sorted_events[0]]
        cluster_start = sorted_events[0].x_pos
        for event in sorted_events[1:]:
            if event.x_pos - current_cluster_events[-1].x_pos <= self.cluster_threshold:
                current_cluster_events.append(event)
            else:
                if len(current_cluster_events) > 1:
                    cluster_end = current_cluster_events[-1].x_pos
                    self.clusters.append(EventCluster(current_cluster_events, cluster_start, cluster_end))
                current_cluster_events = [event]
                cluster_start = event.x_pos
        if len(current_cluster_events) > 1:
            cluster_end = current_cluster_events[-1].x_pos
            self.clusters.append(EventCluster(current_cluster_events, cluster_start, cluster_end))

    def set_visible_events(self, event_set):

        # Filter which events are drawn, pass None to restore show all
        self.visible_event_set = event_set
        if event_set is None:
            self._create_clusters()
        else:
            self._create_clusters(source_events=[e for e in self.events if e in event_set])
        self.update()

    def clear_visible_filter(self):

        # Remove the visibility filter and show all events
        self.set_visible_events(None)

    def set_highlighted_events(self, events):
        self.highlighted_events = events if events else []
        self.update()

    def clear_highlights(self):
        self.highlighted_events = []
        self.update()

    def mouseMoveEvent(self, event):
        mouse_x = event.x()
        mouse_y = event.y()
        timeline_y = self.timeline_height // 2
        
        # Check clusters first
        self.hovered_cluster = None
        cursor_over_cluster = False
        
        for cluster in self.clusters:
            if cluster.contains_point(mouse_x, mouse_y, timeline_y):
                self.hovered_cluster = cluster
                self.hovered_event = None
                cursor_over_cluster = True
                self.update()
                break
        
        # Set cursor to pointing hand over clusters
        if cursor_over_cluster:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            
            # Check individual events if not over a cluster
            self.hovered_event = None
            for ev in self.events:
                if self.visible_event_set is not None and ev not in self.visible_event_set:
                    continue
                # Only check events not in clusters or highlighted
                if ev in self.highlighted_events or any(ev in c.events for c in self.clusters):
                    if ev in self.highlighted_events and abs(ev.x_pos - mouse_x) < 10:
                        self.hovered_event = ev
                        break
                elif abs(ev.x_pos - mouse_x) < 10:
                    self.hovered_event = ev
                    break
            
            if not cursor_over_cluster:
                self.update()

    def leaveEvent(self, event):
        self.hovered_event = None
        self.hovered_cluster = None
        self.setCursor(Qt.ArrowCursor)  # Reset cursor
        self.update()
    
    def mousePressEvent(self, event):

        # Handle mouse clicks on events first, then clusters
        if event.button() != Qt.LeftButton:
            return

        mouse_x    = event.x()
        mouse_y    = event.y()
        timeline_y = self.timeline_height // 2

        # Events inside collapsed clusters shouldn't intercept clicks meant for the cluster bar
        clustered_events = set()
        for cluster in self.clusters:
            if not cluster.expanded:
                clustered_events.update(cluster.events)

        # Check individual events on the open timeline
        for event_obj in self.events:
            if event_obj in clustered_events:
                continue
            if self.visible_event_set is not None and event_obj not in self.visible_event_set:
                continue
            if abs(mouse_x - event_obj.x_pos) < 15 and abs(mouse_y - timeline_y) < 25:
                parent = self.parent()
                while parent and not hasattr(parent, 'on_timeline_event_clicked'):
                    parent = parent.parent()
                if parent and hasattr(parent, 'on_timeline_event_clicked'):
                    parent.on_timeline_event_clicked(event_obj, self.pcap_name)
                event.accept()
                return

        # Check dots inside expanded clusters using their painted positions
        DOT_HIT_R = 8
        for cluster in self.clusters:
            if not cluster.expanded:
                continue
            for (cx, cy, event_obj) in cluster._dot_positions:
                if abs(mouse_x - cx) <= DOT_HIT_R and abs(mouse_y - cy) <= DOT_HIT_R:
                    parent = self.parent()
                    while parent and not hasattr(parent, 'on_timeline_event_clicked'):
                        parent = parent.parent()
                    if parent and hasattr(parent, 'on_timeline_event_clicked'):
                        parent.on_timeline_event_clicked(event_obj, self.pcap_name)
                    event.accept()
                    return

        # 3. Check the cluster box itself, only reached if no dot was hit
        for cluster in self.clusters:
            if cluster.contains_point(mouse_x, mouse_y, timeline_y):
                cluster.toggle_expansion()
                self.update()
                event.accept()
                return

        super().mousePressEvent(event)

    def _compute_expanded_rect(self, cluster):
        
        # Return (box_x, box_y, box_w, box_h) for an expanded cluster without painting.
        
        DOT_R       = 5
        COL_SPACING = 22
        ROW_SPACING = 22
        H_PAD       = 14
        V_PAD_TOP   = 24
        V_PAD_BOT   = 10
        MAX_COLS    = 10

        n    = cluster.count
        cols = min(MAX_COLS, n)
        rows = (n + cols - 1) // cols

        content_w = (cols - 1) * COL_SPACING if cols > 1 else 0
        content_h = (rows - 1) * ROW_SPACING if rows > 1 else 0
        box_w = content_w + H_PAD * 2 + DOT_R * 2
        box_h = content_h + V_PAD_TOP + V_PAD_BOT + DOT_R * 2

        timeline_y = self.timeline_height // 2
        box_x = max(105, cluster.x_center - box_w // 2)
        box_y = timeline_y - box_h // 2
        return (box_x, box_y, box_w, box_h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        # Draw PCAP name
        painter.setPen(QColor(THEME['text_primary']))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(10, 10, 85, 20), Qt.AlignLeft | Qt.AlignVCenter, self.pcap_name)
        
        # Draw timeline bar
        timeline_y = self.timeline_height // 2
        painter.setPen(QPen(QColor(THEME['border']), 2))
        painter.drawLine(100, timeline_y, self.width() - 20, timeline_y)
        
        # Get visible region for culling
        viewport_rect = self.visibleRegion().boundingRect()

        # Pre-compute bounding rects for all expanded clusters so we can occlude
        # anything that sits behind them before they are drawn.
        expanded_rects = []
        for cluster in self.clusters:
            if cluster.expanded:
                rx, ry, rw, rh = self._compute_expanded_rect(cluster)
                expanded_rects.append(QRect(rx, ry, rw, rh))

        def behind_expanded(x):
            
            # Return True if pixel x falls inside any expanded cluster box.
            return any(r.left() <= x <= r.right() for r in expanded_rects)

        # Collapsed clusters 
        for cluster in self.clusters:
            if cluster.expanded:
                continue
            if cluster.x_end < viewport_rect.left() - 50 or cluster.x_start > viewport_rect.right() + 50:
                continue
            # Hide this collapsed bar if its centre sits inside an expanded cluster box
            if behind_expanded(cluster.x_center):
                continue
            is_hovered = cluster == self.hovered_cluster
            self._draw_cluster(painter, cluster, timeline_y, is_hovered)

        # Individual events 
        clustered_events = set()
        expanded_cluster_events = set()

        for cluster in self.clusters:
            if cluster.expanded:
                expanded_cluster_events.update(cluster.events)
            else:
                clustered_events.update(cluster.events)

        for ev in self.events:
            if ev.x_pos < viewport_rect.left() - 50 or ev.x_pos > viewport_rect.right() + 50:
                continue
            if self.visible_event_set is not None and ev not in self.visible_event_set:
                continue
            # Events owned by an expanded cluster are drawn inside that cluster box
            if ev in expanded_cluster_events:
                continue
            # Events in collapsed clusters are hidden unless highlighted
            if ev in clustered_events and ev not in self.highlighted_events:
                continue
            # Hide lone events that sit behind an expanded cluster box
            if behind_expanded(ev.x_pos):
                continue

            is_highlighted = ev in self.highlighted_events
            is_hovered     = ev == self.hovered_event

            if is_highlighted:
                self._draw_highlighted_event(painter, ev, timeline_y)
            elif is_hovered:
                self._draw_hovered_event(painter, ev, timeline_y)
            else:
                color = self._get_event_color(ev.event_type)
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color), 1))
                painter.drawEllipse(ev.x_pos - 4, timeline_y - 4, 8, 8)

        # Expanded clusters drawn last so they paint over everything
        for cluster in self.clusters:
            if not cluster.expanded:
                continue
            if cluster.x_end < viewport_rect.left() - 50 or cluster.x_start > viewport_rect.right() + 50:
                continue
            is_hovered = cluster == self.hovered_cluster
            self._draw_cluster(painter, cluster, timeline_y, is_hovered)

        # Draw tooltips last
        if self.hovered_event:
            self._draw_tooltip(painter, self.hovered_event)
        elif self.hovered_cluster and not self.hovered_cluster.expanded:
            self._draw_cluster_tooltip(painter, self.hovered_cluster)

    def _draw_cluster(self, painter, cluster, timeline_y, is_hovered):
        
        # Draw a cluster of events as a bar or expanded view
        if not cluster.expanded:
            # Collapsed state draw as a compact bar
            width = max(8, cluster.x_end - cluster.x_start)
            
            # Choose color based on hover state
            if is_hovered:
                color = QColor(THEME['accent']).lighter(130)
                border_color = QColor(THEME['accent'])
                border_width = 2
            else:
                color = QColor(THEME['text_secondary']).darker(150)
                border_color = QColor(THEME['border'])
                border_width = 1
            
            # Draw cluster bar
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(border_color, border_width))
            painter.drawRect(cluster.x_start - 2, timeline_y - 8, width + 4, 16)
            
            # Draw event count
            painter.setPen(QColor(THEME['text_primary']))
            font = QFont()
            font.setPointSize(7 if cluster.count < 100 else 6)
            font.setBold(True)
            painter.setFont(font)
            count_text = str(cluster.count)
            painter.drawText(QRect(cluster.x_start - 2, timeline_y - 6, width + 4, 12),
                           Qt.AlignCenter, count_text)
            
            # Draw click hint if hovered
            if is_hovered:
                painter.setPen(QColor(THEME['text_secondary']))
                font.setPointSize(7)
                font.setBold(False)
                painter.setFont(font)
                hint_text = "Click to expand"
                painter.drawText(QRect(cluster.x_start - 20, timeline_y + 12, width + 40, 15),
                               Qt.AlignCenter, hint_text)
        else:
            # Expanded state, draw individual events spread vertically
            self._draw_expanded_cluster(painter, cluster, timeline_y, is_hovered)

    def _draw_expanded_cluster(self, painter, cluster, timeline_y, is_hovered):

        # Draw an expanded cluster showing individual events in an even grid
        # Layout constants
        DOT_R       = 5    # dot radius
        COL_SPACING = 22   # horizontal gap between dot centres
        ROW_SPACING = 22   # vertical gap between dot centres
        H_PAD       = 14   # horizontal padding inside the box
        V_PAD_TOP   = 24   # space reserved at the top for the header bar
        V_PAD_BOT   = 10   # bottom padding
        MAX_COLS    = 10   # cap columns so the box doesn't run off screen

        n    = cluster.count
        cols = min(MAX_COLS, n)
        rows = (n + cols - 1) // cols

        # Size the box to fit the grid exactly
        content_w = (cols - 1) * COL_SPACING if cols > 1 else 0
        content_h = (rows - 1) * ROW_SPACING if rows > 1 else 0
        box_w = content_w + H_PAD * 2 + DOT_R * 2
        box_h = content_h + V_PAD_TOP + V_PAD_BOT + DOT_R * 2

        # Centre the box on the cluster, clamp so it doesn't clip the label column
        box_x = max(105, cluster.x_center - box_w // 2)
        box_y = timeline_y - box_h // 2

        # Store the painted rect so contains_point can use it for hit-testing
        cluster._expanded_rect = (box_x, box_y, box_w, box_h)

        # Draw box background
        painter.setBrush(QBrush(QColor(THEME['surface_elevated']).lighter(105)))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRoundedRect(box_x, box_y, box_w, box_h, 6, 6)

        # Draw header bar, this is the collapse click target
        header_rect = QRect(box_x, box_y, box_w, V_PAD_TOP - 2)
        painter.fillRect(header_rect, QColor(THEME['accent']).darker(130))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(THEME['text_primary']))
        painter.drawText(header_rect, Qt.AlignCenter,
                         f"▲ Click anywhere to collapse  ({n} events)")

        # Work out where the first dot centre sits
        dots_origin_x = box_x + H_PAD + DOT_R
        dots_origin_y = box_y + V_PAD_TOP + DOT_R

        mouse_pos = self.mapFromGlobal(self.cursor().pos())

        # Rebuild dot positions every paint so click detection stays in sync
        cluster._dot_positions = []

        for idx, ev in enumerate(cluster.events):
            row = idx // cols
            col = idx % cols
            cx  = dots_origin_x + col * COL_SPACING
            cy  = dots_origin_y + row * ROW_SPACING

            # Store position so mousePressEvent can match clicks to events
            cluster._dot_positions.append((cx, cy, ev))

            color   = self._get_event_color(ev.event_type)
            hovered = abs(mouse_pos.x() - cx) < DOT_R + 3 and abs(mouse_pos.y() - cy) < DOT_R + 3

            if hovered:
                painter.setBrush(QBrush(QColor(color).lighter(140)))
                painter.setPen(QPen(QColor(color).lighter(160), 2))
                painter.drawEllipse(cx - DOT_R - 2, cy - DOT_R - 2,
                                    (DOT_R + 2) * 2, (DOT_R + 2) * 2)
                self._draw_tooltip(painter, ev, cx, box_y - 10)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(120), 1))
                painter.drawEllipse(cx - DOT_R, cy - DOT_R, DOT_R * 2, DOT_R * 2)
    
    def _draw_cluster_tooltip(self, painter, cluster):
        
        # Draw tooltip for event cluster
        tooltip_text = f"Event Cluster\n{cluster.count} events\nClick to see details"
        
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        
        lines = tooltip_text.split('\n')
        max_width = max(metrics.horizontalAdvance(line) for line in lines)
        line_height = metrics.height()
        tooltip_height = line_height * len(lines) + 10
        tooltip_width = max_width + 20
        
        tooltip_x = cluster.x_center - tooltip_width // 2
        tooltip_y = 10
        
        tooltip_x = max(10, min(tooltip_x, self.width() - tooltip_width - 10))
        
        painter.setBrush(QBrush(QColor(THEME['surface_elevated'])))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRoundedRect(tooltip_x, tooltip_y, tooltip_width, tooltip_height, 4, 4)
        
        painter.setPen(QColor(THEME['text_primary']))
        y_offset = tooltip_y + line_height
        for line in lines:
            painter.drawText(QRect(tooltip_x + 10, y_offset - line_height + 5, 
                                  tooltip_width - 20, line_height), 
                           Qt.AlignLeft | Qt.AlignVCenter, line)
            y_offset += line_height
    
    def _draw_highlighted_event(self, painter, event, timeline_y):
        highlight_color = QColor("#ffdd00")  
        painter.setBrush(QBrush(highlight_color))
        painter.setPen(QPen(highlight_color.darker(120), 2))
        painter.drawEllipse(event.x_pos - 7, timeline_y - 7, 14, 14)

    def _draw_hovered_event(self, painter, event, timeline_y):
        color = self._get_event_color(event.event_type)
        painter.setBrush(QBrush(QColor(color).lighter(130)))
        painter.setPen(QPen(QColor(color).lighter(150), 2))
        painter.drawEllipse(event.x_pos - 6, timeline_y - 6, 12, 12)

    def _draw_tooltip(self, painter, event, tooltip_x=None, tooltip_y=None):
        
        # Draw tooltip for an event, optionally at custom position
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        tooltip_text = f"{event.event_type.upper()}: {event.value}\nTime: {time_str}"
        
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        
        lines = tooltip_text.split('\n')
        max_width = max(metrics.horizontalAdvance(line) for line in lines)
        line_height = metrics.height()
        tooltip_height = line_height * len(lines) + 10
        tooltip_width = max_width + 20
        
        # Use provided coordinates or calculate from event position
        if tooltip_x is None:
            tooltip_x = event.x_pos - tooltip_width // 2
        else:
            tooltip_x = tooltip_x - tooltip_width // 2
            
        if tooltip_y is None:
            tooltip_y = 10
        
        tooltip_x = max(10, min(tooltip_x, self.width() - tooltip_width - 10))
        
        painter.setBrush(QBrush(QColor(THEME['surface_elevated'])))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRoundedRect(tooltip_x, tooltip_y, tooltip_width, tooltip_height, 4, 4)
        
        painter.setPen(QColor(THEME['text_primary']))
        y_offset = tooltip_y + line_height
        for line in lines:
            painter.drawText(QRect(tooltip_x + 10, y_offset - line_height + 5, 
                                  tooltip_width - 20, line_height), 
                           Qt.AlignLeft | Qt.AlignVCenter, line)
            y_offset += line_height

    def _get_event_color(self, event_type):
        colors = {
            'domain': THEME['event_domain'],
            'ip': THEME['event_ip'],
            'port': THEME['event_port'],
        }
        return colors.get(event_type, THEME['accent'])


# Enhanced timestamp axis
class TimestampAxis(QWidget):
    def __init__(self, start_time, end_time, height=40, pixels_per_second=50):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.pixels_per_second = pixels_per_second
        self.setFixedHeight(height)
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        required_width = int(total_duration * self.pixels_per_second) + 200
        self.setMinimumWidth(required_width)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Get visible region
        viewport_rect = self.visibleRegion().boundingRect()
        
        if total_duration <= 60:
            interval = 5
            time_format = "%H:%M:%S"
        elif total_duration <= 300:
            interval = 30
            time_format = "%H:%M:%S"
        elif total_duration <= 1800:
            interval = 60
            time_format = "%H:%M:%S"
        elif total_duration <= 3600:
            interval = 300
            time_format = "%H:%M:%S"
        elif total_duration <= 86400:
            interval = 1800
            time_format = "%H:%M"
        else:
            interval = 3600
            time_format = "%m/%d %H:%M"
        
        # Only draw visible markers
        current_time = self.start_time
        while current_time <= self.end_time:
            elapsed = (current_time - self.start_time).total_seconds()
            x_pos = 100 + int(elapsed * self.pixels_per_second)
            
            # Cull offscreen markers
            if x_pos < viewport_rect.left() - 100 or x_pos > viewport_rect.right() + 100:
                current_time += timedelta(seconds=interval)
                continue
            
            painter.setPen(QPen(QColor(THEME['text_primary']), 2))
            painter.drawLine(x_pos, 5, x_pos, 20)
            
            painter.setPen(QColor(THEME['text_primary']))
            time_str = current_time.strftime(time_format)
            painter.drawText(QRect(x_pos - 50, 20, 100, 18), 
                           Qt.AlignCenter, time_str)
            
            current_time += timedelta(seconds=interval)
        
        # Draw minor ticks
        minor_interval = interval / 5
        current_time = self.start_time
        painter.setPen(QPen(QColor(THEME['border']), 1))
        
        while current_time <= self.end_time:
            elapsed = (current_time - self.start_time).total_seconds()
            x_pos = 100 + int(elapsed * self.pixels_per_second)
            
            if viewport_rect.left() - 50 <= x_pos <= viewport_rect.right() + 50:
                painter.drawLine(x_pos, 10, x_pos, 15)
            
            current_time += timedelta(seconds=minor_interval)


# Optimized overlay with correlation limiting
class CorrelationOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.correlations = []
        self.pcap_timelines = []
        self.scroll_area = None
        self._initialized = False
        self.max_visible_lines = 100  # Limit correlation lines drawn
        
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
    
    def set_data(self, correlations, pcap_timelines, scroll_area):
        self.correlations = correlations if correlations else []
        self.pcap_timelines = pcap_timelines if pcap_timelines else []
        self.scroll_area = scroll_area
        self._initialized = True
        self.update()
    
    def paintEvent(self, event):
        if not self._initialized or not self.correlations:
            return
        if not self.scroll_area or not self.pcap_timelines:
            return
        
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = QPen(QColor(THEME.get('correlation_line', '#FF6B6B')), 2, Qt.DashLine)
            painter.setPen(pen)
            
            h_scrollbar = self.scroll_area.horizontalScrollBar()
            scroll_offset = h_scrollbar.value() if h_scrollbar else 0
            
            # Get viewport for culling
            viewport_rect = self.rect()
            
            lines_drawn = 0
            for event1, event2, time_diff in self.correlations:
                # Limit total lines drawn
                if lines_drawn >= self.max_visible_lines:
                    break
                
                try:
                    timeline1 = next((t for t in self.pcap_timelines if t.pcap_name == event1.pcap_name), None)
                    timeline2 = next((t for t in self.pcap_timelines if t.pcap_name == event2.pcap_name), None)
                    
                    if not timeline1 or not timeline2:
                        continue
                    
                    if not timeline1.isVisible() or not timeline2.isVisible():
                        continue
                    
                    x1 = event1.x_pos - scroll_offset
                    x2 = event2.x_pos - scroll_offset
                    
                    # Cull offscreen lines
                    if (x1 < -50 and x2 < -50) or (x1 > viewport_rect.width() + 50 and x2 > viewport_rect.width() + 50):
                        continue
                    
                    y1_widget = timeline1.mapTo(self.parent(), QPoint(0, timeline1.height() // 2))
                    y1 = y1_widget.y()

                    y2_widget = timeline2.mapTo(self.parent(), QPoint(0, timeline2.height() // 2))
                    y2 = y2_widget.y()
          
                    painter.drawLine(x1, y1, x2, y2)
                    lines_drawn += 1
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error in paintEvent: {e}")


class CrossPCAPTimelineWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.pcap_timelines = []
        self.timestamp_axis = None
        self.correlations = []
        self.all_correlations = []  # Store all before filtering
        self.grouped_visible = {}   # (type, value), pcap_name: [events]
        self.filter_mode = 'found_in_both'   # 'found_in_both' | 'found_multiple_times'
        self.time_threshold = 5.0
        self.pixels_per_second = 50
        self.overlay = None
        self.minimap = None
        self.start_time = None
        self.end_time = None
        self.max_correlations = 500  # Limit correlations shown
        self._incognito_lane = None

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Cross-PCAP Timeline Correlation")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Performance info
        self.perf_label = QLabel("")
        self.perf_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px;")
        header_layout.addWidget(self.perf_label)
        
        # Zoom control
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {THEME['border']};
                height: 4px;
                background: {THEME['button_bg']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['accent']};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        header_layout.addWidget(self.zoom_slider)
        
        self.zoom_value_label = QLabel("50px/s")
        self.zoom_value_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; min-width: 60px;")
        header_layout.addWidget(self.zoom_value_label)
        
        # Mode selector
        filter_label = QLabel("Show:")
        filter_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Found in Both', 'Found Multiple Times'])
        self.filter_combo.setToolTip(
            "Found in Both, only show events that appear across multiple PCAPs\n"
            "Found Multiple Times, show events with more than one occurrence anywhere"
        )
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                selection-background-color: {THEME['accent']};
            }}
        """)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.filter_combo)
        

        layout.addLayout(header_layout)
        
        # Minimap
        minimap_container = QHBoxLayout()
        minimap_label = QLabel("Overview:")
        minimap_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        minimap_container.addWidget(minimap_label)
        
        self.minimap = TimelineMinimap(None, None)
        self.minimap.hide()
        minimap_container.addWidget(self.minimap, 1)
        
        layout.addLayout(minimap_container)
        
        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setMinimumHeight(300)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {THEME['border']};
                background-color: {THEME['timeline_bg']};
                border-radius: 4px;
            }}
            QScrollBar:horizontal {{
                height: 14px;
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME['border']};
                border-radius: 7px;
                min-width: 40px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME['text_secondary']};
            }}
            QScrollBar:vertical {{
                width: 14px;
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']};
                border-radius: 7px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME['text_secondary']};
            }}
        """)
        
        self.timeline_container = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setSpacing(2)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll.setWidget(self.timeline_container)
        self.scroll.horizontalScrollBar().valueChanged.connect(self._update_minimap_position)
        
        layout.addWidget(self.scroll)
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        jump_start_btn = QPushButton("⏮ Start")
        jump_start_btn.clicked.connect(lambda: self.jump_to_position(0.0))
        jump_start_btn.setStyleSheet(self._get_nav_button_style())
        nav_layout.addWidget(jump_start_btn)
        
        jump_end_btn = QPushButton("End ⏭")
        jump_end_btn.clicked.connect(lambda: self.jump_to_position(1.0))
        jump_end_btn.setStyleSheet(self._get_nav_button_style())
        nav_layout.addWidget(jump_end_btn)
        
        nav_layout.addStretch()
        
        # Correlation limit control
        limit_label = QLabel("Max correlations:")
        limit_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        nav_layout.addWidget(limit_label)
        
        self.limit_slider = QSlider(Qt.Horizontal)
        self.limit_slider.setMinimum(50)
        self.limit_slider.setMaximum(1000)
        self.limit_slider.setValue(500)
        self.limit_slider.setSingleStep(50)
        self.limit_slider.setMaximumWidth(120)
        self.limit_slider.valueChanged.connect(self._on_limit_changed)
        self.limit_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {THEME['border']};
                height: 4px;
                background: {THEME['button_bg']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['accent']};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """)
        nav_layout.addWidget(self.limit_slider)
        
        self.limit_value_label = QLabel("500")
        self.limit_value_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; min-width: 40px;")
        nav_layout.addWidget(self.limit_value_label)
        
        layout.addLayout(nav_layout)
        
        # Correlation results
        correlation_header = QHBoxLayout()
        
        correlation_title = QLabel("Correlations Found:")
        correlation_title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: bold;
        """)
        correlation_header.addWidget(correlation_title)
        
        self.correlation_count_label = QLabel("0 correlations")
        self.correlation_count_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
        """)
        correlation_header.addWidget(self.correlation_count_label)
        
        correlation_header.addStretch()
        
        layout.addLayout(correlation_header)
        
        # Info panel overlay (initially hidden)
        self.info_panel = TimelineInfoPanel(self)
        self.info_panel.hide()
    
    
    def _get_nav_button_style(self):
        return f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border-color: {THEME['accent']};
            }}
        """
    
    def _on_limit_changed(self, value):
        
        # Update correlation limit
        self.max_correlations = value
        self.limit_value_label.setText(str(value))
        self._apply_correlation_limit()
    
    def _apply_correlation_limit(self):
        
        # Apply correlation limit and update display
        if not self.all_correlations:
            return
        
        # Take top N correlations 
        self.correlations = self.all_correlations[:self.max_correlations]
        
        # Update overlay
        self._update_overlay()
        
        # Update count label
        shown = len(self.correlations)
        total = len(self.all_correlations)
        if shown < total:
            self.correlation_count_label.setText(f"{shown}/{total} correlations (limited)")
        else:
            self.correlation_count_label.setText(f"{total} correlation{'s' if total != 1 else ''}")
    
    def jump_to_position(self, position_pct):
        if not self.pcap_timelines:
            return
        
        scrollbar = self.scroll.horizontalScrollBar()
        max_val = scrollbar.maximum()
        target = int(max_val * position_pct)
        scrollbar.setValue(target)
    
    def _update_minimap_position(self):
        if not self.minimap or not self.minimap.isVisible():
            return
        
        scrollbar = self.scroll.horizontalScrollBar()
        if scrollbar.maximum() == 0:
            self.minimap.set_visible_range(0.0, 1.0)
            return
        
        visible_start = scrollbar.value() / scrollbar.maximum()
        visible_width = scrollbar.pageStep() / (scrollbar.maximum() + scrollbar.pageStep())
        visible_end = min(1.0, visible_start + visible_width)
        
        self.minimap.set_visible_range(visible_start, visible_end)
    
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ShiftModifier:
            scrollbar = self.scroll.horizontalScrollBar()
            delta = -event.angleDelta().y()
            scrollbar.setValue(scrollbar.value() + delta)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def showEvent(self, event):
        super().showEvent(event)
       

    def resizeEvent(self, event):
        super().resizeEvent(event)

    
    def _update_overlay(self):
        pass
    
    def _on_zoom_changed(self, value):
        self.pixels_per_second = value
        self.zoom_value_label.setText(f"{value}px/s")
        self._rebuild_timelines()
    
    def _rebuild_timelines(self):
        if not self.pcap_timelines:
            return
        
        try:
            timeline_data = {}
            for timeline in self.pcap_timelines:
                timeline_data[timeline.pcap_name] = timeline.events
            
            all_events = []
            for events in timeline_data.values():
                all_events.extend(events)
            
            if not all_events:
                return
            
            start_time = min(e.timestamp for e in all_events)
            end_time = max(e.timestamp for e in all_events)
            
            self.start_time = start_time
            self.end_time = end_time
            
            for i in reversed(range(self.timeline_layout.count())):
                widget = self.timeline_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            self.pcap_timelines = []
            
            for pcap_name, events in sorted(timeline_data.items()):
                if events:
                    timeline = PCAPTimeline(pcap_name, events, start_time, end_time, 
                                           pixels_per_second=self.pixels_per_second)
                    self.pcap_timelines.append(timeline)
                    self.timeline_layout.addWidget(timeline)
            
            self.timestamp_axis = TimestampAxis(start_time, end_time, 
                                               pixels_per_second=self.pixels_per_second)
            self.timeline_layout.addWidget(self.timestamp_axis)
            
            self.timeline_layout.addStretch()
            
            if self.minimap:
                self.minimap.start_time = start_time
                self.minimap.end_time = end_time
                self.minimap.show()
                QTimer.singleShot(50, self._update_minimap_position)
            
            QTimer.singleShot(50, self._update_overlay)
            
        except Exception as e:
            print(f"Error rebuilding timelines: {e}")
    
    def _on_filter_changed(self, label):
        self.filter_mode = 'found_in_both' if label == 'Found in Both' else 'found_multiple_times'
        self._find_correlations()
    
    def _find_correlations(self):
        try:
            import time
            t0 = time.time()
            
            self.all_correlations = []
       
            self.grouped_visible = defaultdict(lambda: defaultdict(list))

            # Group ALL events by (type, value)
            events_by_key  = defaultdict(list)
            pcaps_by_key   = defaultdict(set)
            for timeline in self.pcap_timelines:
                for event in timeline.events:
                    key = (event.event_type, event.value)
                    events_by_key[key].append(event)
                    pcaps_by_key[key].add(event.pcap_name)

            # If there is only one PCAP, skip correlation filtering entirely
            all_pcap_names = {t.pcap_name for t in self.pcap_timelines}
            if len(all_pcap_names) < 2:
                for timeline in self.pcap_timelines:
                    timeline.set_visible_events(None)
                self.correlation_count_label.setText("0 correlations (single source)")
                self.perf_label.setText(f"Found in {time.time() - t0:.2f}s")
                return

            # Determine visible set and build correlation pairs
            visible_events = set()

            if self.filter_mode == 'found_in_both':
                for key, evs in events_by_key.items():
                    if len(pcaps_by_key[key]) < 2:
                        continue
                    visible_events.update(evs)
                    for i, e1 in enumerate(evs):
                        for e2 in evs[i+1:]:
                            if e1.pcap_name != e2.pcap_name:
                                dt = abs((e1.timestamp - e2.timestamp).total_seconds())
                                self.all_correlations.append((e1, e2, dt))
            else:  # found_multiple_times
                for key, evs in events_by_key.items():
                    if len(evs) < 2:
                        continue
                    visible_events.update(evs)
                    for i, e1 in enumerate(evs):
                        for e2 in evs[i+1:]:
                            dt = abs((e1.timestamp - e2.timestamp).total_seconds())
                            self.all_correlations.append((e1, e2, dt))

            self.all_correlations.sort(key=lambda x: x[2])

            # Build grouped_visible from the filtered set
            for timeline in self.pcap_timelines:
                for event in timeline.events:
                    if event in visible_events:
                        key = (event.event_type, event.value)
                        self.grouped_visible[key][timeline.pcap_name].append(event)

            # Push visibility filter down to each timeline widget
            for timeline in self.pcap_timelines:
                tl_visible = {e for e in timeline.events if e in visible_events}
                timeline.set_visible_events(tl_visible if tl_visible else set())

            self._apply_correlation_limit()
            self.perf_label.setText(f"Found in {time.time() - t0:.2f}s")

        except Exception as e:
            print(f"Error finding correlations: {e}")
            import traceback; traceback.print_exc()
    
    def _build_correlated_entries(self, match_type, match_value):

        # Collect all occurrences of this value and attach sibling events
        correlated_events = []

        for timeline in self.pcap_timelines:
            for e in timeline.events:
                if e.event_type == match_type and e.value == match_value:

                    # Find every other event from the same packet in this timeline
                    siblings = [
                        s for s in timeline.events
                        if s.timestamp == e.timestamp and s is not e
                    ]

                    correlated_events.append({
                        'event':    e,
                        'filename': timeline.pcap_name,
                        'siblings': siblings   # other fields from the same packet
                    })

        return correlated_events

    def highlight_group(self, event_type, value):

        # Highlight all events matching type and value across every timeline and scroll to first
        first_event = None
        correlated_events = self._build_correlated_entries(event_type, value)

        for timeline in self.pcap_timelines:
            matching = [e for e in timeline.events
                        if e.event_type == event_type and e.value == value]
            if matching:
                timeline.set_highlighted_events(matching)
                if first_event is None:
                    first_event = matching[0]
            else:
                timeline.clear_highlights()

        if first_event:
            self._scroll_to_event(first_event)

        # Show or refresh the info panel with all occurrences
        if correlated_events:
            self.info_panel.display_events(correlated_events, navigate_callback=self.navigate_to_event)
            self.info_panel.show()
            self.info_panel.raise_()
            panel_width = 400
            panel_height = 500
            self.info_panel.setGeometry(self.width() - panel_width - 15, 10, panel_width, panel_height)

    def _scroll_to_event(self, event):
        scrollbar = self.scroll.horizontalScrollBar()
        viewport_width = self.scroll.viewport().width()
        
        target_x = event.x_pos - (viewport_width // 2)
        target_x = max(0, min(target_x, scrollbar.maximum()))
        
        scrollbar.setValue(target_x)
    
    def highlight_event(self, timestamp, event_type, value):
        
        # Highlight a specific event on the timeline based on timestamp, type, and value


        try:
            # Find the event that matches
            matching_events = []
            
            for timeline in self.pcap_timelines:
                for event in timeline.events:
                    # Match on type and value, with some timestamp tolerance
                    if (event.event_type == event_type and 
                        event.value == value):
                        time_diff = abs((event.timestamp - timestamp).total_seconds())
                        if time_diff < 1.0:  # Within 1 second tolerance
                            matching_events.append((event, timeline, time_diff))
            
            if not matching_events:
                # Clear all highlights if no match
                for timeline in self.pcap_timelines:
                    timeline.clear_highlights()
                return
            
            # Sort by time difference and take the closest match
            matching_events.sort(key=lambda x: x[2])
            best_event, best_timeline, _ = matching_events[0]
            
            # Clear highlights on all timelines first
            for timeline in self.pcap_timelines:
                timeline.clear_highlights()
            
            # Highlight all matching events 
            for event, timeline, _ in matching_events:
                timeline.set_highlighted_events([event])
            
            # Scroll to the best match
            self._scroll_to_event(best_event)
            
            
        except Exception as e:
            print(f"Error in highlight_event: {e}")
            import traceback
            traceback.print_exc()
    
    def navigate_to_event(self, event_data):

        # Scroll to a specific event card clicked in the info panel and focus that lane only
        event = event_data['event']
        filename = event_data['filename']
        for timeline in self.pcap_timelines:
            if timeline.pcap_name == filename:
                timeline.set_highlighted_events([event])
                self._scroll_to_event(event)
            else:
                timeline.clear_highlights()

    def on_timeline_event_clicked(self, event, pcap_name):

      
        # Store the correlated events for the info panel to display when an event card is clicked
        correlated_events = self._build_correlated_entries(event.event_type, event.value)
        
        if correlated_events:
            # Refresh the panel, display_events clears and repopulates automatically
            self.info_panel.display_events(correlated_events, navigate_callback=self.navigate_to_event)
            self.info_panel.show()
            self.info_panel.raise_()
            
            panel_width = 400
            panel_height = 500
            self.info_panel.setGeometry(self.width() - panel_width - 15, 10, panel_width, panel_height)
            
            # Highlight all instances across every timeline
            for timeline in self.pcap_timelines:
                matching = [e for e in timeline.events if e.value == event.value and e.event_type == event.event_type]
                if matching:
                    timeline.set_highlighted_events(matching)
     
    def _create_overlay(self):

        # Create the correlation line overlay and attach it to the scroll viewport
        try:
            if self.overlay:
                self.overlay.deleteLater()
            self.overlay = CorrelationOverlay(self.scroll.viewport())
            self.overlay.setGeometry(self.scroll.viewport().rect())
            self.overlay.show()
            self._update_overlay()
        except Exception as e:
            print(f"Error creating overlay: {e}")

    def load_incognito_gaps(self, gap_data, gap_table_ref=None):

        # Remove any existing gap lane before inserting a fresh one
        if self._incognito_lane:
            self._incognito_lane.deleteLater()
            self._incognito_lane = None

        if not gap_data or not self.start_time or not self.end_time:
            return

        # Build the lane using the same time range as the PCAP lanes
        self._incognito_lane = IncognitoGapTimeline(
            gap_data,
            self.start_time,
            self.end_time,
            pixels_per_second=self.pixels_per_second
        )

        if gap_table_ref:
            self._incognito_lane.set_gap_table(gap_table_ref)

        # Insert directly above the timestamp axis so it sits with the other lanes
        axis_index = self.timeline_layout.indexOf(self.timestamp_axis)
        if axis_index >= 0:
            self.timeline_layout.insertWidget(axis_index, self._incognito_lane)
        else:
            self.timeline_layout.addWidget(self._incognito_lane)
            
    def clear_timeline(self):
        
        # Clear all highlights and events from the timeline
        print("Clearing timeline...")
        
        # Clear highlights from all timelines
        for timeline in self.pcap_timelines:
            timeline.clear_highlights()
        
        # Optionally clear the overlay too
        if self.overlay:
            self.overlay.correlations = []
            self.overlay.update()

    

    def load_timeline_data(self, timeline_data):
        try:
            for i in reversed(range(self.timeline_layout.count())):
                widget = self.timeline_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            self.pcap_timelines = []
            self._incognito_lane = None # Clear any existing gap lane when loading new data

            all_events = []
            for events in timeline_data.values():
                all_events.extend(events)

            if not all_events:
                no_data_label = QLabel("No events found for selected fields")
                no_data_label.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")
                self.timeline_layout.addWidget(no_data_label)
                
                self.correlation_count_label.setText("0 correlations")
                self.minimap.hide()
                return
            
            start_time = min(e.timestamp for e in all_events)
            end_time = max(e.timestamp for e in all_events)
            
            self.start_time = start_time
            self.end_time = end_time
            
            # Update perf label with event count
            total_events = len(all_events)
            self.perf_label.setText(f"{total_events} events loaded")

            for pcap_name, events in sorted(timeline_data.items()):
                if events:
                    timeline = PCAPTimeline(pcap_name, events, start_time, end_time,
                                           pixels_per_second=self.pixels_per_second)
                    self.pcap_timelines.append(timeline)
                    self.timeline_layout.addWidget(timeline)

            self.timestamp_axis = TimestampAxis(start_time, end_time,
                                               pixels_per_second=self.pixels_per_second)
            self.timeline_layout.addWidget(self.timestamp_axis)

            self.timeline_layout.addStretch()

            if self.minimap:
                self.minimap.start_time = start_time
                self.minimap.end_time = end_time
                self.minimap.show()
                QTimer.singleShot(100, self._update_minimap_position)

            QTimer.singleShot(150, self._find_correlations) 
            
        except Exception as e:
            print(f"Error loading timeline data: {e}")


# Clickable event card, clicking navigates the timeline to that specific event
class ClickableEventCard(QFrame):
    def __init__(self, event_data, navigate_callback, parent=None):
        super().__init__(parent)
        self._event_data = event_data
        self._navigate_callback = navigate_callback
        self.setCursor(Qt.PointingHandCursor)
        self._base_style = f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 5px;
            }}
        """
        self._hover_style = f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
                border-radius: 4px;
                padding: 5px;
            }}
        """
        self.setStyleSheet(self._base_style)

    def enterEvent(self, event):
        self.setStyleSheet(self._hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self._base_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._navigate_callback:
            self._navigate_callback(self._event_data)
        super().mousePressEvent(event)


# Info panel overlay showing correlated event details
class TimelineInfoPanel(QFrame):
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 2px solid {THEME['accent']};
                border-radius: 6px;
            }}
        """)
        
        # Enable drop shadow effect
        self.setAutoFillBackground(True)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)  # Tighter margins
        layout.setSpacing(6)  # Tighter spacing
        
        # Header with close button
        header = QHBoxLayout()
        title = QLabel("Correlated Events")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-weight: bold;
            font-size: 11px;
        """)
        header.addWidget(title)
        
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.clicked.connect(self.hide)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {THEME['text_secondary']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {THEME['accent']};
                background-color: {THEME['surface']};
                border-radius: 9px;
            }}
        """)
        header.addWidget(close_btn)
        layout.addLayout(header)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {THEME['border']};")
        layout.addWidget(separator)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(6)  # Tighter spacing
        scroll.setWidget(self.content_widget)
        
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        self._navigate_callback = None
    
    def display_events(self, events, navigate_callback=None):

        # Populate the panel, clears previous content and rebuilds from the new event list
        self._navigate_callback = navigate_callback

        # Clear previous content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not events:
            return
        
        # Summary
        summary = QLabel(f"{len(events)} occurrence(s) — click an event to focus it")
        summary.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 9px;
            padding: 2px 0px;
        """)
        self.content_layout.addWidget(summary)
        
        # Show each event, compact cards
        for i, event_data in enumerate(events):
            event_card = self._create_event_card(event_data, i + 1)
            self.content_layout.addWidget(event_card)
        
        self.content_layout.addStretch()
    
    def _create_event_card(self, event_data, number):

        event    = event_data['event']
        filename = event_data['filename']
        siblings = event_data.get('siblings', [])

        card = ClickableEventCard(event_data, self._navigate_callback)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(2)
        card_layout.setContentsMargins(4, 4, 4, 4)

        header_row = QHBoxLayout()
        number_label = QLabel(f"#{number}")
        number_label.setStyleSheet(f"color: {THEME['accent']}; font-weight: bold; font-size: 9px;")
        header_row.addWidget(number_label)
        header_row.addStretch()
        focus_hint = QLabel("focus")
        focus_hint.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 8px;")
        header_row.addWidget(focus_hint)
        card_layout.addLayout(header_row)

        self._add_detail(card_layout, "File:", filename)
        self._add_detail(card_layout, "Time:", event.timestamp.strftime('%H:%M:%S.%f')[:-3])
        self._add_detail(card_layout, "Protocol:", event.protocol or "N/A")
        self._add_detail(card_layout, event.event_type.upper() + ":", event.value)

        # Show sibling fields from the same packet
        for sibling in siblings:
            self._add_detail(card_layout, sibling.event_type.upper() + ":", sibling.value)

        return card
    
    def _add_detail(self, layout, label, value):

        # Add a label/value row to the card layout, truncates long values
        if len(str(value)) > 35:
            display_value = str(value)[:32] + "..."
        else:
            display_value = str(value)
        
        row = QLabel(f"<span style='color: {THEME['text_secondary']};'>{label}</span> <b>{display_value}</b>")
        row.setWordWrap(True)
        row.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 9px;
        """)
        layout.addWidget(row)

# Incognito gap lane showing incognito gaps
class IncognitoGapTimeline(QWidget):

    def __init__(self, gap_data, start_time, end_time, height=120, pixels_per_second=50):
        super().__init__()
        self.gap_data          = gap_data
        self.start_time        = start_time
        self.end_time          = end_time
        self.timeline_height   = height
        self.pixels_per_second = pixels_per_second
        self.hovered_gap       = None
        self.highlighted_domain = None
        self._dot_positions    = []  
        self._sessions         = []  
        self._gap_table_ref    = None

        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.setMouseTracking(True)

        total_seconds  = (end_time - start_time).total_seconds()
        required_width = int(total_seconds * pixels_per_second) + 200
        self.setMinimumWidth(required_width)

        self._compute_dot_positions()
        self._compute_sessions()

    def set_gap_table(self, table_ref):
        # Wire up to IncognitoGapWidget so clicking a dot selects the matching table row
        self._gap_table_ref = table_ref

    def _compute_dot_positions(self):
        # Calculate x position for each gap from its first_seen timestamp
        self._dot_positions = []
        timeline_y = self.timeline_height // 2

        for gap in self.gap_data:
            elapsed = (gap['first_seen'] - self.start_time).total_seconds()
            x = 100 + int(elapsed * self.pixels_per_second)
            self._dot_positions.append((x, timeline_y, gap))

    def _compute_sessions(self):
        # Group gaps within 5 minutes of each other into inferred session spans
        SESSION_GAP_SECONDS = 300
        self._sessions = []

        if not self._dot_positions:
            return

        sorted_dots = sorted(self._dot_positions, key=lambda d: d[0])
        session_x0  = sorted_dots[0][0]
        session_x1  = sorted_dots[0][0]
        scores      = [sorted_dots[0][2]['suspiciousness']]

        for i in range(1, len(sorted_dots)):
            x, y, gap   = sorted_dots[i]
            prev_gap    = sorted_dots[i - 1][2]
            gap_secs    = (gap['first_seen'] - prev_gap['first_seen']).total_seconds()

            if gap_secs <= SESSION_GAP_SECONDS:
                session_x1 = x
                scores.append(gap['suspiciousness'])
            else:
                if session_x1 > session_x0:
                    self._sessions.append((session_x0, session_x1, max(scores)))
                session_x0 = x
                session_x1 = x
                scores     = [gap['suspiciousness']]

        if session_x1 > session_x0:
            self._sessions.append((session_x0, session_x1, max(scores)))

    def _score_color(self, score):
        # Map suspiciousness score to colour matching the gap table
        if score >= 60:
            return "#FF4444"
        elif score >= 30:
            return "#FFA500"
        else:
            return "#888888"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))

        # Lane label, same position and style as PCAPTimeline
        painter.setPen(QColor(THEME['text_primary']))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(10, 10, 85, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, "Incognito")

        timeline_y    = self.timeline_height // 2
        viewport_rect = self.visibleRegion().boundingRect()

        # Draw inferred session spans as semi-transparent bands behind the dots
        for x_start, x_end, max_score in self._sessions:
            span_col = QColor(self._score_color(max_score))
            span_col.setAlpha(25)
            painter.fillRect(x_start - 10, timeline_y - 18,
                             (x_end - x_start) + 20, 36, span_col)

            border_col = QColor(self._score_color(max_score))
            border_col.setAlpha(70)
            painter.setPen(QPen(border_col, 1, Qt.DashLine))
            painter.drawRect(x_start - 10, timeline_y - 18,
                             (x_end - x_start) + 20, 36)

            # Label the span
            font.setPointSize(7)
            font.setBold(False)
            font.setItalic(True)
            painter.setFont(font)
            painter.setPen(QColor(self._score_color(max_score)))
            painter.drawText(x_start - 8, timeline_y - 22, "possible session")

        # Timeline bar, identical to PCAPTimeline
        painter.setPen(QPen(QColor(THEME['border']), 2))
        painter.drawLine(100, timeline_y, self.width() - 20, timeline_y)

        # Gap dots
        for x, y, gap in self._dot_positions:
            # Cull offscreen dots
            if x < viewport_rect.left() - 50 or x > viewport_rect.right() + 50:
                continue

            color          = self._score_color(gap['suspiciousness'])
            is_hovered     = gap == self.hovered_gap
            is_highlighted = gap['domain'] == self.highlighted_domain

            if is_highlighted:
                painter.setBrush(QBrush(QColor("#ffdd00")))
                painter.setPen(QPen(QColor("#ffdd00").darker(130), 2))
                painter.drawEllipse(x - 7, y - 7, 14, 14)
            elif is_hovered:
                painter.setBrush(QBrush(QColor(color).lighter(140)))
                painter.setPen(QPen(QColor(color).lighter(160), 2))
                painter.drawEllipse(x - 6, y - 6, 12, 12)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(120), 1))
                painter.drawEllipse(x - 4, y - 4, 8, 8)

        # Tooltip drawn last so it sits on top of everything
        if self.hovered_gap:
            self._draw_tooltip(painter, self.hovered_gap)

    def _draw_tooltip(self, painter, gap):
        # Draw tooltip showing domain, score, category and time
        lines = [
            gap['domain'],
            f"Score: {gap['suspiciousness']}  |  {gap['category']}",
            f"First seen: {gap['first_seen'].strftime('%H:%M:%S')}",
            f"Occurrences: {gap['count']}"
        ]

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics   = painter.fontMetrics()
        max_width = max(metrics.horizontalAdvance(l) for l in lines)
        line_h    = metrics.height()
        tip_w     = max_width + 20
        tip_h     = line_h * len(lines) + 10

        dot_x = next((x for x, y, g in self._dot_positions if g == gap), self.width() // 2)
        tip_x = max(10, min(dot_x - tip_w // 2, self.width() - tip_w - 10))
        tip_y = 5

        painter.setBrush(QBrush(QColor(THEME['surface_elevated'])))
        painter.setPen(QPen(QColor(self._score_color(gap['suspiciousness'])), 2))
        painter.drawRoundedRect(tip_x, tip_y, tip_w, tip_h, 4, 4)

        painter.setPen(QColor(THEME['text_primary']))
        y_off = tip_y + line_h
        for line in lines:
            painter.drawText(QRect(tip_x + 10, y_off - line_h + 5, tip_w - 20, line_h),
                            Qt.AlignLeft | Qt.AlignVCenter, line)
            y_off += line_h

    def mouseMoveEvent(self, event):
        mx, my       = event.x(), event.y()
        prev_hovered = self.hovered_gap
        self.hovered_gap = None

        for x, y, gap in self._dot_positions:
            if abs(mx - x) <= 8 and abs(my - y) <= 8:
                self.hovered_gap = gap
                self.setCursor(Qt.PointingHandCursor)
                break
        else:
            self.setCursor(Qt.ArrowCursor)

        if self.hovered_gap != prev_hovered:
            self.update()

    def leaveEvent(self, event):
        self.hovered_gap = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self.hovered_gap:
            return

        # Select matching row in the gap table
        if self._gap_table_ref and hasattr(self._gap_table_ref, 'gap_table'):
            table = self._gap_table_ref.gap_table
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and item.text() == self.hovered_gap['domain']:
                    table.selectRow(row)
                    table.scrollToItem(item)
                    break

        event.accept()