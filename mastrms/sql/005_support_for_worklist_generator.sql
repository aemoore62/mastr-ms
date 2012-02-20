BEGIN;

CREATE TABLE "repository_componentgroup" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(50) NOT NULL
);

INSERT INTO repository_componentgroup("id", "name")
VALUES 
    (1, 'Sample'),
    (2, 'Standard'),
    (3, 'Blank');
ALTER SEQUENCE "repository_componentgroup_id_seq" RESTART WITH 4;

CREATE TABLE "repository_component" (
    "id" serial NOT NULL PRIMARY KEY,
    "sample_type" varchar(255) NOT NULL,
    "sample_code" varchar(255) NOT NULL,
    "filename_prefix" varchar(50) NOT NULL,
    "component_group_id" integer NOT NULL REFERENCES "repository_componentgroup" ("id") DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO repository_component(id, sample_type, sample_code, filename_prefix, component_group_id)
VALUES 
    (0, 'Sample', 'Smp', 'sample', 1),
    (1, 'Pure Standard', 'Std', 'standard', 2),
    (2, 'Pooled Biological QC', 'pbqc', 'pbqc', 1),
    (3, 'Instrument QC', 'iqc', 'iqc', 1),
    (4, 'Solvent Blank', 'SB', 'solvent', 3),
    (5, 'Reagent Blank', 'RB', 'reagent', 3),
    (6, 'Sweep', 'Sweep', 'sweep', 3)
;
ALTER SEQUENCE repository_component_id_seq RESTART WITH 7;

-- Change Run Samples to point to Components instead of the having just a type as before
-- The types will be copied over to component_id (we made sure that the type values match the ids inserted above)
ALTER TABLE "repository_run_samples" ADD COLUMN "component_id" integer;
ALTER TABLE "repository_run_samples" ADD CONSTRAINT "component_id_refs_id_ec749b79" FOREIGN KEY ("component_id") REFERENCES "repository_component" ("id") DEFERRABLE INITIALLY DEFERRED;

UPDATE repository_run_samples SET
    component_id = "type";


CREATE TABLE "repository_rulegenerator" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(255) NOT NULL,
    "description" varchar(1000) NOT NULL,
    "state" integer CHECK ("state" >= 0) NOT NULL,
    "accessibility" integer CHECK ("accessibility" >= 0) NOT NULL,
    "version" integer CHECK ("version" >= 0),
    "previous_version_id" integer,
    "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "created_on" timestamp with time zone NOT NULL
);
ALTER TABLE "repository_rulegenerator" ADD CONSTRAINT "previous_version_id_refs_id_dcab1275" FOREIGN KEY ("previous_version_id") REFERENCES "repository_rulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE "repository_runrulegenerator" (
    "id" serial NOT NULL PRIMARY KEY,
    "rule_generator_id" integer NOT NULL REFERENCES "repository_rulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED,
    "number_of_methods" integer NOT NULL,
    "order_of_methods" integer
);

ALTER TABLE "repository_run" ADD COLUMN "rule_generator_id" integer;
ALTER TABLE "repository_run" ADD CONSTRAINT "rule_generator_id_refs_id_e064e1f3" FOREIGN KEY ("rule_generator_id") REFERENCES "repository_runrulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED;

-- Setting up the Default Rule Generator and pointing all existing Runs to it
INSERT INTO repository_rulegenerator(id, name, description, state, accessibility, created_by_id, created_on)
SELECT 1, 'Default', 'Default Rule Generator converted from the the current version of MAstr-MS', 2, 3, id, now() FROM auth_user where username = 'tszabo@ccg.murdoch.edu.au'; 
ALTER SEQUENCE "repository_rulegenerator_id_seq" RESTART WITH 2;

INSERT INTO repository_runrulegenerator(id, rule_generator_id, number_of_methods)
VALUES (1, 1, 1);
UPDATE repository_run SET rule_generator_id = 1;
ALTER SEQUENCE "repository_runrulegenerator_id_seq" RESTART WITH 2;

