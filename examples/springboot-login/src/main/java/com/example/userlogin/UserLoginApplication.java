package com.example.userlogin;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 用户登录模块启动类（AI Coding Agent Demo 生成）。
 */
@SpringBootApplication
@MapperScan("com.example.userlogin.mapper")
public class UserLoginApplication {

    public static void main(String[] args) {
        SpringApplication.run(UserLoginApplication.class, args);
    }
}
