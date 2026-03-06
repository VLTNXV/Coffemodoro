import gi
import math
import random

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

try:
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg as _Rsvg
    _HAS_RSVG = True
except Exception:
    _HAS_RSVG = False

try:
    import cairo as _cairo
    _OP_CLEAR = _cairo.OPERATOR_CLEAR
    _OP_OVER  = _cairo.OPERATOR_OVER
except ImportError:
    _OP_CLEAR = _OP_OVER = None

import os as _os
_SVG_PATH = _os.path.join(_os.path.dirname(__file__), "..", "assets", "coffee_machine.svg")

# ── SVG coordinate reference (mm, viewBox 0 0 210 297) ────────────────────────
_SVG_W = 210.0
_SVG_H = 297.0

# Crop to machine content with ~5 mm padding (avoids rendering blank A4 space)
_CROP_X = 27.0
_CROP_Y = 64.0
_CROP_W = 155.0
_CROP_H = 165.0

# Nozzle bottom centres
_L_NOZ_CX    = 88.746 + 10.560 / 2   # 94.026
_R_NOZ_CX    = 110.345 + 10.560 / 2  # 115.625
_NOZ_BOTTOM  = 125.994 + 7.200        # 133.194

# Mug walls (from path trace)
_MUG_TOP_Y   = 160.736
_MUG_BOT_Y   = 203.597
_MUG_TOP_L   = 82.037
_MUG_TOP_R   = 126.783
_MUG_BOT_L   = 95.210
_MUG_BOT_R   = 114.789

# Indicator
_IND_CX = 71.649
_IND_CY = 86.373
_IND_R  = 3.562


def _get_accent(widget):
    found, rgba = widget.get_style_context().lookup_color("accent_bg_color")
    if found:
        return (rgba.red, rgba.green, rgba.blue)
    return (53 / 255, 132 / 255, 228 / 255)


def _to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r * 255))),
        max(0, min(255, int(g * 255))),
        max(0, min(255, int(b * 255))),
    )