CREATE TABLE "repository_rulegeneratorstartblock" (
    "id" serial NOT NULL PRIMARY KEY,
    "rule_generator_id" integer NOT NULL REFERENCES "repository_rulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED,
    "index" integer CHECK ("index" >= 0) NOT NULL,
    "count" integer CHECK ("count" >= 0) NOT NULL,
    "component_id" integer NOT NULL REFERENCES "repository_component" ("id") DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO "repository_rulegeneratorstartblock" (id, rule_generator_id, index, count, component_id)
VALUES 
    (1, 1, 1, 1, 4), -- add 1 Solvent
    (2, 1, 2, 1, 5), -- add 1 Reagent Blank
    (3, 1, 3, 1, 3), -- add 1 IQC
    (4, 1, 4, 1, 2)  -- add 1 PBQC
;
ALTER SEQUENCE "repository_rulegeneratorstartblock_id_seq" RESTART WITH 5;


CREATE TABLE "repository_rulegeneratorsampleblock" (
    "id" serial NOT NULL PRIMARY KEY,
    "rule_generator_id" integer NOT NULL REFERENCES "repository_rulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED,
    "index" integer CHECK ("index" >= 0) NOT NULL,
    "sample_count" integer CHECK ("sample_count" >= 0) NOT NULL,
    "count" integer CHECK ("count" >= 0) NOT NULL,
    "component_id" integer NOT NULL REFERENCES "repository_component" ("id") DEFERRABLE INITIALLY DEFERRED,
    "order" integer CHECK ("order" >= 0) NOT NULL
);
INSERT INTO "repository_rulegeneratorsampleblock" (id, rule_generator_id, index, sample_count, count, component_id, "order")
VALUES 
    (1, 1, 1, 20, 1, 2, 1), -- add 1 PQBC for every 20 samples in random order
    (2, 1, 1, 20, 1, 4, 2)  -- add 1 Solvent for every 20 samples in position
;
ALTER SEQUENCE "repository_rulegeneratorsampleblock_id_seq" RESTART WITH 4;


CREATE TABLE "repository_rulegeneratorendblock" (
    "id" serial NOT NULL PRIMARY KEY,
    "rule_generator_id" integer NOT NULL REFERENCES "repository_rulegenerator" ("id") DEFERRABLE INITIALLY DEFERRED,
    "index" integer CHECK ("index" >= 0) NOT NULL,
    "count" integer CHECK ("count" >= 0) NOT NULL,
    "component_id" integer NOT NULL REFERENCES "repository_component" ("id") DEFERRABLE INITIALLY DEFERRED
);

INSERT INTO "repository_rulegeneratorendblock" (id, rule_generator_id, index, count, component_id)
VALUES 
    (1, 1, 1, 1, 2), -- add 1 PQBC
    (2, 1, 2, 1, 3), -- add 1 IQC
    (3, 1, 3, 2, 4)  -- add 2 Solvent
;
ALTER SEQUENCE "repository_rulegeneratorendblock_id_seq" RESTART WITH 4;

-- Standards class functionality replaced by Standard Component
ALTER TABLE "repository_sampleclass" DROP COLUMN is_standards_class;

-- The Mako template is currently stored in the DB on Instrument Method
-- We have to change it, because it should refer to run_sample.filename not run_sample.run_filename() as before
UPDATE repository_instrumentmethod
SET template = E'## -*- coding: utf-8 -*-\n% for a in runsamples:\n${username},${run.machine.default_data_path},${a.filename},${run.method.method_path},${run.method.method_name},${a.sample_name}\n% endfor'
WHERE title = 'Default Method'; 

COMMIT;

BEGIN;

-- Now having the values, we can make the FKs not null
-- We have to do this in a new transaction because the update of repository_run_samples prevents the table to be altered
ALTER TABLE repository_run_samples ALTER COLUMN "component_id" SET NOT NULL;
ALTER TABLE repository_run ALTER COLUMN "rule_generator_id" SET NOT NULL;

-- We do this last in this transaction - we have to make sure we don't lose any data
-- If the first transaction above failed there will be no component_id so this transaction had to fail before reaching this statement
-- If the first transaction worked type had to be migrated into component_id
ALTER TABLE repository_run_samples DROP COLUMN "type";

COMMIT;