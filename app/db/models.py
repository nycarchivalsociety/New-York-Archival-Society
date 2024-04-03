# SQL statements to create tables
create_tables_sql = """
BEGIN;

CREATE TABLE IF NOT EXISTS donors (
    donor_id UUID PRIMARY KEY,
    donor_name VARCHAR(255),
    donor_lastname VARCHAR(255),
    donor_email VARCHAR(255),
    donor_phone VARCHAR(255),
    created_at TIMESTAMPTZ,
    donated_amount FLOAT4,
    donor_zip_code INT
);

CREATE TABLE IF NOT EXISTS items (
    item_id UUID PRIMARY KEY,
    item_name VARCHAR(255),
    item_description VARCHAR(255),
    created_at TIMESTAMPTZ,
    photo BOOLEAN,
    item_img_url VARCHAR(255),
    fee FLOAT4,
    adopted BOOLEAN,
    adoption_date TIMESTAMPTZ,
    total_donated_minus_remaining FLOAT4,
    remaining_balance FLOAT4,
    item_img_alt VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS item_donors (
    item_id UUID REFERENCES items(item_id),
    donor_id UUID REFERENCES donors(donor_id),
    adoption_date TIMESTAMPTZ,
    PRIMARY KEY (item_id, donor_id)
);

COMMIT;
"""
