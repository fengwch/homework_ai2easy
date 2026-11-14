-- 数据库初始化脚本（开发/测试环境）
-- 使用前请修改下面的密码。执行: mysql -u root -p < scripts/init-db.sql

-- 创建数据库
CREATE DATABASE IF NOT EXISTS homework_ai2easy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 创建应用用户（允许任意主机，仅适用于开发/测试；生产请按 docs/database-setup.md 限制 HOST）
-- 请将 'ChangeMe123' 改为强密码，并与 configs/config.yaml 中 data.database.source 一致
CREATE USER IF NOT EXISTS 'homework_app'@'%'
  IDENTIFIED BY 'ChangeMe123';

GRANT ALL PRIVILEGES ON homework_ai2easy.* TO 'homework_app'@'%';
FLUSH PRIVILEGES;

-- 表结构由 GORM 自动迁移创建，无需在此建表。
