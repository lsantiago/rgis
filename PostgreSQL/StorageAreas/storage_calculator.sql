﻿CREATE OR REPLACE FUNCTION "Pasleka".storage_calculator ()
    RETURNS VOID AS
$BODY$
DECLARE
    c cursor FOR SELECT * FROM "Pasleka"."StorageAreas";
    r "Pasleka"."StorageAreas"%ROWTYPE;
    division integer := 5;
    area double precision := 100;
    emin double precision;
    emax double precision;
    lev double precision;
    h double precision;
BEGIN
    FOR r IN c LOOP
        emin := (SELECT MIN("Elevation") FROM "Pasleka"."SASurface" WHERE "StorageID" = r."StorageID");
        emax := (SELECT MAX("Elevation") FROM "Pasleka"."SASurface" WHERE "StorageID" = r."StorageID");
        lev := emin;
        h := (emax - emin) / division;
        FOR i IN 1..division LOOP
            INSERT INTO "Pasleka"."SALevels" ("StorageID", start_level, end_level, volume)
            SELECT r."StorageID", lev, lev + h, SUM("Elevation")*h FROM "Pasleka"."SASurface" WHERE "StorageID" = r."StorageID" AND "Elevation" BETWEEN lev AND lev + h;
            lev := lev + h;
        END LOOP;
    END LOOP;
END;
$BODY$
    LANGUAGE plpgsql;


DROP TABLE IF EXISTS "Pasleka"."SALevels";
CREATE TABLE "Pasleka"."SALevels"("StorageID" integer, start_level double precision, end_level double precision, volume double precision);
SELECT "Pasleka".storage_calculator ();
