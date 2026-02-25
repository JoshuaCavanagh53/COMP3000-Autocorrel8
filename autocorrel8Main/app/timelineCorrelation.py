from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QScrollArea, QComboBox, QSlider, QTableWidget, QHeaderView, 
    QTableWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QWheelEvent
from datetime import timedelta
from collections import defaultdict

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


# Event cluster for grouping nearby events
class EventCluster:
    def __init__(self, events, x_start, x_end):
        self.events = events
        self.x_start = x_start
        self.x_end = x_end
        self.x_center = (x_start + x_end) // 2
        self.count = len(events)
        self.expanded = False  # Track expansion state
    
    def toggle_expansion(self):
        
        # Toggle between expanded and collapsed state
        self.expanded = not self.expanded
        return self.expanded
    
    def contains_point(self, x, y, timeline_y, threshold=10):
        
        # Check if a point is within the cluster bounds
        if not self.expanded:
            # Collapsed cluster check if click is within the bar
            return (self.x_start - threshold <= x <= self.x_end + threshold and
                    timeline_y - 15 <= y <= timeline_y + 15)
        else:
            # Expanded cluster larger vertical area
            return (self.x_start - threshold <= x <= self.x_end + threshold and
                    timeline_y - 40 <= y <= timeline_y + 40)


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
        end_str = self.end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        painter.drawText(QRect(10, 0, 150, bar_y - 10), 
                        Qt.AlignLeft | Qt.AlignBottom, start_str)
        painter.drawText(QRect(self.width() - 160, 0, 150, bar_y - 10), 
                        Qt.AlignRight | Qt.AlignBottom, end_str)
    
    # Check if the user is dragging the timeline scroller
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_x = event.x()
            self._jump_to_position(event.x())
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self._jump_to_position(event.x())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    # Move timeline view to the scrolled location 
    def _jump_to_position(self, x):
        bar_width = self.width() - 20
        clicked_pct = (x - 10) / bar_width
        clicked_pct = max(0.0, min(1.0, clicked_pct))
        
        if hasattr(self.parent(), 'jump_to_position'):
            self.parent().jump_to_position(clicked_pct)


