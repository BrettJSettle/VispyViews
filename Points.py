import numpy as np
import pyqtgraph as pg
from scipy.spatial import ConvexHull, Delaunay

class ActivePoint():
    def __init__(self, data):
        self.pos = np.array([data['Xc'], data['Yc']])
        self.data = data

    def withZ(self):
        return np.array([self[0], self[1], self['Zc']])

    def __getitem__(self, item):
        if type(item) in (int, tuple, slice):
            return self.pos[item]
        if item in self.data:
            return self.data[item]
        else:
            return self.__dict__[item]


def distance(ptA, ptB):
    return np.linalg.norm(np.subtract(ptA[:2], ptB[:2]))

def order_walls(walls):
    new_wall = walls.pop(0)
    while walls:
        add = [wall for wall in walls if new_wall[-1] in wall][0]
        walls.remove(add)
        add.remove(new_wall[-1])
        new_wall.extend(add)
    return new_wall

def getTriangleArea(A, B, C):
    return .5 * abs(A[0]*(B[1] - C[1]) + B[0]*(C[1] - A[1]) + C[0]*(A[1] - B[1]))

def getBorderPoints(points):
    if len(points) > 2:
        ch = ConvexHull(points)
        outerwalls = order_walls(ch.simplices.tolist())
        return [points[i] for i in outerwalls]
    return []

def inSquare(p, x, y, s):
    return x <= p[0] <= x + s and y <= p[1] <= y + s

def gridArea(points):
    dist = averageDistance(points)
    x, y = np.transpose([(p[0], p[1]) for p in points])
    area = 0

    for i in np.arange(min(x), max(x), dist):
        for j in np.arange(min(y), max(y), dist):
            if any([inSquare(p, i, j, dist) for p in points]):
                area += dist ** 2
                continue
    return area

def boxArea(points):
    x, y = np.transpose([(p[0], p[1]) for p in points])
    width = max(x) - min(x)
    height = max(y) - min(y)
    return width * height

def averageDistance(points):
    dists = []
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            dists.append(np.linalg.norm(points[i] - points[j]))
    return sum(dists) / len(dists)
    

def concaveArea(points):
    tri = Delaunay(points)
    outerwalls = tri.convex_hull.tolist()
    outerwalls = order_walls(outerwalls)
    verts = tri.vertices.tolist()
    change = False
    i = 0
    while i < len(outerwalls) - 1:
        at = outerwalls[i]
        next = outerwalls[i + 1]
        outer_dist = distance(points[at], points[next])
        inner = None
        for t in verts:
            inners = set(t) ^ {at, next}
            if len(inners) == 1 and len(set(outerwalls) & set(t)) == 2:
                inner = inners.pop()
                break
        if inner != None and outer_dist > distance(points[at], points[inner]):
            outerwalls.insert(i+1, inner)
            change = True
            verts.remove(t)
            i += 1
        i += 1
        if i >= len(outerwalls) - 1 and change:
            change = False
            i = 0
    pts = np.array([points[i] for i in outerwalls])
    return sum(map(lambda vs: getTriangleArea(*[points[i] for i in vs]), verts))