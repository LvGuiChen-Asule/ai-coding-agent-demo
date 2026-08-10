-- 用户登录模块数据库脚本（AI Coding Agent Demo 生成）
CREATE DATABASE IF NOT EXISTS user_login
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE user_login;

DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    username   VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名',
    password   VARCHAR(128) NOT NULL COMMENT '密码（SHA-256 哈希）',
    email      VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
