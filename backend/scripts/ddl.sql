-- ============================================================
-- 作业 AI 助手 - MySQL DDL
-- 说明：项目默认使用 GORM AutoMigrate 自动建表，本脚本供参考或手动部署
-- 执行前请确保数据库已创建（参见 scripts/init-db.sql）
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- users 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `phone` varchar(20) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `nickname` varchar(50) DEFAULT NULL,
  `avatar_url` varchar(500) DEFAULT NULL,
  `wechat_open_id` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `gender` tinyint DEFAULT 0,
  `birthday` date DEFAULT NULL,
  `subscription_level` tinyint DEFAULT 0,
  `subscription_expires_at` datetime DEFAULT NULL,
  `status` tinyint DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_users_phone` (`phone`),
  KEY `idx_users_deleted_at` (`deleted_at`),
  KEY `idx_users_wechat_open_id` (`wechat_open_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- children 儿童档案表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `children` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `name` varchar(50) NOT NULL,
  `nickname` varchar(50) DEFAULT NULL,
  `gender` tinyint DEFAULT 0,
  `birth_date` date DEFAULT NULL,
  `grade` varchar(20) DEFAULT NULL,
  `avatar_url` varchar(500) DEFAULT NULL,
  `interests` json DEFAULT NULL,
  `custom_interests` json DEFAULT NULL,
  `learning_style` varchar(20) DEFAULT NULL,
  `attention_span` int DEFAULT NULL,
  `weak_subjects` json DEFAULT NULL,
  `learning_stats` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_children_user_id` (`user_id`),
  KEY `idx_children_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- assignments 作业表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `child_id` bigint unsigned NOT NULL,
  `subject` varchar(20) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `original_images` json DEFAULT NULL,
  `questions` json NOT NULL,
  `generated_content` json DEFAULT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `estimated_time` int DEFAULT NULL,
  `actual_time` int DEFAULT NULL,
  `score` decimal(5,2) DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_assignments_child_id` (`child_id`),
  KEY `idx_assignments_status` (`status`),
  KEY `idx_assignments_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- story_contents 故事内容表
-- question_id: 单题生成时非空，作业级生成时为空
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `story_contents` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `story_id` varchar(64) NOT NULL,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) DEFAULT NULL COMMENT '单题生成时非空',
  `title` varchar(200) DEFAULT NULL,
  `summary` text,
  `story` longtext NOT NULL,
  `questions` json DEFAULT NULL,
  `theme` varchar(100) DEFAULT NULL,
  `illustration_status` varchar(20) DEFAULT '' COMMENT '插图生成状态: pending|processing|completed|failed',
  `illustration_images` json DEFAULT NULL COMMENT '故事配图 URL 列表',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_story_contents_story_id` (`story_id`),
  KEY `idx_story_contents_assignment_id` (`assignment_id`),
  KEY `idx_story_contents_question_id` (`question_id`),
  KEY `idx_story_contents_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- question_generation_statuses 单题内容生成状态表
-- (assignment_id, question_id) 唯一
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `question_generation_statuses` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `story_id` varchar(64) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assignment_question` (`assignment_id`, `question_id`),
  KEY `idx_question_generation_statuses_status` (`status`),
  KEY `idx_question_generation_statuses_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- question_answers 题目作答记录表
-- (assignment_id, question_id, child_id) 唯一，同题重复提交覆盖
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `question_answers` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) NOT NULL,
  `child_id` bigint unsigned NOT NULL,
  `user_answer` text NOT NULL,
  `is_correct` tinyint(1) DEFAULT NULL COMMENT '有标准答案时为1/0，无标准答案时为NULL',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_assignment_question_child` (`assignment_id`, `question_id`, `child_id`),
  KEY `idx_question_answers_child_id` (`child_id`),
  KEY `idx_question_answers_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 增量迁移（按需执行）
-- ============================================================
-- 1. story_contents 无 question_id 时：
-- ALTER TABLE `story_contents` ADD COLUMN `question_id` varchar(64) DEFAULT NULL COMMENT '单题生成时非空' AFTER `assignment_id`;
-- ALTER TABLE `story_contents` ADD INDEX `idx_story_contents_question_id` (`question_id`);

-- 2. story_contents 无 illustration_images 时（插图功能需要该列）：
-- ALTER TABLE `story_contents` ADD COLUMN `illustration_images` json DEFAULT NULL COMMENT '故事配图 URL 列表' AFTER `theme`;

-- 2.1 story_contents 无 illustration_status 时（插图异步生成状态）：
-- ALTER TABLE `story_contents` ADD COLUMN `illustration_status` varchar(20) DEFAULT '' COMMENT '插图生成状态: pending|processing|completed|failed' AFTER `theme`;
-- 2.2 story_contents 无 illustration_progress 时（插图生成进度，0-100）：
-- ALTER TABLE `story_contents` ADD COLUMN `illustration_progress` int DEFAULT 0 COMMENT '插图生成进度: 0-100' AFTER `illustration_status`;

-- 3. users 无 wechat_open_id 时（微信登录需此列，GORM 列名为 wechat_open_id）：
-- ALTER TABLE `users` ADD COLUMN `wechat_open_id` varchar(100) DEFAULT NULL;
-- ALTER TABLE `users` ADD INDEX `idx_users_wechat_open_id` (`wechat_open_id`);

-- 4. 若误建为 wechat_openid，可重命名：
-- ALTER TABLE `users` CHANGE COLUMN `wechat_openid` `wechat_open_id` varchar(100) DEFAULT NULL;

-- 5. 新增 question_answers 表（答题提交与批改页）：
-- 见上方 CREATE TABLE question_answers，或执行 scripts/ddl.sql 完整脚本

-- 为作业内容生成与单题内容生成增加图片/插图生成状态字段
-- GeneratedContent: assignment 级别内容生成状态（assignments.generated_content JSON 内部结构）
-- QuestionGenerationStatus: 单题内容生成状态（question_generation_statuses 表）

-- 1. question_generation_statuses 表增加插图状态与图片地址列表（如已存在则按需调整）
-- ALTER TABLE `question_generation_statuses`
--   ADD COLUMN `image_status` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '图片/插图生成状态：none/pending/processing/completed/failed' AFTER `story_id`,
--   ADD COLUMN `image_urls` JSON NULL COMMENT '图片/插图 URL 列表' AFTER `image_status`;

-- 说明：
-- - assignment 级别的图片状态与图片列表存储在 story_contents.illustration_status 与 story_contents.illustration_images 中，
--   此处仅为单题级别预留扩展字段；若未来需要为单题生成独立插图，可复用上述字段。

