import json
from pathlib import Path
from glob import glob
from dataclasses import asdict
import atlas

def carto_exporter(carto_folder, world_folder, target_folder):
	carto_folder = Path(carto_folder) 
	world_folder = Path(world_folder) 
	with open(carto_folder / "map_registry.json", "r") as fd:
		map_records = json.load(fd)

	if len(map_records) == 0:
		raise Exception("No map records")

	ids = [m["mapId"] for m in map_records]
	# if len(ids) == 1:
	# 	ids = ids[0]
	p = world_folder / "data" / "map_*.dat"
	map_files = glob(str(p))
	map_files = [f for f in map_files if any(f.split("map_")[1].split(".")[0] == str(id) for id in ids)]
	print(map_files)

	maps = atlas.load_maps(map_files)
	a = atlas.Atlas()
	a.update(maps)
	a.interpolate()
	atlas.render_by_zoom(a, target_folder)

	with open(Path(target_folder) / "banners.json", "w") as fd:
		json.dump([asdict(b) for b in a.banners], fd)



if __name__ == '__main__':
	carto_exporter("/carto_folder" ,"/world_folder", "/target")