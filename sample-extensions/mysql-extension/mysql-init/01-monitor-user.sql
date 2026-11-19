-- MySQL init script: creates a read-only monitor user for the extension.
-- Executed automatically by the mysql:8.4 image on first container start.
--
-- caching_sha2_password is the only built-in auth plugin in MySQL 8.4.

CREATE USER IF NOT EXISTS 'monitor'@'%'
    IDENTIFIED WITH caching_sha2_password BY 'monitorpassword';

-- PROCESS is needed for SHOW GLOBAL STATUS
GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'monitor'@'%';

-- Performance schema read access for deep-dive metrics
-- GRANT SELECT ON performance_schema.* TO 'monitor'@'%';

FLUSH PRIVILEGES;
