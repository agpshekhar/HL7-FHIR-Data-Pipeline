--staging: the pipeline's own working tables, kept separate from OMOP
CREATE SCHEMA staging;

--holds every HL7 message that was accepted by the pipeline, exactly as arrived
--MSH-10 is the unique identifier for each message, and is used to link the raw message to any FHIR resources that were created from it
CREATE TABLE staging.raw_message (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    msh10 text NOT NULL UNIQUE,
    message_type text NOT NULL,
    raw text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'parsed', 'error')),
    status_detail text,
    processed_at timestamptz
);

--hop 1 picks up work with WHERE status = 'new', so we want to make that fast
CREATE INDEX raw_message_new_idx ON staging.raw_message (status) WHERE status = 'new';


--messages the interface engine rejected, with the NAK code and reason for rejection.  This is used to generate the error queue report.
--MSH-10 may be missing or invalid, so we don't require it to be unique or even present.  The raw message is stored for debugging purposes.
CREATE TABLE staging.error_queue (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    msh10 text,
    raw text NOT NULL,
    ack_code text NOT NULL CHECK (ack_code IN ('AE', 'AR')),
    reason text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now()
    );


--hop 1 output: one row per FHIR resource created from a raw message.  The resource is stored as JSONB, and the MSH-10 of the raw message that created it is stored for traceability.
CREATE TABLE staging.fhir_resource (
    resource_type text NOT NULL,
    id uuid NOT NULL,
    resource jsonb NOT NULL,
    source_msh10 text NOT NULL
        REFERENCES staging.raw_message (msh10) DEFERRABLE INITIALLY DEFERRED,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (resource_type, id)
);


-- Hop 2 memory: which OMOP row each FHIR resource became. Hop 2 rebuilds the CDM tables
-- every run, but this table survives, so the same resource always gets the same OMOP ID.
CREATE TABLE staging.crosswalk (
    fhir_resource_type text NOT NULL,
    fhir_id uuid NOT NULL,
    omop_table text NOT NULL,
    omop_id integer GENERATED ALWAYS AS IDENTITY UNIQUE,
    PRIMARY KEY (fhir_resource_type, fhir_id)
);
