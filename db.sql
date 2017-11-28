-- source db.sql

CREATE DATABASE IF NOT EXISTS tipper;
USE tipper;

CREATE TABLE IF NOT EXISTS users (
  id CHAR(50) NOT NULL PRIMARY KEY,
  name VARCHAR(256),
  addr VARCHAR(50) UNIQUE
  )
ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS transactions (
  from_id CHAR(50),
  to_id CHAR(50),
  state ENUM('new', 'pending', 'accepted', 'declined', 'failed', 'completed'),
  amount FLOAT
  )
ENGINE=InnoDB DEFAULT CHARSET=utf8;