# Optimized timeline with clustering
class PCAPTimeline(QWidget):
    def __init__(self, pcap_name, events, start_time, end_time, height=120, pixels_per_second=50):
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
        
        mouse_x = event.x()
        mouse_y = event.y()
        timeline_y = self.timeline_height // 2
        
        # Check invidual events first
        for event_obj in self.events:
            if self.visible_event_set is not None and event_obj not in self.visible_event_set:
                continue
            distance_x = abs(mouse_x - event_obj.x_pos)
            distance_y = abs(mouse_y - timeline_y)
            
            if distance_x < 15 and distance_y < 25:  # Click area
                print(f"✓ CLICKED EVENT: {event_obj.value}")
                
                # Notify parent
                parent = self.parent()
                while parent and not hasattr(parent, 'on_timeline_event_clicked'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'on_timeline_event_clicked'):
                    parent.on_timeline_event_clicked(event_obj, self.pcap_name)
                
                event.accept()
                return
        
        # Theb check if click is on a cluster 
        for cluster in self.clusters:
            if cluster.contains_point(mouse_x, mouse_y, timeline_y):
                # Toggle cluster expansion
                was_expanded = cluster.toggle_expansion()
                
                print(f"\n=== Cluster Click ===")
                print(f"Cluster with {cluster.count} events")
                print(f"State: {'Expanded' if cluster.expanded else 'Collapsed'}")
                print(f"=== End Click ===\n")
                
                # Redraw to show expansion
                self.update()
                event.accept()
                return
        
        # If no event or cluster was clicked, let the event propagate
        super().mousePressEvent(event)

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
        
        # Draw clusters first
        for cluster in self.clusters:
            # Cull offscreen clusters
            if cluster.x_end < viewport_rect.left() - 50 or cluster.x_start > viewport_rect.right() + 50:
                continue
            
            is_hovered = cluster == self.hovered_cluster
            self._draw_cluster(painter, cluster, timeline_y, is_hovered)
        
        # Draw individual events 
        clustered_events = set()
        expanded_cluster_events = set()
        
        for cluster in self.clusters:
            if cluster.expanded:
                # Events in expanded clusters are drawn by _draw_expanded_cluster
                expanded_cluster_events.update(cluster.events)
            else:
                # Events in collapsed clusters shouldn't be drawn individually
                clustered_events.update(cluster.events)
        
        for ev in self.events:
            # Remove offscreen events
            if ev.x_pos < viewport_rect.left() - 50 or ev.x_pos > viewport_rect.right() + 50:
                continue
            
            # Skip events hidden by the current visibility filter
            if self.visible_event_set is not None and ev not in self.visible_event_set:
                continue
            
            # Skip events in expanded clusters 
            if ev in expanded_cluster_events:
                continue
            
            # Skip events that are in collapsed clusters unless highlighted
            if ev in clustered_events and ev not in self.highlighted_events:
                continue
            
            is_highlighted = ev in self.highlighted_events
            is_hovered = ev == self.hovered_event
            
            if is_highlighted:
                self._draw_highlighted_event(painter, ev, timeline_y)
            elif is_hovered:
                self._draw_hovered_event(painter, ev, timeline_y)
            else:
                color = self._get_event_color(ev.event_type)
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color), 1))
                painter.drawEllipse(ev.x_pos - 4, timeline_y - 4, 8, 8)
        
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
        
        # Draw an expanded cluster showing individual events
        # Draw background box
        width = max(80, cluster.x_end - cluster.x_start + 40)
        height = 70
        
        box_color = QColor(THEME['surface_elevated']).lighter(105)
        painter.setBrush(QBrush(box_color))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRoundedRect(cluster.x_start - 20, timeline_y - height//2, 
                               width, height, 6, 6)
        
        # Draw Click to collapse hint at top
        painter.setPen(QColor(THEME['text_secondary']))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(QRect(cluster.x_start - 15, timeline_y - height//2 + 3, width - 10, 12),
                        Qt.AlignCenter, f"Click to collapse ({cluster.count} events)")
        
        # Draw individual events in a grid layout
        events_per_row = min(10, cluster.count)
        rows_needed = (cluster.count + events_per_row - 1) // events_per_row
        
        event_spacing_x = (width - 40) / max(1, events_per_row - 1) if events_per_row > 1 else 0
        event_spacing_y = 20 if rows_needed > 1 else 0
        
        start_y = timeline_y - height//2 + 25
        
        for idx, event in enumerate(cluster.events):
            row = idx // events_per_row
            col = idx % events_per_row
            
            if events_per_row == 1:
                event_x = cluster.x_center
            else:
                event_x = cluster.x_start - 10 + int(col * event_spacing_x)
            
            event_y = start_y + row * event_spacing_y
            
            # Draw the event dot
            color = self._get_event_color(event.event_type)
            
            # Check if this specific event is hovered
            mouse_pos = self.mapFromGlobal(self.cursor().pos())
            is_event_hovered = (abs(mouse_pos.x() - event_x) < 8 and 
                              abs(mouse_pos.y() - event_y) < 8)
            
            if is_event_hovered:
                painter.setBrush(QBrush(QColor(color).lighter(130)))
                painter.setPen(QPen(QColor(color).lighter(150), 2))
                painter.drawEllipse(event_x - 6, event_y - 6, 12, 12)
                
                # Draw tooltip for hovered event in cluster
                self._draw_tooltip(painter, event, event_x, event_y - 30)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(120), 1))
                painter.drawEllipse(event_x - 4, event_y - 4, 8, 8)
    
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
            'protocol': THEME.get('event_protocol', THEME['accent']),
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
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #3a8eef;
            }}
        """)
        refresh_btn.clicked.connect(self._find_correlations)
        header_layout.addWidget(refresh_btn)
        
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
        if not self.overlay:
            self._create_overlay()
    
    def _create_overlay(self):
        # DISABLED: Correlation overlay causes performance issues
        # The overlay draws lines between correlated events but lags with many correlations
        return
        
        # Old code commented out:
        # try:
        #     if self.overlay:
        #         self.overlay.deleteLater()
        #     
        #     self.overlay = CorrelationOverlay(self.scroll.viewport())
        #     self.overlay.setGeometry(self.scroll.viewport().rect())
        #     self.overlay.show()
        #     self.overlay.raise_()
        #     
        #     if self.scroll.horizontalScrollBar():
        #         self.scroll.horizontalScrollBar().valueChanged.connect(self._update_overlay)
        #     if self.scroll.verticalScrollBar():
        #         self.scroll.verticalScrollBar().valueChanged.connect(self._update_overlay)
        #         
        # except Exception as e:
        #     print(f"Error creating overlay: {e}")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay:
            try:
                self.overlay.setGeometry(self.scroll.viewport().rect())
                self._update_overlay()
            except Exception as e:
                print(f"Error in resizeEvent: {e}")
    
    def _update_overlay(self):
        if self.overlay:
            try:
                self.overlay.setGeometry(self.scroll.viewport().rect())
                self.overlay.set_data(self.correlations, self.pcap_timelines, self.scroll)
            except Exception as e:
                print(f"Error updating overlay: {e}")
    
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
            # grouped_visible: (type, value) → {pcap_name: [events]}  — drives the table
            self.grouped_visible = defaultdict(lambda: defaultdict(list))

            # Group ALL events by (type, value)
            events_by_key  = defaultdict(list)
            pcaps_by_key   = defaultdict(set)
            for timeline in self.pcap_timelines:
                for event in timeline.events:
                    key = (event.event_type, event.value)
                    events_by_key[key].append(event)
                    pcaps_by_key[key].add(event.pcap_name)

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
    
    def highlight_group(self, event_type, value):

        # Highlight all events matching type and value across every timeline and scroll to first
        first_event = None
        correlated_events = []

        for timeline in self.pcap_timelines:
            matching = [e for e in timeline.events
                        if e.event_type == event_type and e.value == value]
            if matching:
                timeline.set_highlighted_events(matching)
                if first_event is None:
                    first_event = matching[0]
                for e in matching:
                    correlated_events.append({'event': e, 'filename': timeline.pcap_name})
            else:
                timeline.clear_highlights()

        if first_event:
            self._scroll_to_event(first_event)

        # Show or refresh the info panel with all occurrences
        if correlated_events:
            self.info_panel.display_events(correlated_events, navigate_callback=self.navigate_to_event)
            self.info_panel.show()
            self.info_panel.raise_()
            panel_width = 280
            panel_height = min(350, self.height() - 80)
            self.info_panel.setGeometry(self.width() - panel_width - 15, 70, panel_width, panel_height)

    def _scroll_to_event(self, event):
        scrollbar = self.scroll.horizontalScrollBar()
        viewport_width = self.scroll.viewport().width()
        
        target_x = event.x_pos - (viewport_width // 2)
        target_x = max(0, min(target_x, scrollbar.maximum()))
        
        scrollbar.setValue(target_x)
    
    def highlight_event(self, timestamp, event_type, value):
        
        # Highlight a specific event on the timeline based on timestamp, type, and value
        print(f"\n=== Timeline highlight_event called ===")
        print(f"Looking for: {event_type} - {value} at {timestamp}")
        
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
                            print(f"  Found match in {timeline.pcap_name}: time_diff={time_diff:.3f}s")
            
            if not matching_events:
                print("  No matching events found!")
                # Clear all highlights if no match
                for timeline in self.pcap_timelines:
                    timeline.clear_highlights()
                return
            
            # Sort by time difference and take the closest match
            matching_events.sort(key=lambda x: x[2])
            best_event, best_timeline, _ = matching_events[0]
            
            print(f"  Highlighting event in {best_timeline.pcap_name}")
            
            # Clear highlights on all timelines first
            for timeline in self.pcap_timelines:
                timeline.clear_highlights()
            
            # Highlight all matching events 
            for event, timeline, _ in matching_events:
                timeline.set_highlighted_events([event])
            
            # Scroll to the best match
            self._scroll_to_event(best_event)
            
            print("=== End highlight_event ===\n")
            
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

        # Show or refresh the info panel when a timeline node is clicked
        print(f"\n=== Timeline Event Clicked ===")
        print(f"Event: {event.value} ({event.event_type})")
        print(f"PCAP: {pcap_name}")
        
        # Collect all events with the same type and value across every PCAP
        correlated_events = []
        for timeline in self.pcap_timelines:
            for e in timeline.events:
                if e.value == event.value and e.event_type == event.event_type:
                    correlated_events.append({
                        'event': e,
                        'filename': timeline.pcap_name
                    })
        
        print(f"Found {len(correlated_events)} correlated events")
        
        if correlated_events:
            # Refresh the panel, display_events clears and repopulates automatically
            self.info_panel.display_events(correlated_events, navigate_callback=self.navigate_to_event)
            self.info_panel.show()
            self.info_panel.raise_()
            
            panel_width = 280
            panel_height = min(350, self.height() - 80)
            self.info_panel.setGeometry(self.width() - panel_width - 15, 70, panel_width, panel_height)
            
            # Highlight all instances across every timeline
            for timeline in self.pcap_timelines:
                matching = [e for e in timeline.events if e.value == event.value and e.event_type == event.event_type]
                if matching:
                    timeline.set_highlighted_events(matching)
        
        print("=== End Event Click ===\n")
    
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

            if not self.overlay:
                QTimer.singleShot(100, self._create_overlay)

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

        # Build a single clickable card showing the event details
        event = event_data['event']
        filename = event_data['filename']
        
        card = ClickableEventCard(event_data, self._navigate_callback)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(2)
        card_layout.setContentsMargins(4, 4, 4, 4)
        
        # Header row: number + focus hint
        header_row = QHBoxLayout()
        number_label = QLabel(f"#{number}")
        number_label.setStyleSheet(f"color: {THEME['accent']}; font-weight: bold; font-size: 9px;")
        header_row.addWidget(number_label)
        header_row.addStretch()
        focus_hint = QLabel("→ focus")
        focus_hint.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 8px;")
        header_row.addWidget(focus_hint)
        card_layout.addLayout(header_row)
        
        self._add_detail(card_layout, "File:", filename)
        self._add_detail(card_layout, "Type:", event.event_type.upper())
        self._add_detail(card_layout, "Value:", event.value)
        self._add_detail(card_layout, "Time:", event.timestamp.strftime('%H:%M:%S'))
        
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