class CoffeeAnimation(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.progress  = 0.0
        self.running   = False
        self.is_break  = False

        self._pulse    = 0.0
        self._pulsing  = False
        self._accent   = None

        self._svg_handle   = None
        self._cached_hex   = None

        self._ind_phase    = 0.0
        self._stream_alpha = [0.72, 0.72]
        self._stream_cd    = 0

        self.set_draw_func(self._draw)
        GLib.timeout_add(33, self._on_frame)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_progress(self, progress: float, is_break: bool = False):
        p = max(0.0, min(1.0, progress))
        self.progress = 1.0 - p if is_break else p
        self.is_break = is_break

    def set_running(self, running: bool):
        self.running = running

    def pulse_complete(self):
        self._pulse   = 0.0
        self._pulsing = True

    # ── Internals ──────────────────────────────────────────────────────────────

    def _svg_handle_for(self, r, g, b):
        if not _HAS_RSVG:
            return None
        hex_color = _to_hex(r, g, b)
        if self._svg_handle is not None and self._cached_hex == hex_color:
            return self._svg_handle
        try:
            with open(_SVG_PATH, "r", encoding="utf-8") as fh:
                svg = fh.read()
            svg = svg.replace("stroke:#000000", f"stroke:{hex_color}")
            svg = svg.replace("fill:#000000",   f"fill:{hex_color}")
            self._svg_handle = _Rsvg.Handle.new_from_data(svg.encode("utf-8"))
            self._cached_hex = hex_color
        except Exception:
            self._svg_handle = None
        return self._svg_handle

    def _xform(self, w, h):
        """(scale, ox, oy) — maps SVG mm coords → widget pixels, content centred."""
        scale = min(w / _CROP_W, h / _CROP_H)
        ox = (w - _CROP_W * scale) / 2 - _CROP_X * scale
        oy = (h - _CROP_H * scale) / 2 - _CROP_Y * scale
        return scale, ox, oy

    def _px(self, x, y, scale, ox, oy):
        return ox + x * scale, oy + y * scale

    def _draw_mug_path(self, cr, scale, ox, oy):
        """Trace the coffee_mug SVG path exactly in Cairo pixel space."""
        s = scale
        def _a(x, y):  return ox + x * s, oy + y * s  # absolute SVG → pixels
        def _d(dx, dy): return dx * s, dy * s           # relative SVG → pixels

        cr.move_to(*_a(82.037379, 160.73628))
        cr.rel_line_to(*_d(44.746161, 0))
        cr.rel_curve_to(*_d(1.06363, 0), *_d(1.92916, 0.84726), *_d(1.91991, 1.91991))
        cr.rel_line_to(*_d(-0.24404, 28.28336))
        cr.rel_curve_to(*_d(-0.11552, 13.38759), *_d(-12.84417, 12.65753), *_d(-13.66973, 12.65753))
        cr.line_to(*_a(95.210319, 203.59708))   # H — absolute x, y unchanged
        cr.rel_curve_to(*_d(-1.063631, 0), *_d(-15.453265, 0.82996), *_d(-15.33689, -12.65753))
        cr.rel_line_to(*_d(0.244039, -28.28336))
        cr.rel_curve_to(*_d(0.0092, -1.06359), *_d(0.85628, -1.91991), *_d(1.919911, -1.91991))
        cr.close_path()

    # ── Frame loop ─────────────────────────────────────────────────────────────

    def _on_frame(self):
        if self.running:
            self._ind_phase = (self._ind_phase + 0.035) % 1.0
            self._stream_cd -= 1
            if self._stream_cd <= 0:
                self._stream_alpha = [
                    random.uniform(0.50, 0.85),
                    random.uniform(0.50, 0.85),
                ]
                self._stream_cd = random.randint(4, 10)

        if self._pulsing:
            self._pulse += 0.05
            if self._pulse >= 1.0:
                self._pulsing = False
                self._pulse   = 0.0

        self.queue_draw()
        return True

    # ── Draw ───────────────────────────────────────────────────────────────────

    def _draw(self, _area, cr, w, h):
        if self._accent is None:
            self._accent = _get_accent(self)
        r, g, b = self._accent

        if _OP_CLEAR is not None:
            cr.set_operator(_OP_CLEAR)
            cr.paint()
            cr.set_operator(_OP_OVER)

        scale, ox, oy = self._xform(w, h)

        # ── Coffee fill (drawn before SVG so mug outline renders on top) ───────
        # The mug's 4 mm stroke naturally frames the fill with equal spacing on
        # all sides; no manual inset needed.
        if self.progress > 0:
            bot    = _MUG_BOT_Y
            top    = _MUG_TOP_Y
            surf_y = bot - (bot - top) * self.progress

            cr.save()
            self._draw_mug_path(cr, scale, ox, oy)
            cr.clip()

            fl, ft = self._px(_MUG_TOP_L, surf_y,      scale, ox, oy)
            fr, fb = self._px(_MUG_TOP_R, _MUG_BOT_Y,  scale, ox, oy)
            cr.set_source_rgba(r * 0.55, g * 0.55, b * 0.55, 0.85)
            cr.rectangle(fl, ft, fr - fl, fb - ft)
            cr.fill()
            cr.restore()

        # ── SVG machine (drawn after fill so mug outline covers fill edges) ────
        handle = self._svg_handle_for(r, g, b)
        if handle is not None:
            cr.save()
            cr.translate(ox, oy)
            cr.scale(scale, scale)
            vp = _Rsvg.Rectangle()
            vp.x, vp.y, vp.width, vp.height = 0.0, 0.0, _SVG_W, _SVG_H
            handle.render_document(cr, vp)
            cr.restore()

        # ── Streams (focus only, disappear when mug is full) ──────────────────
        show_streams = self.running and not self.is_break and self.progress < 1.0
        if show_streams:
            bot     = _MUG_BOT_Y
            top_max = _MUG_TOP_Y
            surf_y  = bot - (bot - top_max) * self.progress

            stream_w = 2.0 * scale
            for i, cx in enumerate((_L_NOZ_CX, _R_NOZ_CX)):
                x0, y0 = self._px(cx, _NOZ_BOTTOM,  scale, ox, oy)
                _,  y1 = self._px(cx, surf_y,        scale, ox, oy)
                if y1 > y0:
                    cr.set_source_rgba(r, g, b, self._stream_alpha[i])
                    cr.rectangle(x0 - stream_w / 2, y0, stream_w, y1 - y0)
                    cr.fill()

        # ── Indicator pulse rings ──────────────────────────────────────────────
        if self.running:
            ix, iy = self._px(_IND_CX, _IND_CY, scale, ox, oy)
            r_base = _IND_R * scale
            cr.set_line_width(1.0)
            for offset in (0.0, 0.5):
                phase  = (self._ind_phase + offset) % 1.0
                ring_r = r_base * (1.0 + phase * 2.5)
                alpha  = (1.0 - phase) * 0.55
                cr.set_source_rgba(r, g, b, alpha)
                cr.arc(ix, iy, ring_r, 0, 2 * math.pi)
                cr.stroke()

        # ── Completion pulse ───────────────────────────────────────────────────
        if self._pulsing:
            glow = math.sin(self._pulse * math.pi) * 0.14
            cr.set_source_rgba(r, g, b, glow)
            cr.paint()
