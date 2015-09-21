# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : RiverGIS
Description          : HEC-RAS tools for QGIS
Date                 : January, 2015
copyright            : (C) 2015 by RiverGIS Group
email                : rpasiok@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
""" 
import hecobjects as heco
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsDataSourceURI

def ras1dStreamCenterlineTopology(rgis):
    """Creates river network topology. Creates nodes at reach ends and finds the direction of flow (fromNode, toNode)"""
    # check if streamlines table is registered
    scExist = 'StreamCenterlines' in rgis.rdb.register.keys()
    if not scExist:
        rgis.addInfo('<br>StreamCenterlines are not registered in the river database. Cancelling...')
        return

    rgis.addInfo('<br><b>Building topology on StreamCenterlines...</b>')
    if rgis.rdb.process_hecobject(heco.StreamCenterlines, 'pg_topology'):
        rgis.addInfo('Done.')


def ras1dStreamCenterlineLengthsStations(rgis):
    """Calculate river reaches lenght and their endpoints stations"""
    ntExist = 'NodesTable' in [t[0] for t in rgis.rdb.list_tables()]
    if not ntExist:
        rgis.addInfo('<br>NodesTable is not registered in the river database.<br>Build StreamCenterlines Topology first.<br>Cancelling...')
        qry = ''
    rgis.addInfo('<br><b>Calculating river reach(es) lenghts and their end stations...</b>')
    if rgis.rdb.process_hecobject(heco.StreamCenterlines, 'pg_lengths_stations'):
        rgis.addInfo('Done.')


def ras1dStreamCenterlineAll(rgis):
    """Runs all analyses for rivers' centerlines, i.e. topology + Lengths/stations"""
    ras1dStreamCenterlineTopology(rgis)
    ras1dStreamCenterlineLengthsStations(rgis)


def ras1dXSRiverReachNames(rgis):
    """Finds river and reach name for each cross-section"""
    # check if streamlines  and xsec tables are registered
    scExist = 'StreamCenterlines' in rgis.rdb.register.keys()
    xsExist = 'XSCutLines' in rgis.rdb.register.keys()
    if not scExist or not xsExist:
        rgis.addInfo('<br>StreamCenterlines or XSCutLines table is not registered in the river database. Cancelling...')
        return
    rgis.addInfo('<br><b>Setting river and reach names for each cross-section...</b>')
    if rgis.rdb.process_hecobject(heco.XSCutLines, 'pg_river_reach_names'):
        rgis.addInfo('Done.')


def ras1dXSStationing(rgis):
    """Finds cross-sections' stationing (chainages) along its river reach"""
    rgis.addInfo('<br><b>Calculating cross-sections\' stationing...</b>')
    if rgis.rdb.process_hecobject(heco.XSCutLines, 'pg_stationing'):
        rgis.addInfo('Done.')


def ras1dXSBankStations(rgis):
    """Find banks stations for each cross-section. Based on intersection of banks and xs lines"""
    rgis.addInfo('<br><b>Calculating cross-sections\' banks stations...</b>')
    if rgis.rdb.process_hecobject(heco.XSCutLines, 'pg_bank_stations'):
        rgis.addInfo('Done.')


def ras1dXSDownstreamLengths(rgis):
    """Calculates downstream reach lengths from each cross-section along the 3 flow paths (channel, left and right overbank)"""
    rgis.addInfo('<br><b>Calculating cross-sections\' distances to the next cross-section downstream ...</b>')
    # check the flowpaths line type if not empty
    qry = 'SELECT "LineType" FROM "{0}"."Flowpaths";'.format(rgis.rdb.SCHEMA)
    lineTypes = rgis.rdb.run_query(qry, fetch=True)
    for row in lineTypes:
        if row[0].lower() not in ['channel', 'right', 'left', 'c', 'l', 'r']:
            rgis.addInfo('Check the Flowpaths LineType attribute values - it should be one of: Channel, Right, Left, C, L, or r')
            return
    if rgis.rdb.process_hecobject(heco.XSCutLines, 'pg_downstream_reach_lengths'):
        rgis.addInfo('Done.')


