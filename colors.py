from dataclasses import dataclass
from math import floor

@dataclass
class Color:
	id: int
	name: str
	r: int
	g: int
	b: int

	@property
	def rgb(self):
		return (self.r, self.g, self.b)

	@property
	def rgba(self):
		if any(c is None for c in self.rgb):
			return (0,) * 4
		else:
			return (*self.rgb, 255)


	
	

C = Color

BASE_COLORS_1_13 = [
	C(0, "AIR", None, None, None),
	C(1, "GRASS", 127, 178, 56),
	C(2, "SAND", 247, 233, 163),
	C(3, "CLOTH", 199, 199, 199),
	C(4, "TNT", 255, 0, 0),
	C(5, "ICE", 160, 160, 255),
	C(6, "IRON", 167, 167, 167),
	C(7, "FOLIAGE", 0, 124, 0),
	C(8, "SNOW", 255, 255, 255),
	C(9, "CLAY", 164, 168, 184),
	C(10, "DIRT", 151, 109, 77),
	C(11, "STONE", 112, 112, 112),
	C(12, "WATER", 64, 64, 255),
	C(13, "WOOD", 143, 119, 72),
	C(14, "QUARTZ", 255, 252, 245),
	C(15, "ADOBE", 216, 127, 51),
	C(16, "MAGENTA", 178, 76, 216),
	C(17, "LIGHT_BLUE", 102, 153, 216),
	C(18, "YELLOW", 229, 229, 51),
	C(19, "LIME", 127, 204, 25),
	C(20, "PINK", 242, 127, 165),
	C(21, "GRAY", 76, 76, 76),
	C(22, "SILVER", 153, 153, 153),
	C(23, "CYAN", 76, 127, 153),
	C(24, "PURPLE", 127, 63, 178),
	C(25, "BLUE", 51, 76, 178),
	C(26, "BROWN", 102, 76, 51),
	C(27, "GREEN", 102, 127, 51),
	C(28, "RED", 153, 51, 51),
	C(29, "BLACK", 25, 25, 25),
	C(30, "GOLD", 250, 238, 77),
	C(31, "DIAMOND", 92, 219, 213),
	C(32, "LAPIS", 74, 128, 255),
	C(33, "EMERALD", 0, 217, 58),
	C(34, "OBSIDIAN", 129, 86, 49),
	C(35, "NETHERRACK", 112, 2, 0),
	C(36, "WHITE_STAINED_HARDENED_CLAY", 209, 177, 161),
	C(37, "ORANGE_STAINED_HARDENED_CLAY", 159, 82, 36),
	C(38, "MAGENTA_STAINED_HARDENED_CLAY", 149, 87, 108),
	C(39, "LIGHT_BLUE_STAINED_HARDENED_CLAY", 112, 108, 138),
	C(40, "YELLOW_STAINED_HARDENED_CLAY", 186, 133, 36),
	C(41, "LIME_STAINED_HARDENED_CLAY", 103, 117, 53),
	C(42, "PINK_STAINED_HARDENED_CLAY", 160, 77, 78),
	C(43, "GRAY_STAINED_HARDENED_CLAY", 57, 41, 35),
	C(44, "SILVER_STAINED_HARDENED_CLAY", 135, 107, 98),
	C(45, "CYAN_STAINED_HARDENED_CLAY", 87, 92, 92),
	C(46, "PURPLE_STAINED_HARDENED_CLAY", 122, 73, 88),
	C(47, "BLUE_STAINED_HARDENED_CLAY", 76, 62, 92),
	C(48, "BROWN_STAINED_HARDENED_CLAY", 76, 50, 35),
	C(49, "GREEN_STAINED_HARDENED_CLAY", 76, 82, 42),
	C(50, "RED_STAINED_HARDENED_CLAY", 142, 60, 46),
	C(51, "BLACK_STAINED_HARDENED_CLAY", 37, 22, 16),
]


def generate_full_palette(base_colors):
	for i, color in enumerate(base_colors):
		assert i == color.id
		rgba = color.rgba
		for m in (180, 220, 255, 135):
			yield (*tuple(floor((c * m) / 255) for c in rgba[:3]), rgba[3])


def extend_list(l, n, pad=0):
    if len(l) >= n:
        return l[:n]
    return l + ((pad,) * (n - len(l)))


FULL_RGBA_COLORS = list(generate_full_palette(BASE_COLORS_1_13))

FULL_RGBA_PALETTE = [c for channel in zip(*FULL_RGBA_COLORS) for c in extend_list(channel, 256)]
# print(FULL_RGBA_PALETTE)