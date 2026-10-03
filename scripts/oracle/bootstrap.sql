-- Creates the schema used by the adaptive-agent project.
-- Connect straight to the PDB service, not the CDB root:
--   sqlplus "sys/<pw>@localhost:1521/FREEPDB1 as sysdba" @scripts/oracle/bootstrap.sql

SET ECHO ON
WHENEVER SQLERROR CONTINUE

-- No password is stored in this file - it is committed, so anything written here
-- would be public. SQL*Plus prompts for one instead, and HIDE keeps it off the
-- screen while you type. VERIFY OFF stops the substituted line being echoed back.
--
-- Use the same value for ORACLE_PASSWORD in your .env (which is gitignored). That
-- is where src/memory/agent_memory.py and scripts/check_env.py read it from, so
-- the two have to match or the connection will fail with ORA-01017.
SET VERIFY OFF
ACCEPT adaptive_pw CHAR PROMPT 'Password for the new ADAPTIVE user: ' HIDE

CREATE USER adaptive IDENTIFIED BY "&adaptive_pw" QUOTA UNLIMITED ON USERS;
GRANT DB_DEVELOPER_ROLE TO adaptive;

-- DB_DEVELOPER_ROLE may already carry this; the grant is harmless if so.
GRANT CREATE PROPERTY GRAPH TO adaptive;

-- Agent Memory builds its own tables in this schema on first use
-- (SchemaPolicy.CREATE_IF_NECESSARY), so there is no DDL for it here.

SELECT username, account_status FROM dba_users WHERE username = 'ADAPTIVE';
SELECT sys_context('userenv', 'con_name') AS container FROM dual;
EXIT
