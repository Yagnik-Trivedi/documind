-- Runs once, when the Postgres volume is first created.
-- A separate database for the end-to-end tests (its schema is wiped on every test run).
CREATE DATABASE documind_test;
