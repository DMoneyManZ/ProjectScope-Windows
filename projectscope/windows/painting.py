"""Qt implementation of the portable crosshair geometry; no Cairo dependency."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from projectscope.render import extent


def render_image(style, width=None, height=None, *, device_pixel_ratio=1.0):
    """Render on a transparent surface, applying opacity to the whole group once."""
    size = math.ceil(extent(style) * 2)
    width = size if width is None else width
    height = size if height is None else height
    ratio = max(1.0, float(device_pixel_ratio))
    layer = QImage(math.ceil(width * ratio), math.ceil(height * ratio), QImage.Format.Format_ARGB32_Premultiplied)
    layer.setDevicePixelRatio(ratio)
    layer.fill(Qt.GlobalColor.transparent)
    painter = QPainter(layer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(width / 2, height / 2)
    painter.rotate(style['rotation'])
    painter.scale(style['scale'], style['scale'])

    def shapes(pad, color):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        lines = style['lines']
        if lines['enabled']:
            t, g, n = lines['thickness'], lines['gap'], lines['length']
            rects = [(g, -t / 2, n, t), (-g - n, -t / 2, n, t), (-t / 2, g, t, n)]
            if lines['top']:
                rects.append((-t / 2, -g - n, t, n))
            for x, y, w, h in rects:
                painter.drawRect(QRectF(x - pad, y - pad, w + 2 * pad, h + 2 * pad))
        dot = style['dot']
        if dot['enabled']:
            radius = dot['radius'] + pad
            painter.drawEllipse(QPointF(0, 0), radius, radius)
        circle = style['circle']
        if circle['enabled']:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(color), circle['thickness'] + 2 * pad))
            painter.drawEllipse(QPointF(0, 0), circle['radius'], circle['radius'])

    if style['outline_width'] > 0:
        shapes(style['outline_width'], style['outline_color'])
    shapes(0, style['color'])
    painter.end()
    result = QImage(layer.size(), layer.format())
    result.setDevicePixelRatio(ratio)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setOpacity(style['opacity'])
    painter.drawImage(QPointF(0, 0), layer)
    painter.end()
    return result
