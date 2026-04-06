import pymysql

MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "dzy2001818"
DATABASE_NAME = "health_agent"

DDL = f"""
USE `{DATABASE_NAME}`;

DROP TABLE IF EXISTS `user_profile_memory`;

CREATE TABLE `user_profile_memory` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,

    `age` VARCHAR(50) NULL,
    `gender` VARCHAR(20) NULL,
    `chronic_disease` TEXT NULL,
    `allergy_history` TEXT NULL,
    `long_term_medications` TEXT NULL,
    `pregnancy_planning` VARCHAR(100) NULL,
    `surgical_history` TEXT NULL,
    `long_term_lifestyle_traits` TEXT NULL,

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_profile_memory_user_id` (`user_id`),
    KEY `idx_user_profile_memory_user_id` (`user_id`),

    CONSTRAINT `fk_user_profile_memory_user_id`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE
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

            cursor.execute("DESC `user_profile_memory`")
            columns = cursor.fetchall()

        print("user_profile_memory 表已重建成功")
        print("当前字段：")
        for col in columns:
            print(col)
    finally:
        conn.close()

if __name__ == "__main__":
    main()