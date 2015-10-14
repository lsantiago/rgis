# -*- coding: utf-8 -*-

from rivergis import river_database as rdb
from rivergis import hecobjects as heco

# UWAGA: W QGIS odpal wtyczkę RiverGIS i zaznacz warstwe z przebiegiem rzeki !
# Warstwa oprócz geometrii może miec wypełnione wszystkie pozostałe atrybuty.

# odwołanie do wtyczki
rgis = qgis.utils.plugins['rivergis'].dlg
# biezaca warstwa do importu
s = iface.activeLayer()

# utworzenie bazy
baza = rdb.RiverDatabase(rgis, 'rivergis', 'localhost', '5432', 'postgres', 'pass')
baza.SCHEMA = 'start'
baza.SRID = 2180
baza.connect_pg()
# utworzenie w bazie funkcji tworzacej indeks przestrzenny, jesli nie istnieje
baza.create_spatial_index()

baza.register_existing(heco)
sc = baza.process_hecobject(heco.StreamCenterlines, 'pg_create_table')
xs = baza.process_hecobject(heco.XSCutLines, 'pg_create_table')
bl = baza.process_hecobject(heco.BankLines, 'pg_create_table')
la = baza.process_hecobject(heco.LeveeAlignment, 'pg_create_table')
fp = baza.process_hecobject(heco.Flowpaths, 'pg_create_table')
lu = baza.process_hecobject(heco.LanduseAreas, 'pg_create_table')

baza.add_to_view(sc)
baza.add_to_view(xs)
baza.add_to_view(bl)
baza.add_to_view(la)
baza.add_to_view(fp)
baza.add_to_view(lu)

baza.insert_layer(s, sc)
iface.mapCanvas().refresh()

# Próbkowanie rastra punktami.
rgis = qgis.utils.plugins['rivergis'].dlg

qry = '''
SELECT
  pts."PtID" AS "PtID",
  ST_X(pts.geom) AS x,
  ST_Y(pts.geom) AS y
FROM
  "Pasleka"."SASurface" AS pts
'''

rlayer = QgsMapLayerRegistry.instance().mapLayers().values()[0]
pts = rgis.rdb.run_query(qry, fetch=True, arraysize=100)
qry = ''
for pt in pts:
    ident = rlayer.dataProvider().identify(QgsPoint(pt[1], pt[2]), QgsRaster.IdentifyFormatValue)
    if ident.isValid():
        pt.append(round(ident.results()[1], 2))
        qry += 'UPDATE "Pasleka"."SASurface" SET "Elevation" = {1} WHERE "PtID" = {2};\n'.format(rgis.rdb.SCHEMA, pt[3], pt[0])
    else:
        pass
rgis.rdb.run_query(qry)