def ras1dXSElevations(rgis):
    """Probe a DTM to find cross-section vertical shape"""
    rgis.addInfo('<br><b>Interpolating cross-sections\' points ...</b>')
    # Create xsection points table
    qry = '''
    DROP TABLE IF EXISTS "{0}"."XSPoints";
    CREATE TABLE "{0}"."XSPoints" (
    "PtID" bigserial primary key,
    "XsecID" integer,
    "Station" double precision,
    "Elevation" double precision,
    "CoverCode" text,
    "SrcId" integer,
    "Notes" text,
    geom geometry(Point, {1})
    );
    '''.format(rgis.rdb.SCHEMA, rgis.rdb.SRID)
    rgis.rdb.run_query(qry)

    # Create DTMs table
    qry = '''
    DROP TABLE IF EXISTS "{0}"."DTMs";
    CREATE TABLE "{0}"."DTMs" (
    "DtmID" bigserial primary key,
    "Name" text,
    "DtmUri" text,
    "Provider" text,
    "LayerID" text,
    "CellSize" double precision,
    geom geometry(Polygon, {1})
    );
    '''.format(rgis.rdb.SCHEMA, rgis.rdb.SRID)
    rgis.rdb.run_query(qry)

    # insert DTMs parameters into the DTMs table
    dtmsParams = []
    for layerId in rgis.dtms:
        rlayer = rgis.mapRegistry.mapLayer(layerId)
        name = '\'{0}\''.format(rlayer.name())
        uri = '\'{0}\''.format(rlayer.dataProvider().dataSourceUri())
        dp = '\'{0}\''.format(rlayer.dataProvider().name())
        lid = '\'{0}\''.format(rlayer.id())
        pixelSize = min(rlayer.rasterUnitsPerPixelX(), rlayer.rasterUnitsPerPixelY())
        bboxWkt = rlayer.extent().asWktPolygon()
        geom = 'ST_GeomFromText(\'{0}\', {1})'.format(bboxWkt, rgis.rdb.SRID)
        params = '({0})'.format(',\n'.join([name, uri, dp, lid, str(pixelSize), geom]))
        dtmsParams.append(params)
    qry = '''
        INSERT INTO "{0}"."DTMs" ("Name","DtmUri", "Provider", "LayerID", "CellSize", geom) VALUES \n  {1};
    '''.format(rgis.rdb.SCHEMA, '{0}'.format(',\n'.join(dtmsParams)))
    rgis.rdb.run_query(qry)

    # get the smallest cell size DTM covering each xsection
    qry = '''
    WITH data AS (
    SELECT DISTINCT ON (xs."XsecID")
      xs."XsecID" as "XsecID",
      dtm."DtmID" as "DtmID",
      dtm."CellSize" as "CellSize"
    FROM
      "{0}"."XSCutLines" as xs,
      "{0}"."DTMs" as dtm
    WHERE
      xs.geom && dtm.geom AND
      ST_Contains(dtm.geom, xs.geom)
    ORDER BY xs."XsecID", dtm."CellSize" ASC)
    UPDATE "{0}"."XSCutLines" as xs
    SET
      "DtmID" = data."DtmID"
    FROM data
    WHERE
      data."XsecID" = xs."XsecID";
    SELECT "XsecID", "DtmID"
    FROM "{0}"."XSCutLines";
    '''.format(rgis.rdb.SCHEMA)
    rgis.rdb.run_query(qry)

    # insert xs points along each xsection
    qry = '''
    WITH line AS
      (SELECT
        xs."XsecID" as "XsecID",
        dtm."CellSize" as "CellSize",
        (ST_Dump(xs.geom)).geom AS geom
      FROM
        "{0}"."XSCutLines" as xs,
        "{0}"."DTMs" as dtm
      WHERE
        xs."DtmID" = dtm."DtmID"),
    linemeasure AS
      (SELECT
        "XsecID",
        ST_AddMeasure(line.geom, 0, ST_Length(line.geom)) AS linem,
        generate_series(0, (ST_Length(line.geom)*100)::int, (line."CellSize"*100)::int) AS "Station"
      FROM line),
    geometries AS (
      SELECT
        "XsecID",
        "Station",
        (ST_Dump(ST_GeometryN(ST_LocateAlong(linem, "Station"/100), 1))).geom AS geom
      FROM linemeasure)

    INSERT INTO "{0}"."XSPoints" ("XsecID", "Station", geom)
    SELECT
      "XsecID",
      "Station",
      ST_SetSRID(ST_MakePoint(ST_X(geom), ST_Y(geom)), {1}) AS geom
    FROM geometries;

    INSERT INTO "{0}"."XSPoints" ("XsecID", "Station", geom)
    SELECT
      "XsecID",
      ST_Length(geom),
      ST_Endpoint(geom)
    FROM "{0}"."XSCutLines";
    '''
    qry = qry.format(rgis.rdb.SCHEMA, rgis.rdb.SRID)
    rgis.rdb.run_query(qry)

    # probe a DTM at each xsection point
    qry = 'SELECT * FROM "{0}"."DTMs";'.format(rgis.rdb.SCHEMA)
    dtms = rgis.rdb.run_query(qry, fetch=True)
    for dtm in dtms:
        dtmId = dtm[0]
        lid = dtm[4]
        cellSize = dtm[5]
        rlayer = rgis.mapRegistry.mapLayer(lid)
        qry = '''
        SELECT "XsecID" FROM "{0}"."XSCutLines" WHERE "DtmID" = {1} ORDER BY "XsecID";
        '''.format(rgis.rdb.SCHEMA, dtmId)
        xsIds = rgis.rdb.run_query(qry, fetch=True)
        xsIdsWhere = '"XsecID" IN ({0})'.format(','.join([str(elem[0]) for elem in xsIds]))
        uri = QgsDataSourceURI()
        uri.setConnection(rgis.rdb.host, rgis.rdb.port, rgis.rdb.dbname, rgis.rdb.user, rgis.rdb.password)
        uri.setDataSource(rgis.rdb.SCHEMA, "XsPoints", "geom", xsIdsWhere)
        pts = QgsVectorLayer(uri.uri(), "XsPoints", "postgres")
        pts.startEditing()
        if rgis.DEBUG:
            rgis.addInfo('Ilosc punktow do interpolacji: {0}'.format(pts.featureCount()))
        for pt in pts.getFeatures():
            geom = pt.geometry()
            ident = rlayer.dataProvider().identify(QgsPoint(geom.asPoint().x(), geom.asPoint().y()), \
                    QgsRaster.IdentifyFormatValue)
            if ident.isValid():
                if rgis.DEBUG:
                    rgis.addInfo('Wartosc rastra w ({1}, {2}): {0}'.format(ident.results()[1], geom.asPoint().x(), geom.asPoint().y()))
                pts.dataProvider().changeAttributeValues({ pt.id() : {3: ident.results()[1]} })
        pts.commitChanges()
    rgis.addInfo('Done')


def ras1dXSAll(rgis):
    """Runs all the XS analyses"""
    pass


