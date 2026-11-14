-- MySQL dump 10.13  Distrib 9.6.0, for macos26.2 (arm64)
--
-- Host: 127.0.0.1    Database: smartstudy
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `assignments`
--

DROP TABLE IF EXISTS `assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignments` (
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
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_assignments_status` (`status`),
  KEY `idx_assignments_deleted_at` (`deleted_at`),
  KEY `idx_assignments_child_id` (`child_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignments`
--

LOCK TABLES `assignments` WRITE;
/*!40000 ALTER TABLE `assignments` DISABLE KEYS */;
INSERT INTO `assignments` VALUES (1,7,'','','[\"/uploads/assignments/1/0.jpg\"]','[]',NULL,'pending',0,0,NULL,NULL,'2026-01-30 13:05:16.729','2026-01-30 13:05:16.739',NULL),(2,7,'数学','','[\"/uploads/assignments/2/0.jpg\"]','[{\"id\": \"q1\", \"original_text\": \"1. 下列哪个数是偶数？\\nA. 1  B. 2  C. 3  D. 5\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"下列哪个数是偶数？\", \"answer\": \"B\", \"options\": [{\"text\": \"1\", \"option\": \"A\"}, {\"text\": \"2\", \"option\": \"B\"}, {\"text\": \"3\", \"option\": \"C\"}, {\"text\": \"5\", \"option\": \"D\"}], \"analysis\": \"偶数是能被2整除的数，2÷2=1，所以2是偶数。\"}}]','{\"status\": \"completed\", \"story_id\": \"story-2\"}','completed',30,0,NULL,NULL,'2026-01-30 13:47:09.685','2026-01-30 16:10:12.972',NULL),(3,7,'数学','','[\"/uploads/assignments/3/0.jpg\"]','[{\"id\": \"q1\", \"original_text\": \"1. 下列哪个数是偶数？\\nA. 1  B. 2  C. 3  D. 5\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"下列哪个数是偶数？\", \"answer\": \"B\", \"options\": [{\"text\": \"1\", \"option\": \"A\"}, {\"text\": \"2\", \"option\": \"B\"}, {\"text\": \"3\", \"option\": \"C\"}, {\"text\": \"5\", \"option\": \"D\"}], \"analysis\": \"偶数是能被2整除的数，2÷2=1，所以2是偶数。\"}}]',NULL,'completed',30,0,NULL,NULL,'2026-02-07 23:10:21.639','2026-02-07 23:11:21.689',NULL),(4,7,'数学','','[\"/uploads/assignments/4/0.jpg\"]','[{\"id\": \"q1\", \"original_text\": \"● 写一写 按照图示填写数字。\\n6 - 4 = □\\n6 - □ = □\\n\\n6 - 5 = □\\n6 - □ = □\\n\\n7 - 5 = □\\n7 - □ = □\\n\\n7 - 3 = □\\n□ - □ = □\\n26\", \"question_type\": \"fill_blank\", \"question_number\": 1, \"structured_data\": {\"stem\": \"● 写一写 按照图示填写数字。\\n6 - 4 = □\\n6 - □ = □\\n\\n6 - 5 = □\\n6 - □ = □\\n\\n7 - 5 = □\\n7 - □ = □\\n\\n7 - 3 = □\\n□ - □ = □\\n26\"}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]','{\"status\": \"completed\", \"story_id\": \"story-3ff7c921\"}','completed',30,0,NULL,NULL,'2026-02-07 23:58:36.355','2026-02-08 00:09:46.515',NULL),(5,7,'数学','','[\"/uploads/assignments/5/0.png\"]','[{\"id\": \"q1\", \"original_text\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。\\nA. “四万万”是 4 亿\\nB. “四万万”是一个近似数\\nC. “四万万”是 4 个十万\\nD. 从 0 开始，“千万、千万”地数，要数 40 次\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。\", \"options\": [{\"text\": \"“四万万”是 4 亿\", \"option\": \"A\"}, {\"text\": \"“四万万”是一个近似数\", \"option\": \"B\"}, {\"text\": \"“四万万”是 4 个十万\", \"option\": \"C\"}, {\"text\": \"从 0 开始，“千万、千万”地数，要数 40 次\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q2\", \"original_text\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（　　）只猎物。\\nA. 5\\nB. 17\\nC. 21\\nD. 32\", \"question_type\": \"multiple_choice\", \"question_number\": 2, \"structured_data\": {\"stem\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（　　）只猎物。\", \"options\": [{\"text\": \"5\", \"option\": \"A\"}, {\"text\": \"17\", \"option\": \"B\"}, {\"text\": \"21\", \"option\": \"C\"}, {\"text\": \"32\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q3\", \"original_text\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（　　）。\\nA. 两点之间线段最短\\nB. 直线可以无限延长\\nC. 两点确定一条直线\\nD. 点到直线间垂线段最短\", \"question_type\": \"multiple_choice\", \"question_number\": 3, \"structured_data\": {\"stem\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（　　）。\", \"options\": [{\"text\": \"两点之间线段最短\", \"option\": \"A\"}, {\"text\": \"直线可以无限延长\", \"option\": \"B\"}, {\"text\": \"两点确定一条直线\", \"option\": \"C\"}, {\"text\": \"点到直线间垂线段最短\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q4\", \"original_text\": \"下列成语所描述的事件中，（　　）发生的可能性最小？\\nA. 海底捞针\\nB. 瓜熟蒂落\\nC. 旭日东升\\nD. 水滴穿石\", \"question_type\": \"multiple_choice\", \"question_number\": 4, \"structured_data\": {\"stem\": \"下列成语所描述的事件中，（　　）发生的可能性最小？\", \"options\": [{\"text\": \"海底捞针\", \"option\": \"A\"}, {\"text\": \"瓜熟蒂落\", \"option\": \"B\"}, {\"text\": \"旭日东升\", \"option\": \"C\"}, {\"text\": \"水滴穿石\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q5\", \"original_text\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（　　）体重差不多。\\nA. 大象（2000 千克）\\nB. 奶牛（250 千克）\\nC. 小狗（30 千克）\\nD. 鲨鱼（2 吨）\", \"question_type\": \"multiple_choice\", \"question_number\": 5, \"structured_data\": {\"stem\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（　　）体重差不多。\", \"options\": [{\"text\": \"大象（2000 千克）\", \"option\": \"A\"}, {\"text\": \"奶牛（250 千克）\", \"option\": \"B\"}, {\"text\": \"小狗（30 千克）\", \"option\": \"C\"}, {\"text\": \"鲨鱼（2 吨）\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q6\", \"original_text\": \"下列说法中正确的是（　　）。\\nA. 用一副三角尺画出 115°\\nB. 2:55 这一刻，时针与分针的夹角等于 120 度\\nC. -5℃比-25℃低\\nD. 用计算器计算时，输错了可以按 [CE] 键清除\", \"question_type\": \"multiple_choice\", \"question_number\": 6, \"structured_data\": {\"stem\": \"下列说法中正确的是（　　）。\", \"options\": [{\"text\": \"用一副三角尺画出 115°\", \"option\": \"A\"}, {\"text\": \"2:55 这一刻，时针与分针的夹角等于 120 度\", \"option\": \"B\"}, {\"text\": \"-5℃比-25℃低\", \"option\": \"C\"}, {\"text\": \"用计算器计算时，输错了可以按 [\", \"option\": \"D\"}, {\"text\": \"E] 键清除\", \"option\": \"C\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q7\", \"original_text\": \"下面算式中，第一步要先算加法的是（　　）。\\nA. 34+66÷3\\nB. 288-(57+43)\\nC. 23×3+24÷4\\nD. 480÷[16+(36-28)]\\n\\n四年级数学试题 第1页（共6页）\", \"question_type\": \"multiple_choice\", \"question_number\": 7, \"structured_data\": {\"stem\": \"下面算式中，第一步要先算加法的是（　　）。\\n\\n四年级数学试题 第1页（共6页）\", \"options\": [{\"text\": \"34+66÷3\", \"option\": \"A\"}, {\"text\": \"288-(57+43)\", \"option\": \"B\"}, {\"text\": \"23×3+24÷4\", \"option\": \"C\"}, {\"text\": \"480÷[16+(36-28)]\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]','{\"status\": \"completed\", \"story_id\": \"story-997d138f\"}','completed',30,0,NULL,NULL,'2026-02-08 12:45:41.917','2026-02-08 12:47:38.335',NULL),(6,7,'数学','','[\"/uploads/assignments/6/0.png\"]','[{\"id\": \"q1\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。  \\nA、 “四万万”是4亿  \\nB、 “四万万”是一个近似数  \\nC、 “四万万”是4个十万  \\nD、 从0开始，“千万、千万”地数，要数40次\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。\", \"options\": [{\"text\": \"“四万万”是4亿\", \"option\": \"A\"}, {\"text\": \"“四万万”是一个近似数\", \"option\": \"B\"}, {\"text\": \"“四万万”是4个十万\", \"option\": \"C\"}, {\"text\": \"从0开始，“千万、千万”地数，要数40次\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]',NULL,'completed',30,0,NULL,NULL,'2026-02-08 13:08:16.895','2026-02-08 13:08:24.610',NULL),(7,13,'数学','','[\"/uploads/assignments/7/0.png\"]','[{\"id\": \"q1\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（ ）。\\nA. “四万万”是 4 亿\\nB. “四万万”是一个近似数\\nC. “四万万”是 4 个十万\\nD. 从 0 开始，“千万、千万”地数，要数 40 次\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（ ）。\", \"options\": [{\"text\": \"“四万万”是 4 亿\", \"option\": \"A\"}, {\"text\": \"“四万万”是一个近似数\", \"option\": \"B\"}, {\"text\": \"“四万万”是 4 个十万\", \"option\": \"C\"}, {\"text\": \"从 0 开始，“千万、千万”地数，要数 40 次\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q2\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（ ）只猎物。\\nA. 5\\nB. 17\\nC. 21\\nD. 32\", \"question_type\": \"multiple_choice\", \"question_number\": 2, \"structured_data\": {\"stem\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（ ）只猎物。\", \"options\": [{\"text\": \"5\", \"option\": \"A\"}, {\"text\": \"17\", \"option\": \"B\"}, {\"text\": \"21\", \"option\": \"C\"}, {\"text\": \"32\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q3\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（ ）。\\nA. 两点之间线段最短\\nB. 直线可以无限延长\\nC. 两点确定一条直线\\nD. 点到直线间垂线段最短\", \"question_type\": \"multiple_choice\", \"question_number\": 3, \"structured_data\": {\"stem\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（ ）。\", \"options\": [{\"text\": \"两点之间线段最短\", \"option\": \"A\"}, {\"text\": \"直线可以无限延长\", \"option\": \"B\"}, {\"text\": \"两点确定一条直线\", \"option\": \"C\"}, {\"text\": \"点到直线间垂线段最短\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q4\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"下列成语所描述的事件中，（ ）发生的可能性最小？\\nA. 海底捞针\\nB. 瓜熟蒂落\\nC. 旭日东升\\nD. 水滴穿石\", \"question_type\": \"multiple_choice\", \"question_number\": 4, \"structured_data\": {\"stem\": \"下列成语所描述的事件中，（ ）发生的可能性最小？\", \"options\": [{\"text\": \"海底捞针\", \"option\": \"A\"}, {\"text\": \"瓜熟蒂落\", \"option\": \"B\"}, {\"text\": \"旭日东升\", \"option\": \"C\"}, {\"text\": \"水滴穿石\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q5\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（ ）体重差不多。\\nA. 大象（2000 千克）\\nB. 奶牛（250 千克）\\nC. 小狗（30 千克）\\nD. 鲨鱼（2 吨）\", \"question_type\": \"multiple_choice\", \"question_number\": 5, \"structured_data\": {\"stem\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（ ）体重差不多。\", \"options\": [{\"text\": \"大象（2000 千克）\", \"option\": \"A\"}, {\"text\": \"奶牛（250 千克）\", \"option\": \"B\"}, {\"text\": \"小狗（30 千克）\", \"option\": \"C\"}, {\"text\": \"鲨鱼（2 吨）\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q6\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"下列说法中正确的是（ ）。\\nA. 用一副三角尺画出 115°\\nB. 2:55 这一刻，时针与分针的夹角等于 120 度\\nC. -5℃比-25℃低\\nD. 用计算器计算时，输错了可以按 \\\\(\\\\boxed{CE}\\\\) 键清除\", \"question_type\": \"multiple_choice\", \"question_number\": 6, \"structured_data\": {\"stem\": \"下列说法中正确的是（ ）。\", \"options\": [{\"text\": \"用一副三角尺画出 115°\", \"option\": \"A\"}, {\"text\": \"2:55 这一刻，时针与分针的夹角等于 120 度\", \"option\": \"B\"}, {\"text\": \"-5℃比-25℃低\", \"option\": \"C\"}, {\"text\": \"用计算器计算时，输错了可以按 \\\\(\\\\boxed{\", \"option\": \"D\"}, {\"text\": \"E}\\\\) 键清除\", \"option\": \"C\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}, {\"id\": \"q7\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"下面算式中，第一步要先算加法的是（ ）。\\nA. \\\\(34+66\\\\div3\\\\)\\nB. \\\\(288-(57+43)\\\\)\\nC. \\\\(23\\\\times3+24\\\\div4\\\\)\\nD. \\\\(480\\\\div[16+(36-28)]\\\\)\\n\\n植树时，需要先确定两个坑的位置，以便使得其他的树坑能和他们排成一行。\\n\\n四年级数学试题 第1页（共6页）\", \"question_type\": \"multiple_choice\", \"question_number\": 7, \"structured_data\": {\"stem\": \"下面算式中，第一步要先算加法的是（ ）。\\n\\n植树时，需要先确定两个坑的位置，以便使得其他的树坑能和他们排成一行。\\n\\n四年级数学试题 第1页（共6页）\", \"options\": [{\"text\": \"\\\\(34+66\\\\div3\\\\)\", \"option\": \"A\"}, {\"text\": \"\\\\(288-(57+43)\\\\)\", \"option\": \"B\"}, {\"text\": \"\\\\(23\\\\times3+24\\\\div4\\\\)\", \"option\": \"C\"}, {\"text\": \"\\\\(480\\\\div[16+(36-28)]\\\\)\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]',NULL,'completed',30,0,NULL,NULL,'2026-02-11 20:10:32.518','2026-02-11 20:10:41.788',NULL),(8,13,'数学','','[\"/uploads/assignments/8/0.jpg\"]','[{\"id\": \"q1\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。  \\nA、 “四万万”是4亿  \\nB、 “四万万”是一个近似数  \\nC、 “四万万”是4个十万  \\nD、 从0开始，“千万、千万”地数，要数40次\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。\", \"options\": [{\"text\": \"“四万万”是4亿\", \"option\": \"A\"}, {\"text\": \"“四万万”是一个近似数\", \"option\": \"B\"}, {\"text\": \"“四万万”是4个十万\", \"option\": \"C\"}, {\"text\": \"从0开始，“千万、千万”地数，要数40次\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]','{\"status\": \"completed\", \"story_id\": \"story-c9b39901\"}','completed',30,0,NULL,NULL,'2026-02-11 20:30:50.512','2026-02-14 10:45:46.574',NULL),(9,13,'数学','','[\"/uploads/assignments/9/0.png\"]','[{\"id\": \"q1\", \"metadata\": {\"has_image\": false, \"confidence\": 0.85, \"word_count\": 0, \"has_formula\": false}, \"original_text\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（　　）体重差不多。\\nA. 大象（2000 千克） B. 奶牛（250 千克） C. 小狗（30 千克） D. 鲨鱼（2 吨）\", \"question_type\": \"multiple_choice\", \"question_number\": 1, \"structured_data\": {\"stem\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（　　）体重差不多。\", \"options\": [{\"text\": \"大象（2000 千克）\", \"option\": \"A\"}, {\"text\": \"奶牛（250 千克）\", \"option\": \"B\"}, {\"text\": \"小狗（30 千克）\", \"option\": \"C\"}, {\"text\": \"鲨鱼（2 吨）\", \"option\": \"D\"}]}, \"knowledge_points\": [{\"topic\": \"综合\", \"subject\": \"数学\", \"subtopic\": \"\", \"difficulty\": \"medium\"}]}]',NULL,'completed',30,0,NULL,NULL,'2026-02-13 22:02:05.534','2026-02-13 22:02:07.225',NULL);
/*!40000 ALTER TABLE `assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `children`
--

DROP TABLE IF EXISTS `children`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `children` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `name` varchar(50) NOT NULL,
  `nickname` varchar(50) DEFAULT NULL,
  `gender` tinyint DEFAULT '0',
  `birth_date` date DEFAULT NULL,
  `grade` varchar(20) DEFAULT NULL,
  `interests` json DEFAULT NULL,
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `avatar_url` varchar(500) DEFAULT NULL,
  `custom_interests` json DEFAULT NULL,
  `learning_style` varchar(20) DEFAULT NULL,
  `attention_span` int DEFAULT NULL,
  `weak_subjects` json DEFAULT NULL,
  `learning_stats` json DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_children_user_id` (`user_id`),
  KEY `idx_children_deleted_at` (`deleted_at`),
  CONSTRAINT `fk_children_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `children`
--

LOCK TABLES `children` WRITE;
/*!40000 ALTER TABLE `children` DISABLE KEYS */;
INSERT INTO `children` VALUES (1,7,'TestChild','',1,NULL,'','[\"Coding\", \"AI\"]','2026-01-22 14:36:42.447','2026-01-22 14:36:42.447',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(2,11,'BrowserChild2','',0,NULL,'','[\"Coding\", \"Math\"]','2026-01-22 14:50:41.372','2026-01-22 14:50:41.372',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(3,12,'BrowserChild2','',0,NULL,'','[\"Coding\", \"Math\"]','2026-01-22 14:53:19.200','2026-01-22 14:53:19.200',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(4,12,'','',0,NULL,'','null','2026-01-22 14:55:03.569','2026-01-22 14:55:03.569',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(5,12,'','',0,NULL,'','null','2026-01-22 14:55:49.485','2026-01-22 14:55:49.485',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(6,12,'BrowserChild2','',0,NULL,'','[\"Coding\", \"Math\"]','2026-01-22 14:56:55.442','2026-01-22 14:56:55.442',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(7,2,'冯雨','',1,NULL,'','[\"奥特曼\", \"海底小纵队\"]','2026-01-22 23:05:04.728','2026-01-22 23:05:04.728',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(8,13,'HomeworkChild','',0,NULL,'','null','2026-01-23 00:36:31.335','2026-01-23 00:36:31.335',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(9,20,'TestKid','',1,NULL,'','[\"Math\"]','2026-01-23 11:24:12.080','2026-01-23 11:24:12.080',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(10,1,'TestKid','',1,NULL,'','[\"Math\"]','2026-01-23 11:31:10.679','2026-01-23 11:31:10.679',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(11,23,'TestHW','',0,NULL,'','[\"Male\"]','2026-01-23 11:47:16.625','2026-01-23 11:47:16.625',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(12,24,'CurlChild','',1,NULL,'','null','2026-01-23 11:54:08.163','2026-01-23 11:54:08.163',NULL,NULL,NULL,NULL,NULL,NULL,NULL),(13,26,'冯玉桥','mino',2,'2019-02-11','幼儿园大班','[\"奥特曼\", \"海底小纵队\", \"超级飞侠\", \"恐龙\", \"动物世界\"]','2026-02-11 15:43:47.734','2026-02-11 15:43:47.734','','[]','视觉型',15,'[\"语文\", \"数学\"]','{\"average_score\": 0, \"last_study_date\": \"\", \"total_study_time\": 0, \"completed_assignments\": 0}',NULL),(14,26,'冯蓝天','sky',1,'2013-02-16','五年级','[\"外星人\", \"未来世界\", \"警察\", \"汽车\", \"积木\"]','2026-02-16 12:40:09.639','2026-02-16 12:40:09.639','','[]','听觉型',0,'[\"英语\", \"科学\"]','{\"average_score\": 0, \"last_study_date\": \"\", \"total_study_time\": 0, \"completed_assignments\": 0}',NULL);
/*!40000 ALTER TABLE `children` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `homeworks`
--

DROP TABLE IF EXISTS `homeworks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `homeworks` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `child_id` bigint unsigned NOT NULL,
  `subject` varchar(20) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `image_url` text,
  `status` varchar(20) DEFAULT 'pending',
  `ocr_result` json DEFAULT NULL,
  `score` int DEFAULT '0',
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_homeworks_child_id` (`child_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `homeworks`
--

LOCK TABLES `homeworks` WRITE;
/*!40000 ALTER TABLE `homeworks` DISABLE KEYS */;
INSERT INTO `homeworks` VALUES (1,12,'Math','Curl HW Fixed','http://img','completed','{\"text\": \"1+1=2, 2+2=5\", \"confidence\": 0.95}',93,'2026-01-23 11:55:27.973','2026-01-23 11:55:29.985');
/*!40000 ALTER TABLE `homeworks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `question_answers`
--

DROP TABLE IF EXISTS `question_answers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_answers` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) NOT NULL,
  `child_id` bigint unsigned NOT NULL,
  `user_answer` text NOT NULL,
  `is_correct` tinyint(1) DEFAULT NULL,
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_assignment_question_child` (`assignment_id`,`question_id`,`child_id`),
  KEY `idx_question_answers_child_id` (`child_id`),
  KEY `idx_question_answers_deleted_at` (`deleted_at`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `question_answers`
--

LOCK TABLES `question_answers` WRITE;
/*!40000 ALTER TABLE `question_answers` DISABLE KEYS */;
INSERT INTO `question_answers` VALUES (1,7,'q1',13,'B',NULL,'2026-02-12 11:30:54.133','2026-02-13 21:51:05.588',NULL),(2,7,'q2',13,'C',NULL,'2026-02-12 11:31:24.851','2026-02-13 21:51:10.705',NULL),(3,7,'q3',13,'C',NULL,'2026-02-12 11:31:28.654','2026-02-13 21:51:14.495',NULL),(4,7,'q4',13,'C',NULL,'2026-02-12 11:31:32.348','2026-02-13 21:51:18.798',NULL),(5,7,'q5',13,'D',NULL,'2026-02-12 11:31:36.204','2026-02-13 21:51:23.212',NULL),(6,7,'q6',13,'A',NULL,'2026-02-12 11:31:40.964','2026-02-13 21:51:36.796',NULL),(7,7,'q7',13,'B',NULL,'2026-02-12 11:31:45.174','2026-02-13 21:51:41.496',NULL),(8,8,'q1',13,'A',NULL,'2026-02-14 10:49:51.040','2026-02-16 12:57:33.373',NULL);
/*!40000 ALTER TABLE `question_answers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `question_generation_statuses`
--

DROP TABLE IF EXISTS `question_generation_statuses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_generation_statuses` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `story_id` varchar(64) DEFAULT NULL,
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assignment_question` (`assignment_id`,`question_id`),
  KEY `idx_question_generation_statuses_status` (`status`),
  KEY `idx_question_generation_statuses_deleted_at` (`deleted_at`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `question_generation_statuses`
--

LOCK TABLES `question_generation_statuses` WRITE;
/*!40000 ALTER TABLE `question_generation_statuses` DISABLE KEYS */;
INSERT INTO `question_generation_statuses` VALUES (1,5,'q4','completed','story-55368b22','2026-02-09 00:27:02.849','2026-02-09 00:27:22.366',NULL),(2,7,'q1','completed','story-fabb5475','2026-02-11 20:10:57.591','2026-02-11 20:11:11.861',NULL),(3,7,'q2','completed','story-e2da38f6','2026-02-12 10:10:27.954','2026-02-12 10:11:01.063',NULL),(4,7,'q3','completed','story-d5289151','2026-02-12 10:15:34.671','2026-02-12 10:15:51.040',NULL),(5,7,'q4','completed','story-6fb95b36','2026-02-12 10:19:29.897','2026-02-12 10:19:46.098',NULL),(6,7,'q5','completed','story-242114d9','2026-02-12 10:27:54.130','2026-02-12 10:28:11.320',NULL),(7,7,'q6','completed','story-6d642b6e','2026-02-12 10:28:27.417','2026-02-12 10:28:52.206',NULL),(8,7,'q7','completed','story-06b69a7e','2026-02-12 10:28:59.267','2026-02-12 10:29:17.354',NULL);
/*!40000 ALTER TABLE `question_generation_statuses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `story_contents`
--

DROP TABLE IF EXISTS `story_contents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `story_contents` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `story_id` varchar(64) NOT NULL,
  `assignment_id` bigint unsigned NOT NULL,
  `question_id` varchar(64) DEFAULT NULL,
  `title` varchar(200) DEFAULT NULL,
  `summary` text,
  `story` longtext NOT NULL,
  `questions` json DEFAULT NULL,
  `theme` varchar(100) DEFAULT NULL,
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_story_contents_story_id` (`story_id`),
  KEY `idx_story_contents_assignment_id` (`assignment_id`),
  KEY `idx_story_contents_deleted_at` (`deleted_at`),
  KEY `idx_story_contents_question_id` (`question_id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `story_contents`
--

LOCK TABLES `story_contents` WRITE;
/*!40000 ALTER TABLE `story_contents` DISABLE KEYS */;
INSERT INTO `story_contents` VALUES (1,'story-3ff7c921',4,NULL,'冯雨的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯雨是个戴红框眼镜、总爱仰头看星星的三年级男孩。他最喜欢奥特曼，不是因为打怪兽，而是因为奥特曼胸前的彩色计时器像一块会发光的数学表盘——滴答、滴答，好像在悄悄教他算数呢！每天放学，他都会把书包放在窗台边，让夕阳给铅笔镀上一层金边，再翻开数学本。\n\n今天，数学本上跳出几道“光之谜题”：一道道减法算式像一排排等待点亮的能量柱。老师说：“这些题目是奥特曼留给地球小战士的‘能量补给站’，填对数字，就能为光之国输送一份力量！”冯雨挠挠头：6 - 4 = □？他伸出左手比划出6根手指，弯下4根，剩下2根——“亮了！”他画了个闪亮的“2”。可下一行“6 - □ = □”让他停住了，像奥特曼遇到迷雾一样眨眨眼。\n\n这时，窗外飞来一只蓝翅膀的小纸鹤（是同桌悄悄折的），轻轻落在“7 - 3 = □”旁边。冯雨灵机一动：7颗星星减去3颗躲进云里的，天上还剩4颗！他拿起彩笔，在每道题旁画上小星星、小云朵和小光点。最后一题“□ - □ = □”，他想起昨天分给妹妹2颗糖，自己原来有5颗——5 - 2 = 3！他笑着写下答案，整页作业本突然像被阳光吻过，暖暖地亮了起来。\n\n第二天，老师夸冯雨的作业像一座小小的光之塔，每道题都写得清清楚楚、闪闪发亮。冯雨摸摸胸口，仿佛听见心里有个温柔的声音说：“真正的光，不在胸前，而在你认真思考的眼睛里。”  \n【学习要点】  \n• 理解减法的意义（从总数中去掉一部分）  \n• 熟练计算6、7减几的算式  \n• 在等式中根据已知数推算未知数（如6 - □ = 2，反向思考）  \n• 用生活情境（分糖、数星星）帮助理解抽象算式','[{\"id\": \"q1\", \"answer\": \"\", \"content\": \"● 写一写 按照图示填写数字。\\n6 - 4 = □\\n6 - □ = □\\n\\n6 - 5 = □\\n6 - □ = □\\n\\n7 - 5 = □\\n7 - □ = □\\n\\n7 - 3 = □\\n□ - □ = □\\n26\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-08 00:09:46.503','2026-02-08 00:09:46.503',NULL),(2,'story-997d138f',5,NULL,'冯雨的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯雨是个爱看奥特曼的小男孩，他总把红蓝相间的运动服当“变身战袍”，书包上还别着一枚闪闪发亮的奥特曼徽章。这天放学，他发现课桌抽屉里躺着一封银光闪闪的信——是来自M78星云的“数学光之信”！信上说：“地球小勇士冯雨，长城需要能量守护，请用智慧解开6道光之谜题，才能点亮长城上的星光屏障！”\n\n冯雨立刻戴上“思考眼镜”（其实是他的圆框眼镜），翻开信纸：第一题问“四万万”是不是4个十万？他掰着手指算：“一万一万……哦！十万是10万，四万万是40000万，就是4亿，不是4个十万！”第二题画着三根绳子，右边结5个疙瘩、中间2个、左边1个，他想起科学课学的“满五进一”，像算盘一样：1×25 + 2×5 + 1 = 36？不对！再数——原来是从右往左：个位（1）、五位（2×5=10）、二十五位（1×25=25），25+10+1=36？等等……信纸角落画了个小箭头：“第三幅图只有两列！”他重看图——右边5个结（5只），左边3个结（3×5=15只），共20只？可选项没有20……啊！是“满五进一”，右边5个结=1个进位，左边3个结=3×5=15，加上右边余0？不，图上右边4个结、左边3个结！4+3×5=19？还是不对……他深吸一口气，模仿奥特曼摆出“光线姿势”，忽然灵光一闪：“老师说过，结绳计数像五进制！第三幅图：右列3个结（3只），中列2个结（2×5=10只），左列1个结（1×25=25只）？但图只有两列！”他翻到背面，发现小字提示：“第三幅图：右4结，左2结”——4 + 2×5 = 14？可选项有17……等等！是“从右往左，满五进一”，所以右列满5才向左进1。右列4个=4只，左列2个=2×5=10只，共14？但B选项是17……他眨眨眼，突然想起美术课画过类似图：最右是“1位”，中间是“5位”，左是“25位”。图中右列2结、中列3结、左列1结？不，信纸上清清楚楚印着：第三幅图——右：2个结，中：3个结，左：1个结！1×25 + 3×5 + 2 = 25+15+2=42？超了……他轻轻敲敲徽章，想起奥特曼从不放弃。再读题干：“如图”——可信纸上没图！他抬头望向窗外，阳光正照在课本《数学伴你成长》第32页——那里正印着结绳图！右2、中3、左1？不，是右2、中3、空左？他翻书，啊！第三幅图：右列3结（3只），中列2结（2×5=10只），共13？还是不对……这时，妈妈端来苹果：“雨雨，吃个‘智慧果’再想？”他咬一口，甜滋滋的，忽然笑出来：“老师说，结绳和我们的十进制一样，只是‘满五’才进！右列3个就是3，中列2个就是2×5=10，加起来13……可选项没有13……”他静下心，重新看题：“第三幅图表示（　　）只猎物”，选项B是17。17怎么来的？2×5 + 7？不对……等等！如果中列是3个结（3×5=15），右列是2个结（2），15+2=17！对啦！图上中列明明是3个结，右列2个结！他开心地跳起来：“是17！B！”\n\n最后一题关于蚂蚁体重，他拿出计算器按呀按：“1只2毫克，1亿只就是2亿毫克！2亿毫克=200千克！和奶牛差不多！”他飞快写完所有答案，信纸顿时亮起金光，窗外长城轮廓浮现出点点星光，像一串温柔的星星项链。“谢谢你，地球小数学家！”信末写道，“真正的光，永远来自认真思考的眼睛。”\n\n【学习要点】  \n• “万”“亿”的计数单位与换算（如四万万=4亿）  \n• 五进制计数原理（满五进一）  \n• 几何公理：两点确定一条直线  \n• 可能性大小判断（成语中的必然与偶然）  \n• 大数单位换算（毫克→克→千克）  \n• 四则运算顺序（带括号、中括号的算式）','[{\"id\": \"q1\", \"answer\": \"\", \"content\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。\\nA. “四万万”是 4 亿\\nB. “四万万”是一个近似数\\nC. “四万万”是 4 个十万\\nD. 从 0 开始，“千万、千万”地数，要数 40 次\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q2\", \"answer\": \"\", \"content\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（　　）只猎物。\\nA. 5\\nB. 17\\nC. 21\\nD. 32\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q3\", \"answer\": \"\", \"content\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（　　）。\\nA. 两点之间线段最短\\nB. 直线可以无限延长\\nC. 两点确定一条直线\\nD. 点到直线间垂线段最短\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q4\", \"answer\": \"\", \"content\": \"下列成语所描述的事件中，（　　）发生的可能性最小？\\nA. 海底捞针\\nB. 瓜熟蒂落\\nC. 旭日东升\\nD. 水滴穿石\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q5\", \"answer\": \"\", \"content\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（　　）体重差不多。\\nA. 大象（2000 千克）\\nB. 奶牛（250 千克）\\nC. 小狗（30 千克）\\nD. 鲨鱼（2 吨）\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q6\", \"answer\": \"\", \"content\": \"下列说法中正确的是（　　）。\\nA. 用一副三角尺画出 115°\\nB. 2:55 这一刻，时针与分针的夹角等于 120 度\\nC. -5℃比-25℃低\\nD. 用计算器计算时，输错了可以按 [CE] 键清除\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}, {\"id\": \"q7\", \"answer\": \"\", \"content\": \"下面算式中，第一步要先算加法的是（　　）。\\nA. 34+66÷3\\nB. 288-(57+43)\\nC. 23×3+24÷4\\nD. 480÷[16+(36-28)]\\n\\n四年级数学试题 第1页（共6页）\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-08 12:47:38.324','2026-02-08 12:47:38.324',NULL),(3,'story-55368b22',5,'q4','冯雨的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯雨是个三年级的小学生，最爱穿蓝色运动服，书包上还别着一枚闪闪发亮的奥特曼徽章。他常说：“我要像奥特曼一样，用智慧和勇气守护大家！”这天放学路上，他发现校门口的“星光小信箱”里插着一封银光闪闪的信——信封上画着奥特曼的彩色计时器，还写着：“紧急求助！请数学小战士解题救急！”\n\n冯雨赶紧拆开信：原来，奥特曼在宇宙巡逻时发现一颗叫“概率星”的小星球正变得灰蒙蒙的！星球上的彩虹桥快要消失，因为居民们分不清哪些事情“几乎不会发生”，哪些“一定会发生”。信里附着一道题：“下列成语中，哪件事发生的可能性最小？”选项是：A.海底捞针　B.瓜熟蒂落　C.旭日东升　D.水滴穿石。\n\n冯雨坐在小区凉亭里，托着腮帮子想呀想。他想起科学课老师说过：“旭日东升每天都会发生，就像呼吸一样自然！”（C一定发生）；“瓜熟了果子自己掉下来，这是植物生长的规律。”（B也很可能）；“水滴坚持落下，石头真会被滴穿——我们班种的豆芽都长高了呢！”（D虽然慢，但真的会发生）。可“海底捞针”呢？大海那么大，针那么小，又没标记，找一万年也难找到呀！他眼睛一亮，掏出荧光笔，在A旁边画了个小星星：“这个最不可能，就像让奥特曼用光线打中一颗隐形的灰尘一样难！”\n\n第二天，冯雨把答案告诉老师，还画了一张“可能性彩虹图”贴在教室墙上：从“一定发生”到“几乎不可能”，像一道弯弯的光谱。下午，天空忽然飘来一朵云，形状正好是奥特曼的侧脸，还洒下一道金灿灿的光——仿佛在说：“谢谢你，数学小战士！”冯雨摸摸徽章，笑得比阳光还亮。\n\n【学习要点】  \n• 理解“可能性大小”的生活含义（一定发生、很可能发生、几乎不可能）  \n• 联系成语与现实事件判断概率高低  \n• 学会用观察、比较和生活经验解决数学问题','[{\"id\": \"q4\", \"answer\": \"\", \"content\": \"下列成语所描述的事件中，（　　）发生的可能性最小？\\nA. 海底捞针\\nB. 瓜熟蒂落\\nC. 旭日东升\\nD. 水滴穿石\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-09 00:27:22.353','2026-02-09 00:27:22.353',NULL),(4,'story-fabb5475',7,'q1','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是幼儿园大班的“数学小超人”，他最爱穿红蓝相间的披风，还总把奥特曼徽章别在书包上。今天放学时，他发现书包里多了一张闪闪发光的“光之答题卡”——原来是奥特曼叔叔送来的特别任务：“答对题目，就能点亮守护地球的‘团结光波’！”\n\n他赶紧掏出铅笔，卡片上写着：《长城谣》里唱“四万万同胞心一样”，可有个选项说错了，要帮奥特曼找出来！四个小星星选项亮晶晶地排着队：A说“四万万”就是4亿；B说它是个大约的数；C说它是4个十万；D说从0开始，每次加“千万”，加40次就到啦！\n\n冯玉桥歪着头想呀想，拿出彩色小积木摆起来：“一千万、两千万……十千万就是一亿！”他数了10次，就有一亿啦！那4亿，就得数40次（10×4=40）——D是对的！他又摆出“十万”块：4个十万才40万，远远不够“四万万”（40000万=4亿）——啊哈！C选项悄悄弄错了！就像把4颗糖果说成4盒糖，差好远呢！\n\n“答对啦！”光之答题卡“叮”一声变成一道彩虹光束，飞向天空，和月亮上的奥特曼击了个掌！冯玉桥开心地跳起来：“原来‘四万万’不是随便说说，是大家紧紧抱在一起的大数字，像长城砖一块连一块，谁也分不开！”  \n\n【学习要点】  \n• “四万万”=4亿=400000000  \n• “万万”就是“亿”（1万×1万=1亿）  \n• 4个十万=40万，≠4亿（大小比较）  \n• “四万万”是近似数，表示约4亿人团结一心','[{\"id\": \"q1\", \"answer\": \"\", \"content\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（ ）。\\nA. “四万万”是 4 亿\\nB. “四万万”是一个近似数\\nC. “四万万”是 4 个十万\\nD. 从 0 开始，“千万、千万”地数，要数 40 次\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-11 20:11:11.855','2026-02-11 20:11:11.855',NULL),(5,'story-e2da38f6',7,'q2','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是阳光幼儿园大班最爱动脑筋的小朋友，他有个闪闪发光的奥特曼徽章，每次遇到难题，就摸一摸徽章说：“奥特曼，帮帮我！”这天，老师带来一本神奇的《古早小故事书》，翻开一页，画着一位笑眯眯的神农爷爷，正用彩色绳子打结记猎物呢！“看，这是古代的‘数学绳’哦！”老师眨眨眼，“从右边开始数，每5个结就变成左边一个新结——就像把5颗糖换成1个大糖果盒！”\n\n故事里，神农爷爷的第三根绳子上，右边有2个小结，中间有3个中结，左边有1个大结（图上画得像小星星、月亮和太阳）。老师问：“小朋友们，这根绳子到底记了几只小兔子呀？”大家你看看我，我看看你。冯玉桥歪着头，拿出自己的五彩积木：先摆2块红积木（右边小结），再摆3组“5块蓝积木”（中间3个中结=3×5=15），最后摆1组“5个5块黄积木”（左边1个大结=1×5×5=25）……咦？不对！他想起老师说的“从右往左，满五进一”，就像搭积木塔：最右边是“个位”（1只兔子=1个结），中间是“五位”（1个结=5只），左边是“二十五位”（1个结=25只）！所以：1×25 + 3×5 + 2×1 = 25+15+2 = 42？等等……他翻回书页，发现图上左边只有1个结、中间3个、右边2个——可选项里没有42！他深吸一口气，再数一遍：啊！原来左边那个“大结”代表的是“1个二十五”，但图里其实是“1个五位结”和“2个一位结”？不，再看仔细——老师悄悄指了指图注：“第三幅图：左1·中3·右2”。他灵光一闪：左是25位？不对！古代结绳是“五进制”，不是“二十五进制”哦！正确是：右位=1，中位=5，左位=5×5=25？可题目选项最大才32……他忽然想起奥特曼徽章背面刻着“5进制小口诀”：“右1中5左25！”——但25+15+2=42超了！他轻轻碰碰徽章，小声说：“奥特曼，请教我怎么看对？”这时同桌小雨递来5根小棒：“玉桥，我们按‘满五进一’来摆！”他们一起摆：右边2根（2只），中间3捆（每捆5根→15只），左边1捆（但这一捆是“5捆才换1个”，所以左边1个=5×5=25？还是……等等！老师笑着提示：“小朋友，神农爷爷只用两层绳结哦——左是‘五位’，右是‘个位’，中间那层其实是‘五位’？不，图上只有三格：右、中、左，对应‘1、5、25’。”他恍然大悟：1×25 + 3×5 + 2×1 = 25+15+2=42？可选项没有42……他再盯图——啊！第三幅图其实是：左0、中3、右2？不，图明确画着左1、中3、右2。他忽然明白：题目中“第三幅图”在原题里对应选项B.17？他快速心算：如果左是“5×5=25”太大，那可能只是“五进制三位数”，即左×5² + 中×5¹ + 右×5⁰ = 1×25 + 3×5 + 2×1 = 42，但选项无42……等等！他翻到书末小贴士：“神农结绳，两档记数：右为1，左为5，满五进左——所以最多两档！”他抬头喊：“老师，图上只有两档？中间那个是装饰？”老师笑着点头：“对啦！真正结绳只有右和左两列，中间是分隔线！第三幅图：左3个结（3×5=15），右2个结（2×1=2），一共17只！”冯玉桥跳起来：“是17！选B！”全班响起小星星掌声。\n\n放学时，冯玉桥把徽章擦得亮亮的，心想：“原来古代人也用数学保护小动物——数清兔子，才能分得公平呀！”他牵着妈妈的手，哼起自编的歌：“结绳记数真奇妙，五只一堆刚刚好！”\n\n【学习要点】  \n• 认识五进制计数法（满五进一）  \n• 理解数位含义：右位=1，左位=5  \n• 练习简单加法与倍数计算（如3×5+2）','[{\"id\": \"q2\", \"answer\": \"\", \"content\": \"在《说文解字·序》中提及“神农氏结绳为治，而统其事”。有一位神农氏时代的村民，用结绳来记录猎物的数量。他的方法是“从右往左，满五进一”（如图），第三幅图表示（ ）只猎物。\\nA. 5\\nB. 17\\nC. 21\\nD. 32\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:11:01.048','2026-02-12 10:11:01.048',NULL),(6,'story-d5289151',7,'q3','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是幼儿园大班的“小奥特曼迷”，他总爱披着蓝披风，用纸板剪出闪闪发光的彩色计时器挂在脖子上。今天，他和老师、小伙伴们一起去幼儿园的小花园种小树苗啦！大家挖好了一个个圆圆的树坑，可排得歪歪扭扭，像一条弯弯的毛毛虫。“这样不行哦，”老师笑着说，“小树苗站成整齐的一队，才能一起晒太阳、喝雨水，长得又高又壮！”\n\n这时，科学小助手——一只戴眼镜的卡通小机器人“叮叮”从工具箱里跳出来：“玉桥，快帮我们想个办法！只要在地面上先标出两个小石子，再用一根彩色绳子拉直连起来，后面所有的树坑都沿着这条线挖，就能排成笔直的一队啦！”冯玉桥挠挠头：“咦？为什么只放两颗小石子，就能管住整条直线呀？”\n\n他蹲下来，用小手指点着第一颗石子说：“这是点A！”又点点第二颗：“这是点B！”他拿起绳子一拉——哗！一道亮晶晶的直线出现了！“原来呀，只要有两个确定的位置，就像奥特曼发射光线一样，‘嗖’一下，就只能画出唯一一条直直的线！”他开心地拍手，“怪不得小树们排队这么听话呢！”\n\n最后，大家沿着这条“奥特曼光线线”挖好了所有树坑，小树苗们排得整整齐齐，像一支精神抖擞的绿色小分队！冯玉桥摸摸胸前的纸板计时器，笑得眼睛弯成了月牙：“原来数学，就是藏在生活里的超级能量！”\n\n【学习要点】  \n• 两点确定一条直线  \n• 直线是笔直、可以向两边无限延伸的  \n• 生活中用两点连线来保证排列整齐（如种树、摆椅子、画跑道）','[{\"id\": \"q3\", \"answer\": \"\", \"content\": \"植树时，确保树坑排成一行的方法（如图）所含的数学原理是（ ）。\\nA. 两点之间线段最短\\nB. 直线可以无限延长\\nC. 两点确定一条直线\\nD. 点到直线间垂线段最短\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:15:51.035','2026-02-12 10:15:51.035',NULL),(7,'story-6fb95b36',7,'q4','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是个戴红围巾、爱眨眼睛的小男孩，他最喜欢奥特曼——不是打怪兽的那种，而是“智慧光之战士”奥特曼！这位奥特曼不靠激光炮，靠动脑筋发光！每天放学，玉桥都会在窗台摆好小奥特曼模型，等它“接收智慧信号”。\n\n今天，玉桥刚写完作业，窗外忽然亮起一道柔柔的蓝光。“叮！”奥特曼从书包里“嗖”地跳出来（其实是玉桥用磁铁和纸板做的小机关，但他相信是真的！），举起闪亮的手环说：“玉桥，地球遇到‘可能性迷雾’啦！快帮我们选出发光最弱的成语——它藏着最小的机会！”手环上跳出四个选项：A.海底捞针，B.瓜熟蒂落，C.旭日东升，D.水滴穿石。\n\n玉桥托着小脸想呀想：旭日东升？每天早上太阳都笑眯眯地爬上来，肯定常常发生！瓜熟蒂落？妈妈种的南瓜藤上，小瓜慢慢变大，“啪嗒”掉下来，也很自然！水滴穿石？他和爸爸在公园看过石阶上的小坑，一滴、两滴……好久好久才有一点点小窝，但真的能成功！最后是“海底捞针”——大海那么大，水那么深，针又细又小，连小海豚都找不到呢！“啊！”玉桥拍拍手，“它发生的可能最小，就像……像我找不见掉进沙发缝的彩虹糖一样难！”\n\n奥特曼“唰”地亮起金光，把“海底捞针”圈成一颗小星星：“答对啦！可能性小，不等于不可能哦——只要坚持，连小水滴都能穿石头！”玉桥笑着把答案工整写进作业本，窗外的晚霞也像一道温柔的光束，悄悄落在他画满星星的数学本上。\n\n【学习要点】  \n• 理解“可能性大小”的生活含义（常见 vs 罕见）  \n• 通过自然现象和日常经验比较事件发生的容易程度  \n• 培养积极心态：小概率≠做不到，坚持就有光','[{\"id\": \"q4\", \"answer\": \"\", \"content\": \"下列成语所描述的事件中，（ ）发生的可能性最小？\\nA. 海底捞针\\nB. 瓜熟蒂落\\nC. 旭日东升\\nD. 水滴穿石\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:19:46.073','2026-02-12 10:19:46.073',NULL),(8,'story-242114d9',7,'q5','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是幼儿园大班最爱动脑筋的小朋友，他有个闪闪发亮的奥特曼徽章，每次遇到难题，就摸一摸徽章说：“奥特曼，帮帮我！”这天放学路上，他看见一群小蚂蚁排着队搬饼干渣，像一支勇敢的小军队。\n\n突然，一只穿着银色小披风的“数学精灵”从蒲公英里跳出来，笑嘻嘻地说：“冯玉桥，奥特曼选中你当‘地球智慧小卫士’啦！快解开这个谜题，才能获得守护森林的能量光波哦！”她变出一张发光卡片：一只蚂蚁约重2-3毫克，1000只约2-3克，那1亿只蚂蚁加起来，体重差不多等于一只什么动物呢？选项有大象、奶牛、小狗和鲨鱼——可冯玉桥还没学过“亿”和“吨”呀！\n\n冯玉桥蹲在草地上，拿出小本子画呀算呀：“1000只=2克，那100万只就是2000克，也就是2千克……1亿是100个100万！2千克×100=200千克！”他眼睛一亮，“200千克——和奶牛哥哥的体重一样重！”这时，奥特曼徽章轻轻发热，一道彩虹光射向天空，变成一只温柔的奶牛剪影，还“哞～”地打了个友好的招呼！\n\n原来，再小的蚂蚁团结起来，也能拥有大大的力量！冯玉桥开心地把答案告诉精灵，整片草地都开出了会眨眼睛的小雏菊。他明白了：数字不是冷冰冰的符号，而是悄悄藏在小蚂蚁、小奶牛和我们生活里的奇妙魔法！\n\n【学习要点】  \n• 认识质量单位：毫克、克、千克、吨的换算关系  \n• 理解“1亿=100×100万”，体会大数的倍数关系  \n• 用分步计算解决实际问题（如1000只→100万只→1亿只）  \n• 感受数学与自然生命的有趣联系','[{\"id\": \"q5\", \"answer\": \"\", \"content\": \"一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（ ）体重差不多。\\nA. 大象（2000 千克）\\nB. 奶牛（250 千克）\\nC. 小狗（30 千克）\\nD. 鲨鱼（2 吨）\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:28:11.307','2026-02-12 10:28:11.307',NULL),(9,'story-6d642b6e',7,'q6','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是个戴小眼镜、爱穿蓝背带裤的男孩，他最喜欢奥特曼——不是打怪兽的那种，而是“数学奥特曼”！他总说：“光之力量=认真思考+勇敢尝试！”每天放学，他都会和玩具奥特曼一起“守护数字星球”。\n\n今天，奥特曼的通讯器突然亮起蓝光：“嘀嘀！紧急任务：请破解‘温度星’‘时钟塔’‘三角尺峡谷’和‘计算器飞船’四道谜题，才能激活彩虹能量盾，保护幼儿园的彩虹花圃不被寒流冻住！”冯玉桥立刻掏出他的“奥特曼数学笔记本”，上面正写着四道挑战题——原来，这是老师悄悄放进他书包的数学小任务！\n\n他先看“温度星”：-5℃比-25℃低？他摸摸小脸蛋：“冬天里，-25℃可比-5℃冷多啦！就像冰激凌在冰箱最冷格，比放冷藏格更硬更凉——所以-5℃其实‘高’一点，暖一点！”他点点头。再看“时钟塔”：2:55时针和分针夹角是120度吗？他拿出纸盘画了个钟面，发现分针指11，时针快到3但还没到，夹角明明更小！最后，“计算器飞船”上闪着CE键的光——他按过这个键，输错数字时一按就清掉，真像奥特曼的“净化光波”！而“三角尺峡谷”最难：一副三角尺只有30°、45°、60°、90°，拼不出115°（因为115不是这些角的和或差）。他深吸一口气，举起奥特曼玩具：“答案是D！CE键就是我们的纠错超能力！”\n\n第二天，冯玉桥在数学课上自信说出答案，老师笑着给他贴了一颗“奥特曼思考星”。放学时，他看见幼儿园的彩虹花圃开得更艳了——原来，认真解对一道题，也能让世界变得更明亮呢！\n\n【学习要点】  \n• 温度比较：负数越小，温度越低（-25℃＜-5℃）  \n• 钟面角度：会估算2:55时针与分针的大概夹角（约27.5°）  \n• 三角尺角度：标准三角尺只能拼出15°的整数倍角（如75°、105°），不能拼115°  \n• 计算器功能：CE键（Clear Entry）清除当前输入，不删全部','[{\"id\": \"q6\", \"answer\": \"\", \"content\": \"下列说法中正确的是（ ）。\\nA. 用一副三角尺画出 115°\\nB. 2:55 这一刻，时针与分针的夹角等于 120 度\\nC. -5℃比-25℃低\\nD. 用计算器计算时，输错了可以按 \\\\(\\\\boxed{CE}\\\\) 键清除\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:28:52.200','2026-02-12 10:28:52.200',NULL),(10,'story-06b69a7e',7,'q7','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是阳光小学四年级的小超人迷，他最爱和奥特曼一起“守护秩序”——不是打怪兽，而是帮大家把事情做得又快又准！他书包上贴着闪闪发光的奥特曼徽章，连铅笔盒都画着彩色光剑呢。\n\n一天放学后，冯玉桥和好朋友朵朵在校园小花园帮忙植树。老师说：“要种一排小树苗，得先找准‘领头的两个坑’，就像奥特曼发射光线前要对准目标一样！”他们挖好第一个坑，正要挖第二个时，发现地上画着一道神奇的“数学光波题”：原来这是奥特曼留下的“智慧考验”，只有答对，才能用“顺序光束”精准定位第二个坑的位置！题目是：“下面算式中，第一步要先算加法的是（ ）？”四个选项像四颗小星星，眨着眼睛等答案。\n\n冯玉桥戴上他的“思考眼镜”（其实是爸爸送的圆框眼镜），认真看每个算式：“A是加法和除法打架，但除法先站岗；C是乘法和除法手拉手，加法只能排队；D里括号最厉害，可先算的是减法……咦？B选项里有小括号，里面写着57+43——加法被括号‘请’到最前面啦！”他开心地拍手：“就是B！就像我们先手拉手确定两个起点，其他树坑才能排成直直的一行！”朵朵立刻按答案挖下第二个坑，两坑一连，果然成了完美的“植树基准线”！\n\n第二天，小树苗们挺直腰杆排成一列，风一吹，叶子沙沙响，好像在说：“谢谢冯玉桥的数学光波！”冯玉桥摸摸奥特曼徽章，心里暖暖的：原来学好数学，真的能帮大家种出最美的春天！\n\n【学习要点】  \n• 四则运算中，括号里的运算最先进行  \n• 小括号（ ）有“优先通行权”，里面的加法必须先算  \n• 解决实际问题时，数学规则就像“小指挥家”，帮我们理清步骤','[{\"id\": \"q7\", \"answer\": \"\", \"content\": \"下面算式中，第一步要先算加法的是（ ）。\\nA. \\\\(34+66\\\\div3\\\\)\\nB. \\\\(288-(57+43)\\\\)\\nC. \\\\(23\\\\times3+24\\\\div4\\\\)\\nD. \\\\(480\\\\div[16+(36-28)]\\\\)\\n\\n植树时，需要先确定两个坑的位置，以便使得其他的树坑能和他们排成一行。\\n\\n四年级数学试题 第1页（共6页）\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-12 10:29:17.350','2026-02-12 10:29:17.350',NULL),(11,'story-c9b39901',8,'','冯玉桥的数学奇遇记','基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。','冯玉桥是个爱穿蓝背带裤、总把橡皮擦捏成小星星的二年级小朋友。他最喜欢奥特曼——不是打怪兽的那种，而是“数学奥特曼”！他的书包里藏着一枚亮晶晶的“智慧光镯”，只要认真思考，镯子就会轻轻发暖，像奥特曼在悄悄给他加油！\n\n放学路上，冯玉桥发现校门口的“星光数学站”信箱里有一封银色信封，上面印着发光的奥特曼徽章。他好奇地打开，里面是一张画着长城和星星的卡片，还有一道题：“《长城谣》里唱‘四万万同胞心一样’，下面谁说错了？”四个选项像四颗小星星排成一排。冯玉桥歪着头：“四万万？是四万个‘万’吗？那得数好久呀……”\n\n他掏出小算盘，又拿出彩色小纸条：一张写“1万”，叠40张就是“四十万”？不对！他想起老师教过——“万”后面是“十万”“百万”“千万”“亿”。他用手指当小棒，边数边念：“1个万、2个万……10个万是十万，100个万是一百万……10000个万才是‘一亿’！”他眼睛一亮：“啊！‘四万万’就是4×10000×10000=4亿！所以C说‘是4个十万’——才40万呢，差远啦！”智慧光镯“叮”地暖了一下，闪出一道小彩虹。\n\n第二天，冯玉桥在班级“奥特曼小讲师”时间，用长城积木搭出数字阶梯，带着大家“千万、千万”地数：数1次是1000万，数40次正好是4亿！全班都举起小手：“我们也是四万万颗闪亮的心！”  \n\n【学习要点】  \n• “万”“十万”“百万”“千万”“亿”的进率关系（每相邻两个计数单位之间是10倍）  \n• “四万万”=4×10000×10000=4亿，是准确数，不是近似数  \n• 理解“4个十万”=40万，与“四万万”相差很大','[{\"id\": \"q1\", \"answer\": \"\", \"content\": \"《长城谣》是一首脍炙人口的爱国歌曲，其歌词中“四万万同胞心一样”，表达了全国人民团结一心、保家卫国的决心和信念。下面，关于“四万万”理解错误的是（　　）。  \\nA、 “四万万”是4亿  \\nB、 “四万万”是一个近似数  \\nC、 “四万万”是4个十万  \\nD、 从0开始，“千万、千万”地数，要数40次\", \"options\": [], \"analysis\": \"\", \"questionNumber\": 0}]','奥特曼','2026-02-14 10:45:46.559','2026-02-14 10:45:46.559',NULL);
/*!40000 ALTER TABLE `story_contents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `phone` varchar(20) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `nickname` varchar(50) DEFAULT NULL,
  `avatar_url` varchar(500) DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  `created_at` datetime(3) DEFAULT NULL,
  `updated_at` datetime(3) DEFAULT NULL,
  `deleted_at` datetime(3) DEFAULT NULL,
  `wechat_open_id` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `gender` tinyint DEFAULT '0',
  `birthday` date DEFAULT NULL,
  `subscription_level` tinyint DEFAULT '0',
  `subscription_expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_users_phone` (`phone`),
  KEY `idx_users_deleted_at` (`deleted_at`),
  KEY `idx_users_wechat_open_id` (`wechat_open_id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 ;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'13900139000','kratos_password','User_9000','',1,'2026-01-22 14:12:08.723','2026-01-22 14:12:08.723',NULL,NULL,NULL,0,NULL,0,NULL),(2,'15217331661','123456','User_1661','',1,'2026-01-22 14:28:24.752','2026-01-22 14:28:24.752',NULL,NULL,NULL,0,NULL,0,NULL),(4,'13969063726','password','User_3726','',1,'2026-01-22 14:35:26.349','2026-01-22 14:35:26.349',NULL,NULL,NULL,0,NULL,0,NULL),(5,'13969063740','password','User_3740','',1,'2026-01-22 14:35:40.222','2026-01-22 14:35:40.222',NULL,NULL,NULL,0,NULL,0,NULL),(6,'13969063788','password','User_3788','',1,'2026-01-22 14:36:28.864','2026-01-22 14:36:28.864',NULL,NULL,NULL,0,NULL,0,NULL),(7,'13969063802','password','User_3802','',1,'2026-01-22 14:36:42.444','2026-01-22 14:36:42.444',NULL,NULL,NULL,0,NULL,0,NULL),(8,'13500000002','password','User_0002','',1,'2026-01-22 14:42:38.907','2026-01-22 14:42:38.907',NULL,NULL,NULL,0,NULL,0,NULL),(10,'13500000003','password','User_0003','',1,'2026-01-22 14:45:38.456','2026-01-22 14:45:38.456',NULL,NULL,NULL,0,NULL,0,NULL),(11,'13500000004','password','User_0004','',1,'2026-01-22 14:49:20.051','2026-01-22 14:49:20.051',NULL,NULL,NULL,0,NULL,0,NULL),(12,'13500000006','password','User_0006','',1,'2026-01-22 14:52:08.090','2026-01-22 14:52:08.090',NULL,NULL,NULL,0,NULL,0,NULL),(13,'13500000011','password','User_0011','',1,'2026-01-23 00:33:53.307','2026-01-23 00:33:53.307',NULL,NULL,NULL,0,NULL,0,NULL),(17,'13512345678','password','User_5678','',1,'2026-01-23 00:35:40.886','2026-01-23 00:35:40.886',NULL,NULL,NULL,0,NULL,0,NULL),(18,'13599998888','password','User_8888','',1,'2026-01-23 00:35:46.304','2026-01-23 00:35:46.304',NULL,NULL,NULL,0,NULL,0,NULL),(20,'13812345678','123456','User_5678','',1,'2026-01-23 11:21:43.874','2026-01-23 11:21:43.874',NULL,NULL,NULL,0,NULL,0,NULL),(21,'18888888888','123456','User_8888','',1,'2026-01-23 11:25:50.521','2026-01-23 11:25:50.521',NULL,NULL,NULL,0,NULL,0,NULL),(22,'13698765432','123456','User_5432','',1,'2026-01-23 11:40:29.781','2026-01-23 11:40:29.781',NULL,NULL,NULL,0,NULL,0,NULL),(23,'13612344321','123456','User_4321','',1,'2026-01-23 11:43:23.420','2026-01-23 11:43:23.420',NULL,NULL,NULL,0,NULL,0,NULL),(24,'13100000001','password','User_0001','',1,'2026-01-23 11:53:46.325','2026-01-23 11:53:46.325',NULL,NULL,NULL,0,NULL,0,NULL),(26,'wxou9Bm18LZHlpq1O3XO','$2a$10$EeX6dHKMKEL1kLNVpHmrZOoQ/anBfBgbLEzA02rjjOhTJmn/RA86u','微信用户','/uploads/users/26/avatar.jpg',1,'2026-02-10 00:56:22.135','2026-02-16 21:10:58.753',NULL,'ou9Bm18LZHlpq1O3XORJGCiTzIiI','',0,NULL,0,NULL),(27,'wxootoy3TJNgG3_DJX67','$2a$10$aQrlUKh.ZCQsk2IUpGCcgOnXTnJqFTDm3Dh2d1Rq8uSgrHI46Mqgq','微信用户','',1,'2026-02-15 21:26:05.748','2026-02-15 21:26:05.748',NULL,'ootoy3TJNgG3_DJX67R8SlyITD2w','',0,NULL,0,NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'smartstudy'
--
--
-- WARNING: can't read the INFORMATION_SCHEMA.libraries table. It's most probably an old server 8.0.44.
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-17 17:06:26
