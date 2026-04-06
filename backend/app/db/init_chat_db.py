import pymysql

MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "dzy2001818"
DATABASE_NAME = "health_agent"

DDL = f"""
USE `{DATABASE_NAME}`;

-- 会话表
CREATE TABLE IF NOT EXISTS `chat_session` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `title` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `last_message_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_chat_session_user_id` (`user_id`),
    KEY `idx_chat_session_user_updated_at` (`user_id`, `updated_at`),
    KEY `idx_chat_session_user_last_message_at` (`user_id`, `last_message_at`),
    CONSTRAINT `fk_chat_session_user`
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 全量聊天记录表
CREATE TABLE IF NOT EXISTS `chat_message` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `session_id` BIGINT UNSIGNED NOT NULL,
    `role` ENUM('system', 'user', 'assistant') NOT NULL,
    `content` MEDIUMTEXT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_chat_message_user_id` (`user_id`),
    KEY `idx_chat_message_session_id` (`session_id`),
    KEY `idx_chat_message_session_created_at` (`session_id`, `created_at`),
    CONSTRAINT `fk_chat_message_user`
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_chat_message_session`
        FOREIGN KEY (`session_id`) REFERENCES `chat_session`(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户静态档案表
CREATE TABLE IF NOT EXISTS `user_profile` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `profile_text` TEXT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_profile_user_id` (`user_id`),
    CONSTRAINT `fk_user_profile_user`
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户长期记忆摘要表
CREATE TABLE IF NOT EXISTS `user_memory_summary` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `session_id` BIGINT UNSIGNED DEFAULT NULL,
    `summary_text` TEXT NOT NULL,
    `source_start_msg_id` BIGINT UNSIGNED DEFAULT NULL,
    `source_end_msg_id` BIGINT UNSIGNED DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_memory_summary_user_id` (`user_id`),
    KEY `idx_user_memory_summary_user_created_at` (`user_id`, `created_at`),
    KEY `idx_user_memory_summary_session_id` (`session_id`),
    CONSTRAINT `fk_user_memory_summary_user`
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_user_memory_summary_session`
        FOREIGN KEY (`session_id`) REFERENCES `chat_session`(`id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def main():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=DATABASE_NAME,
        autocommit=True,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            for stmt in [x.strip() for x in DDL.split(";") if x.strip()]:
                cursor.execute(stmt)
    finally:
        conn.close()

if __name__ == "__main__":
    main()