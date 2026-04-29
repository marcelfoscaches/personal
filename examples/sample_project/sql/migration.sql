CREATE TABLE cliente (
  cnpj numeric(14,0)
);
ALTER TABLE cliente ADD CONSTRAINT ck_cnpj CHECK (length(cnpj)=14);
