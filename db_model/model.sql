-- Table Creation for Access Control and Schema

-- Patient Table
CREATE TABLE PATIENT (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    DNI VARCHAR(20),
    gender ENUM('M', 'F', 'Other'),
    age INT,
    phone VARCHAR(15),
    email VARCHAR(100),
    cancer_id INT,
    FOREIGN KEY (cancer_id) REFERENCES CANCER_TYPE(cancer_id)
);

-- Cancer Type Table
CREATE TABLE CANCER_TYPE (
    cancer_id INT AUTO_INCREMENT PRIMARY KEY,
    cancer_type VARCHAR(50) NOT NULL
);

-- VCF Entry Table
CREATE TABLE VCF_ENTRY (
    vcf_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    path VARCHAR(255) NOT NULL COMMENT 'web server',
    upload_date DATE,
    processed BOOLEAN,
    delete_date DATE NULL,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id)
);

-- Gene Table
CREATE TABLE GENE (
    gene_id INT AUTO_INCREMENT PRIMARY KEY,
    gene_symbol VARCHAR(50),
    gene_name VARCHAR(50),
    location VARCHAR(50),
	role_in_cancer VARCHAR(50)
);

-- Variant Table
CREATE TABLE VARIANT (
    variant_id INT AUTO_INCREMENT PRIMARY KEY,
    variant_type VARCHAR(50),
    change_id VARCHAR(100),
    gene_id INT NOT NULL,
    FOREIGN KEY (gene_id) REFERENCES GENE(gene_id)
);

-- Patient Has Variant Table
CREATE TABLE PATIENT_HAS_VARIANT (
    patient_id INT,
    variant_id INT,
    PRIMARY KEY (patient_id, variant_id),
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id),
    FOREIGN KEY (variant_id) REFERENCES VARIANT(variant_id)
);

-- Gene and Variant Association with Drug Table
CREATE TABLE DRUG_ASSOCIATION (
    association_id INT AUTO_INCREMENT PRIMARY KEY,
    gene_id INT,
    variant_id INT,
    drug_id INT,
    cancer_id INT,
    response ENUM('resistance', 'treatment'),
    source ENUM('Source1', 'Source2', 'Source3'),
    reference TEXT,
    FOREIGN KEY (variant_id) REFERENCES VARIANT(variant_id),
    FOREIGN KEY (drug_id) REFERENCES DRUG(drug_id),
    FOREIGN KEY (cancer_id) REFERENCES CANCER_TYPE(cancer_id)
);

-- Drug Table
CREATE TABLE DRUG (
    drug_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100)
);

-- Patient Treated With Drug Table
CREATE TABLE PATIENT_TREATED_WITH_DRUG (
    patient_id INT,
    drug_id INT,
    PRIMARY KEY (patient_id, drug_id),
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id),
    FOREIGN KEY (drug_id) REFERENCES DRUG(drug_id)
);

-- Personnel Attend to Patient Table
CREATE TABLE PERSONNEL_ATTEND_TO_PATIENT (
    patient_id INT,
    personnel_id INT,
    PRIMARY KEY (patient_id, personnel_id),
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id),
    FOREIGN KEY (personnel_id) REFERENCES HEALTHCARE_PERSONNEL(personnel_id)
);


-- Roles Table
CREATE TABLE ROLE (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    privileges VARCHAR(100) NOT NULL
);

-- Healthcare Personnel Table
CREATE TABLE HEALTHCARE_PERSONNEL (
    personnel_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100),
    role_id INT,
    FOREIGN KEY (role_id) REFERENCES ROLE(role_id)
);

-- Login Table
CREATE TABLE LOGIN (
    email VARCHAR(100) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL,
    personnel_id INT,
    FOREIGN KEY (personnel_id) REFERENCES HEALTHCARE_PERSONNEL(personnel_id)
);

-- Access Control Insertions

-- Add Roles
INSERT INTO ROLE (name, description) VALUES ('Doctor', 'Access to all data and edit privileges');
INSERT INTO ROLE (name, description) VALUES ('Nurse', 'Access to treatment-related data only');

-- Add Privileges
INSERT INTO PRIVILEGES (name, description) VALUES ('View_Patient', 'View patient information');
INSERT INTO PRIVILEGES (name, description) VALUES ('Edit_Patient', 'Edit patient information');
INSERT INTO PRIVILEGES (name, description) VALUES ('View_Treatment', 'View treatment details');

-- Assign Privileges to Roles
INSERT INTO ROLE_HAS_PRIVILEGES (role_id, privilege_id) VALUES (1, 1); -- Doctor can view patient
INSERT INTO ROLE_HAS_PRIVILEGES (role_id, privilege_id) VALUES (1, 2); -- Doctor can edit patient
INSERT INTO ROLE_HAS_PRIVILEGES (role_id, privilege_id) VALUES (2, 3); -- Nurse can view treatment
