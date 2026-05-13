from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QScrollArea
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
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
        self.expanded = not self.expanded
        if not self.expanded:
            # Clear cached geometry 
            self._expanded_rect = None
            self._dot_positions = []
        return self.expanded

    def contains_point(self, x, y, timeline_y, threshold=10):
        if not self.expanded:
            return (self.x_start - threshold <= x <= self.x_end + threshold and
                    timeline_y - 15 <= y <= timeline_y + 15)
        if self._expanded_rect:
            rx, ry, rw, rh = self._expanded_rect
            return rx <= x <= rx + rw and ry <= y <= ry + rh
        return (self.x_start - threshold <= x <= self.x_end + threshold and
                timeline_y - 60 <= y <= timeline_y + 60)


# Minimap widget showing full timeline overview
class TimelineMinimap(QWidget):
    def __init__(self, start_time, end_time, height=40):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.visible_start = 0.0
        self.visible_end = 1.0
        self.setFixedHeight(height)
        self.setMinimumWidth(400)
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
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        bar_y = self.height() // 2
        painter.setPen(QPen(QColor(THEME['border']), 2))
        painter.drawLine(10, bar_y, self.width() - 10, bar_y)

        bar_w = self.width() - 20
        vis_x1 = 10 + int(bar_w * self.visible_start)
        vis_x2 = 10 + int(bar_w * self.visible_end)

        painter.fillRect(vis_x1, bar_y - 8, vis_x2 - vis_x1, 16,
                         QColor(THEME['accent']).lighter(150))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRect(vis_x1, bar_y - 8, vis_x2 - vis_x1, 16)

        painter.setPen(QColor(THEME['text_secondary']))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(QRect(10, 0, 150, bar_y - 10),
                         Qt.AlignLeft | Qt.AlignBottom,
                         self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        painter.drawText(QRect(self.width() - 160, 0, 150, bar_y - 10),
                         Qt.AlignRight | Qt.AlignBottom,
                         self.end_time.strftime("%Y-%m-%d %H:%M:%S"))


# Optimized timeline with clustering
class PCAPTimeline(QWidget):
    def __init__(self, pcap_name, events, start_time, end_time,
                 height=100, pixels_per_second=10, lane_index=0):
        super().__init__()
        self.pcap_name = pcap_name
        self.events = events
        self.start_time = start_time
        self.end_time = end_time
        self.timeline_height = height
        self.lane_index = lane_index  
        self.highlighted_events = []
        self.pixels_per_second = pixels_per_second
        self.hovered_event = None
        self.hovered_cluster = None
        self.clusters = []
        self.use_clustering = True
        self.cluster_threshold = 15 
        self.visible_event_set = None 

        self.setMinimumHeight(height)
        self.setMouseTracking(True)

        total_duration = (self.end_time - self.start_time).total_seconds()
        self.setMinimumWidth(int(total_duration * self.pixels_per_second) + 200)

        self._calculate_event_positions()
        self._create_clusters()

    def _calculate_event_positions(self):
        total = (self.end_time - self.start_time).total_seconds()
        if not self.events or total == 0:
            return
        for ev in self.events:
            elapsed = (ev.timestamp - self.start_time).total_seconds()
            ev.x_pos = 100 + int(elapsed * self.pixels_per_second)

    def _create_clusters(self, source_events=None):
        events = source_events if source_events is not None else self.events
        if not events or not self.use_clustering:
            self.clusters = []
            return
        sorted_ev = sorted(events, key=lambda e: e.x_pos)
        self.clusters = []
        cur = [sorted_ev[0]]
        s = sorted_ev[0].x_pos
        for ev in sorted_ev[1:]:
            if ev.x_pos - cur[-1].x_pos <= self.cluster_threshold:
                cur.append(ev)
            else:
                if len(cur) > 1:
                    self.clusters.append(EventCluster(cur, s, cur[-1].x_pos))
                cur = [ev]
                s = ev.x_pos
        if len(cur) > 1:
            self.clusters.append(EventCluster(cur, s, cur[-1].x_pos))

    def set_visible_events(self, event_set):

        # Filter which events are drawn
        self.visible_event_set = event_set
        if event_set is None:
            self._create_clusters()
        else:
            self._create_clusters([e for e in self.events if e in event_set])
        self.update()

    def clear_visible_filter(self):
        self.set_visible_events(None)

    def set_highlighted_events(self, events):
        self.highlighted_events = events or []
        self.update()

    def clear_highlights(self):
        self.highlighted_events = []
        self.update()

    # Mouse events

    def mouseMoveEvent(self, event):
        mx, my = event.x(), event.y()
        tl_y = self.height() // 2
        self.hovered_cluster = None
        over_cluster = False

        for c in self.clusters:
            if c.contains_point(mx, my, tl_y):
                self.hovered_cluster = c
                self.hovered_event = None
                over_cluster = True
                self.update()
                break

        if over_cluster:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.hovered_event = None
            for ev in self.events:
                if self.visible_event_set is not None and ev not in self.visible_event_set:
                    continue
                if ev in self.highlighted_events or any(ev in c.events for c in self.clusters):
                    if ev in self.highlighted_events and abs(ev.x_pos - mx) < 10:
                        self.hovered_event = ev
                        break
                elif abs(ev.x_pos - mx) < 10:
                    self.hovered_event = ev
                    break
            self.update()

    def leaveEvent(self, event):
        self.hovered_event = None
        self.hovered_cluster = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        mx, my = event.x(), event.y()
        tl_y = self.height() // 2

        clustered = set()
        for c in self.clusters:
            if not c.expanded:
                clustered.update(c.events)

        for ev in self.events:
            if ev in clustered:
                continue
            if self.visible_event_set is not None and ev not in self.visible_event_set:
                continue
            if abs(mx - ev.x_pos) < 15 and abs(my - tl_y) < 25:
                parent = self.parent()
                while parent and not hasattr(parent, 'on_timeline_event_clicked'):
                    parent = parent.parent()
                if parent:
                    parent.on_timeline_event_clicked(ev, self.pcap_name)
                event.accept()
                return

        # Check dots inside expanded clusters using their painted positions
        DOT_R = 8
        for c in self.clusters:
            if not c.expanded:
                continue
            for cx, cy, ev in c._dot_positions:
                if abs(mx - cx) <= DOT_R and abs(my - cy) <= DOT_R:
                    parent = self.parent()
                    while parent and not hasattr(parent, 'on_timeline_event_clicked'):
                        parent = parent.parent()
                    if parent:
                        parent.on_timeline_event_clicked(ev, self.pcap_name)
                    event.accept()
                    return

        for c in self.clusters:
            if c.contains_point(mx, my, tl_y):
                c.toggle_expansion()
                self.update()
                event.accept()
                return

        super().mousePressEvent(event)

    # Painting
    def _compute_expanded_rect(self, cluster):
        DOT_R = 5; COL_SPC = 22; ROW_SPC = 22
        H_PAD = 14; V_PAD_TOP = 24; V_PAD_BOT = 10; MAX_COLS = 10
        n = cluster.count
        cols = min(MAX_COLS, n)
        rows = (n + cols - 1) // cols
        bw = (cols - 1) * COL_SPC + H_PAD * 2 + DOT_R * 2 if cols > 1 else H_PAD * 2 + DOT_R * 2
        bh = (rows - 1) * ROW_SPC + V_PAD_TOP + V_PAD_BOT + DOT_R * 2 if rows > 1 else V_PAD_TOP + V_PAD_BOT + DOT_R * 2
        tl_y = self.height() // 2
        bx = max(105, cluster.x_center - bw // 2)
        by = tl_y - bh // 2
        return (bx, by, bw, bh)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Zebra stripe differentiation between stacked lanes
        bg = QColor(THEME['timeline_bg'])
        if self.lane_index % 2 == 1:
            bg = bg.darker(108)
        painter.fillRect(self.rect(), bg)

        # Sidebar label 
        painter.fillRect(0, 0, 100, self.height(), QColor(THEME['surface']))
        painter.setPen(QPen(QColor(THEME['border']), 1))
        painter.drawLine(100, 0, 100, self.height())

        # PCAP name label
        painter.setPen(QColor(THEME['text_primary']))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(10, 0, 85, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.pcap_name)

        tl_y = self.height() // 2

        track = QColor(THEME['accent']); track.setAlpha(90)
        painter.setPen(QPen(track, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(105, tl_y, self.width() - 20, tl_y)

        vp = self.visibleRegion().boundingRect()

        # Pre-compute expanded cluster rects 
        expanded_rects = []
        for c in self.clusters:
            if c.expanded:
                rx, ry, rw, rh = self._compute_expanded_rect(c)
                expanded_rects.append(QRect(rx, ry, rw, rh))

        def behind(x):
            return any(r.left() <= x <= r.right() for r in expanded_rects)

        for c in self.clusters:
            if c.expanded:
                continue
            if c.x_end < vp.left() - 50 or c.x_start > vp.right() + 50:
                continue
            if behind(c.x_center):
                continue
            self._draw_cluster(painter, c, tl_y, c == self.hovered_cluster)

        clustered_ev = set()
        expanded_ev = set()
        for c in self.clusters:
            (expanded_ev if c.expanded else clustered_ev).update(c.events)

        for ev in self.events:
            if ev.x_pos < vp.left() - 50 or ev.x_pos > vp.right() + 50:
                continue
            if self.visible_event_set is not None and ev not in self.visible_event_set:
                continue
            if ev in expanded_ev:
                continue
            if ev in clustered_ev and ev not in self.highlighted_events:
                continue
            if behind(ev.x_pos):
                continue
            if ev in self.highlighted_events:
                self._draw_highlighted_event(painter, ev, tl_y)
            elif ev == self.hovered_event:
                self._draw_hovered_event(painter, ev, tl_y)
            else:
                # Base dot
                c = QColor(self._get_event_color(ev.event_type))
                painter.setBrush(QBrush(c))
                painter.setPen(QPen(c.darker(150), 1))
                painter.drawEllipse(ev.x_pos - 5, tl_y - 5, 10, 10)

        # Expanded clusters drawn last so they sit on top
        for c in self.clusters:
            if not c.expanded:
                continue
            if c.x_end < vp.left() - 50 or c.x_start > vp.right() + 50:
                continue
            self._draw_cluster(painter, c, tl_y, c == self.hovered_cluster)

        if self.hovered_event:
            self._draw_tooltip(painter, self.hovered_event)
        elif self.hovered_cluster and not self.hovered_cluster.expanded:
            self._draw_cluster_tooltip(painter, self.hovered_cluster)

    def _draw_cluster(self, painter, cluster, tl_y, is_hovered):
        if not cluster.expanded:
            w = max(8, cluster.x_end - cluster.x_start)
            if is_hovered:
                color = QColor(THEME['accent']).lighter(130)
                border = QColor(THEME['accent']); bw = 2
            else:
                color = QColor(THEME['text_secondary']).darker(140)
                border = QColor(THEME['accent']).darker(120); bw = 1
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(border, bw))
            painter.drawRoundedRect(cluster.x_start - 2, tl_y - 9, w + 4, 18, 8, 8)
            painter.setPen(QColor(THEME['text_primary']))
            font = QFont()
            font.setPointSize(8 if cluster.count < 100 else 7)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRect(cluster.x_start - 2, tl_y - 9, w + 4, 18),
                             Qt.AlignCenter, str(cluster.count))
        else:
            self._draw_expanded_cluster(painter, cluster, tl_y, is_hovered)

    def _draw_expanded_cluster(self, painter, cluster, tl_y, is_hovered):
        DOT_R = 5; COL_SPC = 22; ROW_SPC = 22
        H_PAD = 14; V_PAD_TOP = 24; V_PAD_BOT = 10; MAX_COLS = 10
        n = cluster.count
        cols = min(MAX_COLS, n)
        rows = (n + cols - 1) // cols
        bw = (cols - 1) * COL_SPC + H_PAD * 2 + DOT_R * 2 if cols > 1 else H_PAD * 2 + DOT_R * 2
        bh = (rows - 1) * ROW_SPC + V_PAD_TOP + V_PAD_BOT + DOT_R * 2 if rows > 1 else V_PAD_TOP + V_PAD_BOT + DOT_R * 2
        bx = max(105, cluster.x_center - bw // 2)
        by = tl_y - bh // 2
        cluster._expanded_rect = (bx, by, bw, bh)

        painter.setBrush(QBrush(QColor(THEME['surface_elevated']).lighter(105)))
        painter.setPen(QPen(QColor(THEME['accent']), 2))
        painter.drawRoundedRect(bx, by, bw, bh, 6, 6)

        header = QRect(bx, by, bw, V_PAD_TOP - 2)
        painter.fillRect(header, QColor(THEME['accent']).darker(130))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(THEME['text_primary']))
        painter.drawText(header, Qt.AlignCenter, f"▲ Click to collapse  ({n} events)")

        ox = bx + H_PAD + DOT_R
        oy = by + V_PAD_TOP + DOT_R
        mp = self.mapFromGlobal(self.cursor().pos())
        cluster._dot_positions = []

        for idx, ev in enumerate(cluster.events):
            row = idx // cols; col = idx % cols
            cx = ox + col * COL_SPC; cy = oy + row * ROW_SPC
            cluster._dot_positions.append((cx, cy, ev))
            color = self._get_event_color(ev.event_type)
            hovered = abs(mp.x() - cx) < DOT_R + 3 and abs(mp.y() - cy) < DOT_R + 3
            if hovered:
                painter.setBrush(QBrush(QColor(color).lighter(140)))
                painter.setPen(QPen(QColor(color).lighter(160), 2))
                painter.drawEllipse(cx - DOT_R - 2, cy - DOT_R - 2, (DOT_R + 2) * 2, (DOT_R + 2) * 2)
                self._draw_tooltip(painter, ev, cx, by - 10)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(120), 1))
                painter.drawEllipse(cx - DOT_R, cy - DOT_R, DOT_R * 2, DOT_R * 2)

    def _draw_cluster_tooltip(self, painter, cluster):
        lines = [f"Event Cluster", f"{cluster.count} events", "Click to see details"]
        self._render_tooltip(painter, lines, cluster.x_center, THEME['accent'])

    def _draw_highlighted_event(self, painter, ev, tl_y):
        c = QColor("#ffdd00")
        painter.setBrush(QBrush(c))
        painter.setPen(QPen(c.darker(120), 2))
        painter.drawEllipse(ev.x_pos - 7, tl_y - 7, 14, 14)

    def _draw_hovered_event(self, painter, ev, tl_y):
        c = QColor(self._get_event_color(ev.event_type))
        painter.setBrush(QBrush(c.lighter(130)))
        painter.setPen(QPen(c.lighter(150), 2))
        painter.drawEllipse(ev.x_pos - 6, tl_y - 6, 12, 12)

    def _draw_tooltip(self, painter, ev, tip_x=None, tip_y=None):
        t = ev.timestamp.strftime("%H:%M:%S.%f")[:-3]
        lines = [f"{ev.event_type.upper()}: {ev.value}", f"Time: {t}"]
        self._render_tooltip(painter, lines, tip_x if tip_x else ev.x_pos, THEME['accent'], tip_y)

    def _render_tooltip(self, painter, lines, cx, border_color, ty=None):
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        m = painter.fontMetrics()
        mw = max(m.horizontalAdvance(l) for l in lines)
        lh = m.height()
        tw = mw + 20; th = lh * len(lines) + 10
        tx = max(10, min(cx - tw // 2, self.width() - tw - 10))
        ty = ty if ty is not None else 10
        painter.setBrush(QBrush(QColor(THEME['surface_elevated'])))
        painter.setPen(QPen(QColor(border_color), 2))
        painter.drawRoundedRect(tx, ty, tw, th, 4, 4)
        painter.setPen(QColor(THEME['text_primary']))
        yo = ty + lh
        for line in lines:
            painter.drawText(QRect(tx + 10, yo - lh + 5, tw - 20, lh),
                             Qt.AlignLeft | Qt.AlignVCenter, line)
            yo += lh

    def _get_event_color(self, event_type):
        return {
            'domain': THEME['event_domain'],
            'ip':     THEME['event_ip'],
            'port':   THEME['event_port'],
        }.get(event_type, THEME['accent'])


# Enhanced timestamp axis
class TimestampAxis(QWidget):
    def __init__(self, start_time, end_time, height=40, pixels_per_second=50):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.pixels_per_second = pixels_per_second
        self.setFixedHeight(height)
        total = (end_time - start_time).total_seconds()
        self.setMinimumWidth(int(total * pixels_per_second) + 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))

        # Match sidebar labels
        painter.fillRect(0, 0, 100, self.height(), QColor(THEME['surface']))
        painter.setPen(QPen(QColor(THEME['border']), 1))
        painter.drawLine(100, 0, 100, self.height())

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        total = (self.end_time - self.start_time).total_seconds()
        vp = self.visibleRegion().boundingRect()

        if total <= 60:       interval = 5;    fmt = "%H:%M:%S"
        elif total <= 300:    interval = 30;   fmt = "%H:%M:%S"
        elif total <= 1800:   interval = 60;   fmt = "%H:%M:%S"
        elif total <= 3600:   interval = 300;  fmt = "%H:%M:%S"
        elif total <= 86400:  interval = 1800; fmt = "%H:%M"
        else:                 interval = 3600; fmt = "%m/%d %H:%M"

        minor_col = QColor(THEME['border']); minor_col.setAlpha(90)
        painter.setPen(QPen(minor_col, 1))
        minor = interval / 5
        cur = self.start_time
        while cur <= self.end_time:
            e = (cur - self.start_time).total_seconds()
            x = 100 + int(e * self.pixels_per_second)
            if vp.left() - 50 <= x <= vp.right() + 50:
                painter.drawLine(x, 8, x, 14)
            cur += timedelta(seconds=minor)

        # Major ticks and labels
        cur = self.start_time
        while cur <= self.end_time:
            e = (cur - self.start_time).total_seconds()
            x = 100 + int(e * self.pixels_per_second)
            if vp.left() - 100 <= x <= vp.right() + 100:
                painter.setPen(QPen(QColor(THEME['text_secondary']), 2))
                painter.drawLine(x, 4, x, 18)
                painter.setPen(QColor(THEME['text_secondary']))
                painter.drawText(QRect(x - 50, 18, 100, 18), Qt.AlignCenter, cur.strftime(fmt))
            cur += timedelta(seconds=interval)


# Browser activity lane
class IncognitoGapTimeline(QWidget):
    def __init__(self, gap_data, start_time, end_time,
                 normal_events=None, height=120, pixels_per_second=50):
        super().__init__()
        self.gap_data = gap_data
        self.normal_events = normal_events or []
        self.start_time = start_time
        self.end_time = end_time
        self.timeline_height = height
        self.pixels_per_second = pixels_per_second
        self.hovered_gap = None
        self.highlighted_domain = None
        self._dot_positions = []      
        self._normal_dot_positions = [] 
        self._sessions = []
        self._gap_table_ref = None

        self.setMinimumHeight(height)
        self.setMouseTracking(True)
        total = (end_time - start_time).total_seconds()
        self.setMinimumWidth(int(total * pixels_per_second) + 200)

        self._compute_dot_positions()
        self._compute_sessions()

    def set_gap_table(self, ref):
        self._gap_table_ref = ref

    def highlight_domain(self, domain: str):
        self.highlighted_domain = domain
        self.update()

    def clear_highlight(self):
        self.highlighted_domain = None
        self.update()

    def _compute_dot_positions(self):
        self._dot_positions = []
        self._normal_dot_positions = []
        tl_y = self.height() // 2 or self.timeline_height // 2

        for gap in self.gap_data:
            elapsed = (gap['first_seen'] - self.start_time).total_seconds()
            x = 100 + int(elapsed * self.pixels_per_second)
            self._dot_positions.append((x, tl_y, gap))

        # Deduplicate normal events by domain
        seen_domains = {}
        for ev in self.normal_events:
            if not ev.value or ev.value in seen_domains:
                continue
            elapsed = (ev.timestamp - self.start_time).total_seconds()
            x = 100 + int(elapsed * self.pixels_per_second)
            self._normal_dot_positions.append((x, tl_y, ev.value))
            seen_domains[ev.value] = x

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._compute_dot_positions()
        self._compute_sessions()
        self.update()

    def _compute_sessions(self):
        # Group gaps within 5 minutes of each other into inferred session spans
        SESSION_GAP = 300
        self._sessions = []
        if not self._dot_positions:
            return
        dots = sorted(self._dot_positions, key=lambda d: d[0])
        x0 = x1 = dots[0][0]
        scores = [dots[0][2].get('suspiciousness', 50)]
        for i in range(1, len(dots)):
            x, y, gap = dots[i]
            prev = dots[i - 1][2]
            secs = (gap['first_seen'] - prev['first_seen']).total_seconds()
            if secs <= SESSION_GAP:
                x1 = x
                scores.append(gap.get('suspiciousness', 50))
            else:
                if x1 > x0:
                    self._sessions.append((x0, x1, max(scores)))
                x0 = x1 = x
                scores = [gap.get('suspiciousness', 50)]
        if x1 > x0:
            self._sessions.append((x0, x1, max(scores)))

    @staticmethod
    def _dot_color(score):
        if score >= 60: return "#FF4444"
        if score >= 30: return "#FFA500"
        return "#888888"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))

        # Sidebar label zone matches the PCAP lanes above
        painter.fillRect(0, 0, 100, self.height(), QColor(THEME['surface']))
        painter.setPen(QPen(QColor(THEME['border']), 1))
        painter.drawLine(100, 0, 100, self.height())

        # Lane label
        painter.setPen(QColor(THEME['text_primary']))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(10, 0, 85, self.height()), Qt.AlignLeft | Qt.AlignVCenter, "Browser")

        tl_y = self.height() // 2
        vp = self.visibleRegion().boundingRect()

        # Session span bands
        for x0, x1, ms in self._sessions:
            sc = QColor(self._dot_color(ms)); sc.setAlpha(35)
            painter.fillRect(x0 - 10, tl_y - 18, (x1 - x0) + 20, 36, sc)

        track = QColor(THEME['accent']); track.setAlpha(90)
        painter.setPen(QPen(track, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(105, tl_y, self.width() - 20, tl_y)

        for x, y, domain in self._normal_dot_positions:
            if x < vp.left() - 50 or x > vp.right() + 50:
                continue
            painter.setBrush(QBrush(QColor("#4a7a4a")))
            painter.setPen(QPen(QColor("#2d5c2d"), 1))
            painter.drawEllipse(x - 3, y - 3, 6, 6)

        for x, y, gap in self._dot_positions:
            if x < vp.left() - 50 or x > vp.right() + 50:
                continue
            score = gap.get('suspiciousness', 50)
            color = self._dot_color(score)
            is_hover = gap == self.hovered_gap
            is_high = gap['domain'] == self.highlighted_domain

            if is_high:
                painter.setBrush(QBrush(QColor("#ffdd00")))
                painter.setPen(QPen(QColor("#ffdd00").darker(130), 2))
                painter.drawEllipse(x - 7, y - 7, 14, 14)
            elif is_hover:
                painter.setBrush(QBrush(QColor(color).lighter(140)))
                painter.setPen(QPen(QColor(color).lighter(160), 2))
                painter.drawEllipse(x - 6, y - 6, 12, 12)
            else:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(140), 1))
                painter.drawEllipse(x - 5, y - 5, 10, 10)

        if self.hovered_gap:
            self._draw_tooltip(painter, self.hovered_gap)

    def _draw_tooltip(self, painter, gap):
        score = gap.get('suspiciousness', 50)
        lines = [
            gap['domain'],
            f"Category: {gap['category']}",
            f"First seen: {gap['first_seen'].strftime('%H:%M:%S')}",
            f"Occurrences: {gap['count']}"
        ]
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        m = painter.fontMetrics()
        mw = max(m.horizontalAdvance(l) for l in lines)
        lh = m.height()
        tw = mw + 20; th = lh * len(lines) + 10
        dx = next((x for x, y, g in self._dot_positions if g == gap), self.width() // 2)
        tx = max(10, min(dx - tw // 2, self.width() - tw - 10))
        ty = 5
        painter.setBrush(QBrush(QColor(THEME['surface_elevated'])))
        painter.setPen(QPen(QColor(self._dot_color(score)), 2))
        painter.drawRoundedRect(tx, ty, tw, th, 4, 4)
        painter.setPen(QColor(THEME['text_primary']))
        yo = ty + lh
        for line in lines:
            painter.drawText(QRect(tx + 10, yo - lh + 5, tw - 20, lh),
                             Qt.AlignLeft | Qt.AlignVCenter, line)
            yo += lh

    def mouseMoveEvent(self, event):
        mx, my = event.x(), event.y()
        prev = self.hovered_gap
        self.hovered_gap = None
        for x, y, gap in self._dot_positions:
            if abs(mx - x) <= 8 and abs(my - y) <= 8:
                self.hovered_gap = gap
                self.setCursor(Qt.PointingHandCursor)
                break
        else:
            self.setCursor(Qt.ArrowCursor)
        if self.hovered_gap != prev:
            self.update()

    def leaveEvent(self, event):
        self.hovered_gap = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self.hovered_gap:
            return
        if self._gap_table_ref and hasattr(self._gap_table_ref, '_table'):
            tbl = self._gap_table_ref._table
            domain_col = getattr(self._gap_table_ref, '_COL_DOMAIN', 1)
            for row in range(tbl.rowCount()):
                item = tbl.item(row, domain_col)
                if item and item.text() == self.hovered_gap['domain']:
                    tbl.selectRow(row)
                    tbl.scrollToItem(item)
                    break
        event.accept()


# Clickable event card, clicking navigates the timeline to that specific event
class ClickableEventCard(QFrame):
    def __init__(self, event_data, navigate_callback, parent=None):
        super().__init__(parent)
        self._event_data = event_data
        self._navigate_callback = navigate_callback
        self.setCursor(Qt.PointingHandCursor)
        self._base = f"QFrame {{ background-color: {THEME['surface']}; border: 1px solid {THEME['border']}; border-radius: 4px; padding: 5px; }}"
        self._hover = f"QFrame {{ background-color: {THEME['surface_elevated']}; border: 1px solid {THEME['accent']}; border-radius: 4px; padding: 5px; }}"
        self.setStyleSheet(self._base)

    def enterEvent(self, e): self.setStyleSheet(self._hover)
    def leaveEvent(self, e): self.setStyleSheet(self._base)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._navigate_callback:
            self._navigate_callback(self._event_data)
        super().mousePressEvent(event)


# Info panel overlay showing event details when clicking on the timeline
class TimelineInfoPanel(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {THEME['surface_elevated']}; border: 2px solid {THEME['accent']}; border-radius: 6px; }}")
        self.setAutoFillBackground(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header with close button
        header = QHBoxLayout()
        title = QLabel("Event Details")
        title.setStyleSheet(f"color: {THEME['text_primary']}; font-weight: bold; font-size: 11px;")
        header.addWidget(title)
        header.addStretch()

        close = QPushButton("✕")
        close.setFixedSize(18, 18)
        close.clicked.connect(self.hide)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {THEME['text_secondary']}; font-size: 14px; font-weight: bold; }} QPushButton:hover {{ color: {THEME['accent']}; }}")
        header.addWidget(close)
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {THEME['border']};")
        layout.addWidget(sep)

        # Scrollable content area
        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(6)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        self._navigate_callback = None

    def display_events(self, events, navigate_callback=None):
        self._navigate_callback = navigate_callback
        while self.content_layout.count():
            c = self.content_layout.takeAt(0)
            if c.widget():
                c.widget().deleteLater()
        if not events:
            return
        summary = QLabel(f"{len(events)} occurrence(s) — click to focus")
        summary.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 9px;")
        self.content_layout.addWidget(summary)
        for i, ed in enumerate(events):
            self.content_layout.addWidget(self._make_card(ed, i + 1))
        self.content_layout.addStretch()

    def _make_card(self, event_data, number):
        ev = event_data['event']
        filename = event_data['filename']
        siblings = event_data.get('siblings', [])
        card = ClickableEventCard(event_data, self._navigate_callback)
        lay = QVBoxLayout(card)
        lay.setSpacing(2)
        lay.setContentsMargins(4, 4, 4, 4)

        hr = QHBoxLayout()
        num = QLabel(f"#{number}")
        num.setStyleSheet(f"color: {THEME['accent']}; font-weight: bold; font-size: 9px;")
        hr.addWidget(num)
        hr.addStretch()
        hint = QLabel("focus")
        hint.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 8px;")
        hr.addWidget(hint)
        lay.addLayout(hr)

        self._detail(lay, "File:",  filename)
        self._detail(lay, "Time:",  ev.timestamp.strftime('%H:%M:%S.%f')[:-3])
        self._detail(lay, "Proto:", ev.protocol or "N/A")
        self._detail(lay, ev.event_type.upper() + ":", ev.value)

        for s in siblings:
            self._detail(lay, s.event_type.upper() + ":", s.value)
        return card

    def _detail(self, lay, label, value):
        disp = (str(value)[:32] + "...") if len(str(value)) > 35 else str(value)
        row = QLabel(f"<b>{label}</b> {disp}")
        row.setWordWrap(True)
        row.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 9px;")
        lay.addWidget(row)


# Main timeline widget
class CrossPCAPTimelineWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.pcap_timelines = []
        self.timestamp_axis = None
        self.pixels_per_second = 50
        self.start_time = None
        self.end_time = None
        self._incognito_lane = None
        self._sep_label = None
        # Cached so the incognito lane survives rebuilds
        self._incognito_gap_data = None
        self._incognito_gap_table = None
        self._normal_events = None
        # Focus mode state
        self._in_focus = False
        self._focus_window = None
        self._focused_gap = None

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()

        title = QLabel("Network Activity Timeline")
        title.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self._perf_label = QLabel("")
        self._perf_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px;")
        header.addWidget(self._perf_label)

        self._hash_label = QLabel("")
        self._hash_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px;")
        header.addWidget(self._hash_label)

        layout.addLayout(header)

        # Focus bar
        self._focus_bar = QWidget()
        self._focus_bar.setFixedHeight(34)
        self._focus_bar.setStyleSheet(f"background-color: {THEME['accent']};")
        focus_bar_layout = QHBoxLayout(self._focus_bar)
        focus_bar_layout.setContentsMargins(12, 4, 12, 4)

        self._focus_label = QLabel("Focused view")
        self._focus_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        focus_bar_layout.addWidget(self._focus_label)
        focus_bar_layout.addStretch()

        exit_btn = QPushButton("X  Exit Focus")
        exit_btn.setFixedHeight(24)
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.5);
                border-radius: 4px;
                padding: 0px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.35);
            }
        """)
        exit_btn.clicked.connect(self.exit_focus)
        focus_bar_layout.addWidget(exit_btn)

        self._focus_bar.hide()
        layout.addWidget(self._focus_bar)
        self.scroll = QScrollArea()
        self.scroll.setMinimumHeight(300)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {THEME['border']};
                background-color: {THEME['timeline_bg']};
                border-radius: 4px;
            }}
            QScrollBar:vertical {{
                width: 14px; background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']}; border-radius: 7px; min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {THEME['text_secondary']}; }}
        """)

        self.timeline_container = QWidget()
        self.timeline_container.setStyleSheet(f"background-color: {THEME['timeline_bg']};")
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setSpacing(0)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.timeline_container)
        layout.addWidget(self.scroll)

        # Info panel overlay (initially hidden)
        self.info_panel = TimelineInfoPanel(self)
        self.info_panel.hide()

    def set_hash_statuses(self, statuses: dict):
        # statuses is {filename: status} e.g. {'capture.pcap': 'verified'}
        n_mismatch = sum(1 for s in statuses.values() if s == 'mismatch')
        n_verified  = sum(1 for s in statuses.values() if s == 'verified')
        n_new       = sum(1 for s in statuses.values() if s == 'new')

        if n_mismatch:
            badge = f"🔴 {n_mismatch} HASH MISMATCH{'ES' if n_mismatch > 1 else ''}"
        elif n_verified:
            badge = f"🟢 {n_verified} verified"
        else:
            badge = f"🔵 {n_new} new"

        self._hash_label.setText(f"  |  PCAPs: {badge}")

    # Public API
    def load_timeline_data(self, timeline_data: dict):
        try:

            self._incognito_gap_data = None
            self._incognito_gap_table = None
            self._clear_lanes()
            all_events = [e for evs in timeline_data.values() for e in evs]

            if not all_events:
                no_data = QLabel("No events found for selected fields")
                no_data.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")
                self.timeline_layout.addWidget(no_data)
                return

            self.start_time = min(e.timestamp for e in all_events)
            self.end_time = max(e.timestamp for e in all_events)

            self._perf_label.setText(f"{len(all_events)} events loaded")

            for idx, (pcap_name, events) in enumerate(sorted(timeline_data.items())):
                if events:
                    tl = PCAPTimeline(pcap_name, events,
                                      self.start_time, self.end_time,
                                      pixels_per_second=self.pixels_per_second,
                                      lane_index=idx)
                    self.pcap_timelines.append(tl)
                    self.timeline_layout.addWidget(tl, 1)

            self.timestamp_axis = TimestampAxis(self.start_time, self.end_time,
                                                pixels_per_second=self.pixels_per_second)
            self.timeline_layout.addWidget(self.timestamp_axis)

            # Auto-fit once the widget has finished laying out
            QTimer.singleShot(100, self._fit_to_viewport)

        except Exception as e:
            print(f"Error loading timeline data: {e}")

    def _fit_to_viewport(self):
        # Calculate pixels_per_second so the full timeline spans the visible width
        if not self.start_time or not self.end_time:
            return
        total_sec = (self.end_time - self.start_time).total_seconds()
        if total_sec <= 0:
            return
        available = self.scroll.viewport().width() - 120
        if available <= 0:
            return
        self.pixels_per_second = max(1.0, available / total_sec)
        self._rebuild_timelines()

    def load_browser_activity(self, gap_data, normal_events=None, gap_table_ref=None):
        # Cache everything so _rebuild_timelines can restore after zoom/fit
        self._incognito_gap_data = gap_data
        self._normal_events = normal_events or []
        self._incognito_gap_table = gap_table_ref
        self._insert_incognito_lane()

    def highlight_incognito_gap(self, gap: dict):
        if self._incognito_lane:
            self._incognito_lane.highlight_domain(gap['domain'])

    def clear_incognito_highlight(self):
        if self._incognito_lane:
            self._incognito_lane.clear_highlight()

    def focus_on_gap(self, gap: dict):
        if not self.start_time or not self.end_time:
            return

        PADDING = 20  # seconds of context either side
        focus_start = max(self.start_time, gap['first_seen'] - timedelta(seconds=PADDING))
        focus_end = min(self.end_time, gap['last_seen'] + timedelta(seconds=PADDING))

        self._in_focus = True
        self._focus_window = (focus_start, focus_end)
        self._focused_gap = gap

        total_sec = (focus_end - focus_start).total_seconds()
        available = self.scroll.viewport().width() - 120
        if total_sec > 0 and available > 0:
            self.pixels_per_second = available / total_sec

        self._rebuild_timelines()

        self._focus_label.setText(f"Focused on: {gap['domain']}  —  {gap['first_seen'].strftime('%H:%M:%S')} → {gap['last_seen'].strftime('%H:%M:%S')}")
        self._focus_bar.show()

    def exit_focus(self):
        self._in_focus = False
        self._focus_window = None
        self._focused_gap = None
        self._focus_bar.hide()
        self._fit_to_viewport()

    def _apply_focus_highlight(self):
        # Called via singleShot after layout settles so the lane is visible
        if self._focused_gap and self._incognito_lane:
            self._incognito_lane.highlight_domain(self._focused_gap['domain'])

    def clear_timeline(self):
        for tl in self.pcap_timelines:
            tl.clear_highlights()

    def on_timeline_event_clicked(self, event, pcap_name):
        entries = self._build_correlated_entries(event.event_type, event.value)
        if entries:
            self.info_panel.display_events(entries, navigate_callback=self.navigate_to_event)
            self.info_panel.show()
            self.info_panel.raise_()
            self.info_panel.setGeometry(self.width() - 415, 10, 400, 500)
        for tl in self.pcap_timelines:
            matching = [e for e in tl.events
                        if e.value == event.value and e.event_type == event.event_type]
            if matching:
                tl.set_highlighted_events(matching)

    def navigate_to_event(self, event_data):
        ev = event_data['event']
        fn = event_data['filename']
        for tl in self.pcap_timelines:
            if tl.pcap_name == fn:
                tl.set_highlighted_events([ev])
            else:
                tl.clear_highlights()

    # Helpers

    def _insert_incognito_lane(self):
        # Remove stale lane and separator before inserting fresh ones
        if self._incognito_lane:
            self._incognito_lane.deleteLater()
            self._incognito_lane = None
        if self._sep_label:
            self._sep_label.deleteLater()
            self._sep_label = None

        if not self._incognito_gap_data or not self.start_time or not self.end_time:
            return

        # Use focus window bounds when zoomed in, otherwise full range
        lane_start = self._focus_window[0] if self._focus_window else self.start_time
        lane_end = self._focus_window[1] if self._focus_window else self.end_time

        # In focus mode only show gaps within the window, otherwise show all
        if self._focus_window:
            lane_gaps = [
                g for g in self._incognito_gap_data
                if lane_start <= g['first_seen'] <= lane_end
            ]
            # Always include the focused gap itself even if it sits on the boundary
            if self._focused_gap and self._focused_gap not in lane_gaps:
                lane_gaps = [self._focused_gap] + lane_gaps
        else:
            lane_gaps = self._incognito_gap_data

        if not lane_gaps:
            lane_gaps = self._incognito_gap_data

        self._sep_label = QLabel("BROWSER ACTIVITY   ·   incognito gaps  ●   normal history  ●")
        self._sep_label.setFixedHeight(24)
        self._sep_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._sep_label.setStyleSheet(f"""
            background-color: {THEME['surface']};
            color: {THEME['text_secondary']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            padding-left: 12px;
            border-top: 2px solid {THEME['accent']};
            border-bottom: 1px solid {THEME['border']};
        """)

        self._incognito_lane = IncognitoGapTimeline(
            lane_gaps, lane_start, lane_end,
            normal_events=[ev for ev in (self._normal_events or [])
                           if lane_start <= ev.timestamp <= lane_end],
            height=110, pixels_per_second=self.pixels_per_second
        )
        if self._incognito_gap_table:
            self._incognito_lane.set_gap_table(self._incognito_gap_table)

        idx = self.timeline_layout.indexOf(self.timestamp_axis)
        if idx >= 0:
            self.timeline_layout.insertWidget(idx, self._sep_label)
            self.timeline_layout.insertWidget(idx + 1, self._incognito_lane, 1)
        else:
            self.timeline_layout.addWidget(self._sep_label)
            self.timeline_layout.addWidget(self._incognito_lane, 1)

    def _clear_lanes(self):
        for i in reversed(range(self.timeline_layout.count())):
            w = self.timeline_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.pcap_timelines = []
        self._incognito_lane = None
        self._sep_label = None

    def _rebuild_timelines(self):
        if not self.pcap_timelines and not self._focus_window:
            return
        data = {tl.pcap_name: tl.events for tl in self.pcap_timelines}
        self._clear_lanes()

        start = self._focus_window[0] if self._focus_window else self.start_time
        end = self._focus_window[1] if self._focus_window else self.end_time

        for idx, (name, evs) in enumerate(sorted(data.items())):
            if evs:
                tl = PCAPTimeline(name, evs, start, end,
                                  pixels_per_second=self.pixels_per_second,
                                  lane_index=idx)
                if self._focus_window:
                    tl.use_clustering = False
                    tl._create_clusters()
                    # Compare timestamps 
                    def _ts(t):
                        return t.replace(tzinfo=None) if t.tzinfo else t
                    s = _ts(start)
                    e2 = _ts(end)
                    in_window = {e for e in evs if s <= _ts(e.timestamp) <= e2}
                    tl.set_visible_events(in_window if in_window else None)
                self.pcap_timelines.append(tl)
                self.timeline_layout.addWidget(tl, 1)

        self.timestamp_axis = TimestampAxis(start, end,
                                            pixels_per_second=self.pixels_per_second)
        self.timeline_layout.addWidget(self.timestamp_axis)
        self._insert_incognito_lane()

        # Apply highlight after layout has settled
        if self._focused_gap and self._incognito_lane:
            QTimer.singleShot(50, lambda: self._apply_focus_highlight())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Don't refit while in focus mode, it would reset the zoom
        if not self._in_focus:
            QTimer.singleShot(50, self._fit_to_viewport)

    def _build_correlated_entries(self, match_type, match_value):
        results = []
        for tl in self.pcap_timelines:
            for e in tl.events:
                if e.event_type == match_type and e.value == match_value:
                    siblings = [s for s in tl.events if s.timestamp == e.timestamp and s is not e]
                    results.append({'event': e, 'filename': tl.pcap_name, 'siblings': siblings})
        return results