from Config import Settings
from PyQT5.QtCore import *
from PyQT5.QtGui import *
import math

class Plot(QGraphicsScene):
    def __init__(self, x, y, *args):
        super(Plot, self).__init__(*args)

        if len(x) < 2:
            return

        min_x, max_x = min(x), max(x)
        min_y, max_y = min(y), max(y)

        p = QPen(Qt.blue)
        p.setCosmetic(True)
        p.setWidthF(2.0)
        p.setCapStyle(Qt.RoundCap)
        for i in range(0, len(x)-1):
            self.addLine(x[i], -y[i], x[i+1], -y[i+1], p)

        # Add axes
        if Settings.get('show_xaxis'):
            if min_y > 0:
                min_y = 0
            elif max_y < 0:
                max_y = 0
        if min_y <= 0 <= min_y:
            self.addLine(min_x, 0, max_x, 0)
        if min_x <= 0 <= max_x:
            self.addLine(0, -min_y, 0, -max_y)

        w, h = max_x - min_x, max_y - min_y

        if h <= 0 or w <= 0:
            return

        # Add background lines
        spc = math.pow(10.0, math.ceil(math.log10(h)-1))
        while h/spc < 5:
            spc /= 2

        ns = int(min_y/spc) * spc
        start = ns

        qp = QPen(QColor(Qt.lightGray))
        qp.setStyle(Qt.DotLine)

        while start < max_y + spc:
            lin = self.addLine(min_x, -start, max_x, -start, qp)
            lin.setZValue(-1.0)

            lbl = QGraphicsSimpleTextItem("%g" % start)
            th, tw = lbl.boundingRect().height(), lbl.boundingRect().width()
            lbl.scale(0.026*w/tw, spc/th)
            lbl.setPos(QPointF(min_x - 0.03*w, -start-spc/2))
            self.addItem(lbl)

            start += spc

        qr = QRectF(min_x-0.03*w, -start+spc/2, 1.03*w, start-ns)
        self.setSceneRect(qr)

class Plotter(QGraphicsView):
    def __init__(self, *args):
        super(Plotter, self).__init__(*args)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        #self.connect(scene, SIGNAL("sceneRectChanged(QRectF)"), self.fitInView)

    def resizeEvent(self, evt):
        QGraphicsView.resizeEvent(self, evt)
        if self.scene():
            self.fitInView(self.scene().sceneRect())

    def setScene(self, scene):
        QGraphicsView.setScene(self, scene)
        self.fitInView(scene.sceneRect())

