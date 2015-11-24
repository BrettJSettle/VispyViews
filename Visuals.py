from __future__ import division
import numpy as np
from PyQt4.QtCore import pyqtSignal as Signal
from vispy import app
from vispy import gloo
from vispy.visuals.shaders import ModularProgram
from vispy.visuals import Visual, LinePlotVisual, LineVisual, PolygonVisual
from vispy.visuals.transforms import (STTransform, LogTransform,
                                      TransformSystem, ChainTransform)
from pyqtgraph import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from Points import *

class BorderVisual(PolygonVisual):
    def __init__(self, active_points):
        BorderVisual.__init__(self, color=None, border_color='green')
        self.points = BorderVisual.getBorderPoints([p.pos for p in active_points])

    @staticmethod
    def order_walls(walls):
        new_wall = walls.pop(0)
        while walls:
            add = [wall for wall in walls if new_wall[-1] in wall][0]
            walls.remove(add)
            add.remove(new_wall[-1])
            new_wall.extend(add)
        return new_wall

    @staticmethod
    def getBorderPoints(points):
        if len(points) > 2:
            ch = ConvexHull(points)
            outerwalls = order_walls(ch.simplices.tolist())
            return np.array([points[i] for i in outerwalls], dtype=np.float32)
            

class ChannelVisual(Visual):
    channel_colors = {}
    # My full vertex shader, with just a `transform` hook.
    VERTEX_SHADER = """
        #version 120

        attribute vec2 a_position;
        attribute vec3 a_color;
        attribute float a_size;

        varying vec4 v_fg_color;
        varying vec4 v_bg_color;
        varying float v_radius;
        varying float v_linewidth;
        varying float v_antialias;

        void main (void) {
            v_radius = a_size;
            v_linewidth = 1.0;
            v_antialias = 1.0;
            v_fg_color  = vec4(0.0,0.0,0.0,0.5);
            v_bg_color  = vec4(a_color,    1.0);

            gl_Position = $transform(vec4(a_position,0,1));

            gl_PointSize = 2.0*(v_radius + v_linewidth + 1.5*v_antialias);
        }
    """

    FRAGMENT_SHADER = """
        #version 120
        varying vec4 v_fg_color;
        varying vec4 v_bg_color;
        varying float v_radius;
        varying float v_linewidth;
        varying float v_antialias;
        void main()
        {
            float size = 2.0*(v_radius + v_linewidth + 1.5*v_antialias);
            float t = v_linewidth/2.0-v_antialias;
            float r = length((gl_PointCoord.xy - vec2(0.5,0.5))*size);
            float d = abs(r - v_radius) - t;
            if( d < 0.0 )
                gl_FragColor = v_fg_color;
            else
            {
                float alpha = d/v_antialias;
                alpha = exp(-alpha*alpha);
                if (r > v_radius)
                    gl_FragColor = vec4(v_fg_color.rgb, alpha*v_fg_color.a);
                else
                    gl_FragColor = mix(v_bg_color, v_fg_color, alpha);
            }
        }
    """

    def __init__(self, name, active_points=None, color=None, size=None):
        self._program = ModularProgram(self.VERTEX_SHADER,
                                       self.FRAGMENT_SHADER)        
        self.name = name
        self.set_data(active_points=active_points, color=color, size=size)

    @staticmethod
    def getChannelColor(name):
        if name in ChannelVisual.channel_colors:
            return ChannelVisual.channel_colors[name]
        else:
            ChannelVisual.channel_colors[name] = np.random.random((3,))
            return ChannelVisual.channel_colors[name]

    def set_options(self):
        """Special function that is used to set the options. Automatically
        called at initialization."""
        gloo.set_state(clear_color=(1, 1, 1, 1), blend=True,
                       blend_func=('src_alpha', 'one_minus_src_alpha'))

    def set_data(self, active_points=None, color=None, size=None):
        """I'm not required to use this function. We could also have a system
        of trait attributes, such that a user doing
        `visual.position = myndarray` results in an automatic update of the
        buffer. Here I just set the buffers manually."""
        self.points = active_points
        pos = np.array([p.pos for p in active_points], dtype=np.float32)
        if color == None:
            color = ChannelVisual.getChannelColor(self.name)
        if color.ndim == 1:
            color = np.array([color for i in range(len(pos))], dtype=np.float32)
        if size == None:
            size = np.ones((len(active_points),)).astype(np.float32) * 2
        self._pos = pos
        self._color = color
        self._size = size

    def draw(self, transforms):
        # attributes / uniforms are not available until program is built
        tr = transforms.get_full_transform()
        self._program.vert['transform'] = tr.shader_map()
        self._program.prepare()  # Force ModularProgram to set shaders
        self._program['a_position'] = gloo.VertexBuffer(self._pos)
        self._program['a_color'] = gloo.VertexBuffer(self._color)
        self._program['a_size'] = gloo.VertexBuffer(self._size)
        self._program.draw('points')

class ROIVisual(PolygonVisual):
    def __init__(self, pos):
        PolygonVisual.__init__(self, color=None, border_color='white')
        self.points = np.array([pos],dtype=np.float32)
        self.finished = False
        self.hover = False
        self.selected = False
        self._selected_color = np.array([1, 1, 1], dtype=np.float32)
        self.colorDialog=QtGui.QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
        self._make_menu()

    def colorSelected(self, color):
        self.border_color = (color.redF(), color.greenF(), color.blueF())
        self._selected_color = self.border_color

    def mouseIsOver(self, pos):
        self.hover = self.contains(pos)
        return self.hover

    def _make_menu(self):
        self.menu = QtGui.QMenu('ROI Menu')
        self.menu.addAction(QtGui.QAction("Change Color", self.menu, triggered = self.colorDialog.show))

    def contextMenuEvent(self, pos):
        self.menu.popup(pos)

    def extend(self, pos):
        if not self.finished:
            self.points = np.array(np.vstack((self.points, pos)), dtype=np.float32)
            self.pos = self.points
        
    def select(self):
        self.selected = True
        self.border_color = np.array([1, 0, 0], dtype=np.float32)

    def deselect(self):
        self.selected = False
        self.border_color = self._selected_color

    def draw_finished(self):
        self.points = np.vstack((self.points, self.points[0]))
        self.pos = self.points
        self.finished = True
        self.select()

    def contains(self, pt):
        if not hasattr(self, 'path_item'):
            self.path_item = QtGui.QPainterPath()
            self.path_item.moveTo(*self.points[0])
            for i in self.points[1:]:
                self.path_item.lineTo(*i)
            self.path_item.lineTo(*self.points[0])
        return self.path_item.contains(QtCore.QPointF(*pt))

    def translate(self, dxy):
        self.points += dxy
        self.pos = self.points
        if hasattr(self, 'path_item'):
            self.path_item.translate(*dxy)
    
    def draw(self, tr_sys):
        if not self.finished:
            color = np.ones((len(self.points), 3)).astype(np.float32)
            lp = LinePlotVisual(data=self.points, color=color)
            lp.draw(tr_sys)
        elif len(self.points) > 2:
            PolygonVisual.draw(self, tr_sys)
