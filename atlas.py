import re
from enum import Enum
from pathlib import PurePath, Path
from nbt import nbt
from PIL import Image
from PIL.ImagePalette import ImagePalette
from collections import defaultdict

map_id_re = re.compile(r"^map_(\d+)$")

SIDE_LEN = [ 2 ** (7+i) for i in range(0, 5)]


class Direction(Enum):
    NW = 0
    NE = 1
    SW = 2
    SE = 3




class MinecraftPalette(ImagePalette):
    palette_1_12 = [
        0,0,0,0,0,0,0,0,0,0,0,0,90,126,40,110,154,48,127,178,56,67,94,30,174,164,115,213,201,141,247,233,163,131,123,86,140,140,140,172,172,172,199,199,199,105,105,105,180,0,0,220,0,0,255,0,0,135,0,0,113,113,180,138,138,220,160,160,255,85,85,135,118,118,118,144,144,144,167,167,167,88,88,88,0,88,0,0,107,0,0,124,0,0,66,0,180,180,180,220,220,220,255,255,255,135,135,135,116,119,130,141,145,159,164,168,184,87,89,97,107,77,54,130,94,66,151,109,77,80,58,41,79,79,79,97,97,97,112,112,112,59,59,59,45,45,180,55,55,220,64,64,255,34,34,135,101,84,51,123,103,62,143,119,72,76,63,38,180,178,173,220,217,211,255,252,245,135,133,130,152,90,36,186,110,44,216,127,51,114,67,27,126,54,152,154,66,186,178,76,216,94,40,114,72,108,152,88,132,186,102,153,216,54,81,114,162,162,36,198,198,44,229,229,51,121,121,27,90,144,18,110,176,22,127,204,25,67,108,13,171,90,116,209,110,142,242,127,165,128,67,87,54,54,54,66,66,66,76,76,76,40,40,40,108,108,108,132,132,132,153,153,153,81,81,81,54,90,108,66,110,132,76,127,153,40,67,81,90,44,126,110,54,154,127,63,178,67,33,94,36,54,126,44,66,154,51,76,178,27,40,94,72,54,36,88,66,44,102,76,51,54,40,27,72,90,36,88,110,44,102,127,51,54,67,27,108,36,36,132,44,44,153,51,51,81,27,27,18,18,18,22,22,22,25,25,25,13,13,13,176,168,54,216,205,66,250,238,77,132,126,41,65,155,150,79,189,184,92,219,213,49,116,113,52,90,180,64,110,220,74,128,255,39,68,135,0,153,41,0,187,50,0,217,58,0,115,31,91,61,35,111,74,42,129,86,49,68,46,26,79,1,0,97,2,0,112,2,0,59,1,0,    ]

    def __init__(self):
        super().__init__("RGB",self.palette_1_12,len(self.palette_1_12))


class Map:
    def __init__(self, filename):
        stem = PurePath(filename).stem
        m = map_id_re.match(stem)
        self.id = int(m.group(1)) if m else None
        self.nbtfile = nbt.NBTFile(filename)
        self.center = (int(self.nbtfile["data"]["xCenter"].value), int(self.nbtfile["data"]["zCenter"].value))
        self.scale = int(self.nbtfile["data"]["scale"].value)

    def extract_image(self):
        colors = bytes(self.nbtfile["data"]["colors"].value)
        result = Image.frombytes("P", (128, 128), colors)
        result.putpalette(MinecraftPalette().tobytes())
        return result

    @property
    def rect(self):
        side = SIDE_LEN[self.scale]
        x, z = self.center
        l = x - side // 2
        t = z - side // 2
        b = t + side
        r = l + side
        return (l, t, r, b)
    
    def get_megaregion_coords(self):
        return self.get_coords(4)

    def get_coords(self, scale):
        return tuple(c // (SIDE_LEN[scale]) for c in self.center)

    def direction_from(self, other_center):
        x, z = self.center
        x_from, z_from = other_center
        ns = 0 if x_from > x else 2
        we = 0 if z_from > z else 1
        return Direction(ns + we)
   
    def __repr__(self):
        return "Map(id={}, scale={}, center={}, coords={})".format(self.id, self.scale, self.center, self.get_coords(self.scale))


class MapTree:
    def __init__(self, center, scale):
        self.center = center
        self.scale = scale
        self.elt = None
        if scale > 0:
            self.children = {}
        else:
            self.children = {}

    def add(self, elt):
        if self.scale == elt.scale:
            self.elt = elt
        elif self.scale > elt.scale:
            d = elt.direction_from(self.center)
            self.children[d] = MapTree(sub_center(d, self.center, self.scale), self.scale - 1)
            self.children[d].add(elt)
        else:
            raise Exception("how we got here?")

    def __repr__(self):
        return "MapTree({!r}, children<{}>)".format(self.elt, list(self.children.items()))


class Atlas():
    """
    Atlas stores minecraft maps in megaregions
    megaregion is size of a biggest map scale: 128x128 chunks
    """
    def __init__(self):
        self.megaregions = {}

    def add(self, m):
        self.megaregions[m.get_megaregion_coords()] = MapTree(m.get_megaregion_coords(), 4)
        self.megaregions[m.get_megaregion_coords()].add(m)

    def update(self, *maps):
        for m in maps:
            self.add(m)

    def get_top_left(self):
        x, z = tuple(zip(*self.megaregions.keys()))
        return (min(x), min(z))

    def get_dimension(self):
        x, z = tuple(zip(*self.megaregions.keys()))
        return (abs(max(x) - min(x)) , abs(max(z) - min(z)))

    def get_maps_by_scale(self):
        result = defaultdict(list)
        queue = list(self.megaregions.values())
        while len(queue) != 0:
            mt = queue.pop()
            if mt.elt:
                result[mt.scale].append(mt.elt)
            print(list(mt.children.values()))
            queue.extend(list(mt.children.values()))
        return result

        

    def __repr__(self):
        return "Atlas(dim=<{}>)".format(self.get_dimension())


def load_maps(paths):
    return [Map(p) for p in paths]


def sub_center(direction, center, scale):
    x, z = center
    o = SIDE_LEN[scale] // 2
    if Direction.NW:
        return (x - o, z - o)
    elif Direction.NE:
        return (x - o, z + o)
    elif Direction.SW:
        return (x + o, z - o)
    elif Direction.SE:
        return (x + o, z + o)


def coords_to_center(coords, scale):
    return tuple(c * SIDE_LEN[scale] + SIDE_LEN[scale] // 2 for c in coords)


def render_by_zoom(atlas, path):
    by_scale = atlas.get_maps_by_scale()
    path = Path(path)
    for s, maps in by_scale.items():
        zoom_path = path.joinpath(str(4 - s))
        if not zoom_path.exists():
            zoom_path.mkdir()
        for m in maps:
            x, z = m.get_coords(s)
            file_path = zoom_path.joinpath(str(x))
            if not file_path.exists():
                file_path.mkdir()
            file_path = file_path.joinpath(str(z) + ".png")
            print(file_path)
            m.extract_image().resize((256,256),Image.NEAREST).save(file_path, "PNG")



