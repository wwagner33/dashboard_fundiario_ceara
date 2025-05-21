import geopandas as gpd

# Caminho do seu GeoJSON
geojson_path = "../data/geojson-municipios_ceara-normalizado.geojson"
# Pasta onde o Shapefile será salvo (ela será criada se não existir)
shapefile_dir = "../data/municipios_ceara_shp"

# Lê o GeoJSON
gdf = gpd.read_file(geojson_path)

# Salva como Shapefile
gdf.to_file(shapefile_dir, driver="ESRI Shapefile")

print("Shapefile salvo em:", shapefile_dir)
