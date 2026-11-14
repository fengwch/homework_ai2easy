-- 为作业内容生成与单题内容生成增加图片/插图生成状态字段
-- GeneratedContent: assignment 级别内容生成状态（assignments.generated_content JSON 内部结构）
-- QuestionGenerationStatus: 单题内容生成状态（question_generation_statuses 表）

-- 1. question_generation_statuses 表增加插图状态与图片地址列表（如已存在则按需调整）
ALTER TABLE `question_generation_statuses`
  ADD COLUMN `image_status` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '图片/插图生成状态：none/pending/processing/completed/failed' AFTER `story_id`,
  ADD COLUMN `image_urls` JSON NULL COMMENT '图片/插图 URL 列表' AFTER `image_status`;

-- 2. story_contents 表增加插图生成进度 illustration_progress（0-100）
ALTER TABLE `story_contents`
  ADD COLUMN `illustration_progress` INT NOT NULL DEFAULT 0 COMMENT '插图生成进度: 0-100' AFTER `illustration_status`;

-- 说明：
-- - assignment 级别的图片状态与图片列表存储在 story_contents.illustration_status 与 story_contents.illustration_images 中，
--   此处仅为单题级别预留扩展字段；若未来需要为单题生成独立插图，可复用上述字段。

