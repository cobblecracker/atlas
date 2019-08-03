import re
from enum import Enum
from pathlib import PurePath, Path
from nbt import nbt
from PIL import Image
from PIL.ImagePalette import ImagePalette
from collections import defaultdict
from dataclasses import dataclass
import colors

map_id_re = re.compile(r"^map_(\d+)$")

SIDE_LEN = [2 ** (7 + i) for i in range(0, 5)]


class Direction(Enum):
    NW = 0
    NE = 1
    SW = 2
    SE = 3


@dataclass(frozen=True)
class Bounds:
    x: int
    z: int
    scale: int

    def __post_init__(self):
        assert self.x % 8 == 0
        assert self.z % 8 == 0
        assert self.scale >= 0

    def get_coords(self, scale=None):
        if scale is None:
            scale = self.scale
        return ((self.x + 64) // SIDE_LEN[scale], (self.z + 64) // SIDE_LEN[scale])

    def sub_bounds(self, direction):
        if self.scale == 0:
            raise Exception("limit")
        o = SIDE_LEN[self.scale] // 4
        if direction == Direction.NW:
            return Bounds(self.x - o, self.z - o, self.scale - 1)
        elif direction == Direction.NE:
            return Bounds(self.x - o, self.z + o, self.scale - 1)
        elif direction == Direction.SW:
            return Bounds(self.x + o, self.z - o, self.scale - 1)
        elif direction == Direction.SE:
            return Bounds(self.x + o, self.z + o, self.scale - 1)

    def direction_from(self, parent):
        # assert self.scale + 1 == parent.scale
        ns = 0 if parent.x > self.x else 2
        we = 0 if parent.z > self.z else 1
        return Direction(ns + we)

    def contains(self, other):
        print(self, "contains?", other)
        if self.scale < other.scale:
            return False
        l, t, r, b = self.rect
        return l < other.x and r > other.x and t < other.z and b > other.z

    def containing_bounds(self, scale):
        cx, cz = self.get_coords(scale)
        x = cx * SIDE_LEN[scale] + SIDE_LEN[scale] // 2 - 64
        z = cz * SIDE_LEN[scale] + SIDE_LEN[scale] // 2 - 64
        result = Bounds(x, z, scale)
        assert result.contains(self)
        return result

    @property
    def rect(self):
        side = SIDE_LEN[self.scale]
        l = self.x - side // 2
        t = self.z - side // 2
        b = t + side
        r = l + side
        return (l, t, r, b)


CROP_COORDS = {
    Direction.NW: (0, 0, 64, 64),
    Direction.NE: (0, 64, 64, 128),
    Direction.SW: (64, 0, 128, 64),
    Direction.SE: (64, 64, 128, 128),
}


class MinecraftPalette(ImagePalette):
    def __init__(self):
        p = colors.FULL_RGBA_PALETTE
        super().__init__("RGBA", p, len(p))


class AbstractMap:
    @property
    def rect(self):
        side = SIDE_LEN[self.scale]
        x, z = self.center
        l = x - side // 2
        t = z - side // 2
        b = t + side
        r = l + side
        return (l, t, r, b)

    def get_coords(self, scale):
        r = tuple(c // (SIDE_LEN[scale]) for c in self.center)
        print(self.center, r)
        return tuple(c // (SIDE_LEN[scale]) for c in self.center)

    def direction_from(self, other_center):
        x, z = self.center
        x_from, z_from = other_center
        ns = 0 if x_from > x else 2
        we = 0 if z_from > z else 1
        return Direction(ns + we)


class Map(AbstractMap):
    def __init__(self, filename):
        stem = PurePath(filename).stem
        m = map_id_re.match(stem)
        self.id = int(m.group(1)) if m else None
        self.nbtfile = nbt.NBTFile(filename)
        self.bounds = Bounds(
            int(self.nbtfile["data"]["xCenter"].value),
            int(self.nbtfile["data"]["zCenter"].value),
            int(self.nbtfile["data"]["scale"].value),
        )

    def get_image(self):
        colors = bytes(self.nbtfile["data"]["colors"].value)
        result = Image.frombytes("P", (128, 128), colors)
        alpha_layer = bytes(
            bytearray(map(lambda b: 0x00 if b == 0x00 else 0xFF, colors))
        )
        alpha = Image.frombytes("L", (128, 128), alpha_layer)
        result.im.putpalette(*MinecraftPalette().getdata())
        result = result.convert("RGB")
        result.putalpha(alpha)
        return result

    def __repr__(self):
        return "Map(id={}, bounds={})".format(self.id, self.bounds)


class MapView(AbstractMap):
    def __init__(self, bounds, parent):
        self.bounds = bounds
        self.parent = parent

    def get_image(self):
        parent_image = self.parent.get_image()
        direction = self.bounds.direction_from(self.parent.bounds)
        result = parent_image.crop(CROP_COORDS[direction]).resize(
            (128, 128), Image.NEAREST
        )
        # result.show()
        return result

    @classmethod
    def from_direction(cls, direction, parent):
        return cls(
            sub_center(direction, parent.center, parent.scale), parent.scale - 1, parent
        )


class MapStack(AbstractMap):
    def __init__(self, bounds):
        self.bounds = bounds
        self.stack = []

    def get_image(self):
        result = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        images = (m.get_image() for m in reversed(self.stack))
        for im in images:
            result.alpha_composite(im)
        return result

    def add(self, elt):
        assert self.bounds == elt.bounds
        self.stack.append(elt)

    def empty(self):
        return not self.stack

    def __repr__(self):
        return "MapStack(stack<{}>)".format(self.stack)


class MapTree:
    def __init__(self, bounds):
        self.bounds = bounds
        self.stack = MapStack(bounds)
        if bounds.scale > 0:
            self.children = {}
        else:
            self.children = None

    def add(self, elt):
        print()
        print(self, elt)

        # print(self.bounds, elt.bounds)
        if self.bounds == elt.bounds:
            self.stack.add(elt)
        elif self.bounds.contains(elt.bounds):
            d = elt.bounds.direction_from(self.bounds)
            if d not in self.children:
                self.children[d] = MapTree(self.bounds.sub_bounds(d))
            self.children[d].add(elt)
        else:
            raise Exception("how we got here?")

    def interpolate(self):
        if self.children is None:
            return
        for d in Direction:
            # print(d)
            # child_center = sub_center(d, self.center, self.scale)
            if d not in self.children:
                self.children[d] = MapTree(self.bounds.sub_bounds(d))
            self.children[d].add(MapView(self.bounds.sub_bounds(d), self.stack))
            self.children[d].interpolate()

    def __repr__(self):
        if self.children is None:
            return "MapTree({}, {!r})".format(self.bounds, self.stack)
        return "MapTree({}, {!r}, \nchildren<{}>)".format(
            self.bounds, self.stack, list(self.children.items())
        )


class Atlas:
    """
    Atlas stores minecraft maps in megaregions
    megaregion is size of a biggest map scale: 128x128 chunks
    """

    def __init__(self):
        self.megaregions = {}

    def add(self, m):
        print(m)
        if m.bounds.get_coords(4) not in self.megaregions:
            self.megaregions[m.bounds.get_coords(4)] = MapTree(
                m.bounds.containing_bounds(4)
            )
        self.megaregions[m.bounds.get_coords(4)].add(m)

    def update(self, *maps):
        for m in maps:
            self.add(m)

    def get_top_left(self):
        x, z = tuple(zip(*self.megaregions.keys()))
        return (min(x), min(z))

    def get_dimension(self):
        x, z = tuple(zip(*self.megaregions.keys()))
        return (abs(max(x) - min(x)), abs(max(z) - min(z)))

    def get_maps_by_scale(self):
        result = defaultdict(list)
        queue = list(self.megaregions.values())
        while len(queue) != 0:
            mt = queue.pop()
            if mt.stack:
                result[mt.bounds.scale].append(mt.stack)
            # print(list(mt.children.values()))
            if mt.children is not None:
                queue.extend(list(mt.children.values()))
        return result

    def interpolate(self):
        for mt in self.megaregions.values():
            mt.interpolate()

    def __repr__(self):
        return "Atlas(dim=<{}>)".format(self.get_dimension())


def load_maps(paths):
    return [Map(p) for p in paths]


def render_by_zoom(atlas, path):
    by_scale = atlas.get_maps_by_scale()
    path = Path(path)
    for s, maps in by_scale.items():
        zoom_path = path.joinpath(str(4 - s))
        if not zoom_path.exists():
            zoom_path.mkdir()
        for m in maps:
            x, z = m.bounds.get_coords(s)
            file_path = zoom_path.joinpath(str(x))
            if not file_path.exists():
                file_path.mkdir()
            file_path = file_path.joinpath(str(z) + ".png")
            print(file_path)
            m.get_image().resize((256, 256), Image.NEAREST).save(file_path, "PNG")
