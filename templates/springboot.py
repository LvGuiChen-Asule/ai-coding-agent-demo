"""SpringBoot 用户登录模块模板（MyBatis + MySQL + REST API）。"""

from __future__ import annotations

import re
from typing import Any


def _java_class_name(project_name: str) -> str:
    """将项目名转成驼峰类名，如 user-login -> UserLogin。"""
    words = re.split(r"[-_\s]+", project_name)
    return "".join(w.capitalize() for w in words if w)


def render_springboot(project: dict[str, Any]) -> dict[str, str]:
    """生成 SpringBoot 用户登录模块的所有文件（path -> content）。"""
    artifact = project.get("artifact", "user-login")
    group = project.get("group", "com.example")
    package = project.get("package", "com.example.login")
    app_name = _java_class_name(artifact) or "UserLogin"
    pkg_dir = package.replace(".", "/")
    files: dict[str, str] = {}

    files[f"pom.xml"] = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.5</version>
        <relativePath/>
    </parent>

    <groupId>{group}</groupId>
    <artifactId>{artifact}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>{artifact}</name>
    <description>AI Coding Agent Demo 生成</description>

    <properties>
        <java.version>17</java.version>
        <mybatis.version>3.0.3</mybatis.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.mybatis.spring.boot</groupId>
            <artifactId>mybatis-spring-boot-starter</artifactId>
            <version>${{mybatis.version}}</version>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""

    files[f"src/main/resources/application.yml"] = f"""server:
  port: 8080

spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://localhost:3306/{artifact.replace('-', '_')}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
    username: root
    password: root

mybatis:
  mapper-locations: classpath:mapper/*.xml
  type-aliases-package: {package}.entity

logging:
  level:
    {package}.mapper: debug
"""

    files[f"src/main/resources/mapper/UserMapper.xml"] = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{package}.mapper.UserMapper">

    <select id="findByUsername" resultType="User">
        SELECT id, username, password, email, created_at
        FROM sys_user
        WHERE username = #{{username}}
    </select>

    <insert id="insert" parameterType="User" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO sys_user (username, password, email, created_at)
        VALUES (#{{username}}, #{{password}}, #{{email}}, #{{createdAt}})
    </insert>

    <select id="searchByKeyword" resultType="User">
        SELECT id, username, password, email, created_at
        FROM sys_user
        WHERE username LIKE '%${{keyword}}%'
    </select>
</mapper>
"""

    files[f"src/main/java/{pkg_dir}/{app_name}Application.java"] = f"""package {package};

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 用户登录模块启动类（AI Coding Agent Demo 生成）。
 */
@SpringBootApplication
@MapperScan("{package}.mapper")
public class {app_name}Application {{

    public static void main(String[] args) {{
        SpringApplication.run({app_name}Application.class, args);
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/entity/User.java"] = f"""package {package}.entity;

import java.time.LocalDateTime;

/**
 * 用户实体。
 */
public class User {{

    private Long id;
    private String username;
    private String password;
    private String email;
    private LocalDateTime createdAt;

    public Long getId() {{
        return id;
    }}

    public void setId(Long id) {{
        this.id = id;
    }}

    public String getUsername() {{
        return username;
    }}

    public void setUsername(String username) {{
        this.username = username;
    }}

    public String getPassword() {{
        return password;
    }}

    public void setPassword(String password) {{
        this.password = password;
    }}

    public String getEmail() {{
        return email;
    }}

    public void setEmail(String email) {{
        this.email = email;
    }}

    public LocalDateTime getCreatedAt() {{
        return createdAt;
    }}

    public void setCreatedAt(LocalDateTime createdAt) {{
        this.createdAt = createdAt;
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/dto/LoginRequest.java"] = f"""package {package}.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 登录请求。
 */
public class LoginRequest {{

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;

    public String getUsername() {{
        return username;
    }}

    public void setUsername(String username) {{
        this.username = username;
    }}

    public String getPassword() {{
        return password;
    }}

    public void setPassword(String password) {{
        this.password = password;
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/dto/RegisterRequest.java"] = f"""package {package}.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 注册请求。
 */
public class RegisterRequest {{

    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 20, message = "用户名长度需在 3-20 之间")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 32, message = "密码长度需在 6-32 之间")
    private String password;

    @Email(message = "邮箱格式不正确")
    private String email;

    public String getUsername() {{
        return username;
    }}

    public void setUsername(String username) {{
        this.username = username;
    }}

    public String getPassword() {{
        return password;
    }}

    public void setPassword(String password) {{
        this.password = password;
    }}

    public String getEmail() {{
        return email;
    }}

    public void setEmail(String email) {{
        this.email = email;
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/dto/LoginResponse.java"] = f"""package {package}.dto;

/**
 * 登录响应。
 */
public class LoginResponse {{

    private String token;
    private String username;
    private String message;

    public LoginResponse() {{
    }}

    public LoginResponse(String token, String username, String message) {{
        this.token = token;
        this.username = username;
        this.message = message;
    }}

    public String getToken() {{
        return token;
    }}

    public void setToken(String token) {{
        this.token = token;
    }}

    public String getUsername() {{
        return username;
    }}

    public void setUsername(String username) {{
        this.username = username;
    }}

    public String getMessage() {{
        return message;
    }}

    public void setMessage(String message) {{
        this.message = message;
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/common/ApiResponse.java"] = f"""package {package}.common;

/**
 * 统一响应包装。
 */
public class ApiResponse<T> {{

    private int code;
    private String message;
    private T data;

    public ApiResponse() {{
    }}

    public ApiResponse(int code, String message, T data) {{
        this.code = code;
        this.message = message;
        this.data = data;
    }}

    public static <T> ApiResponse<T> ok(T data) {{
        return new ApiResponse<>(200, "success", data);
    }}

    public static <T> ApiResponse<T> error(int code, String message) {{
        return new ApiResponse<>(code, message, null);
    }}

    public int getCode() {{
        return code;
    }}

    public void setCode(int code) {{
        this.code = code;
    }}

    public String getMessage() {{
        return message;
    }}

    public void setMessage(String message) {{
        this.message = message;
    }}

    public T getData() {{
        return data;
    }}

    public void setData(T data) {{
        this.data = data;
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/mapper/UserMapper.java"] = f"""package {package}.mapper;

import {package}.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 用户数据访问层。
 */
@Mapper
public interface UserMapper {{

    User findByUsername(@Param("username") String username);

    int insert(User user);

    List<User> searchByKeyword(@Param("keyword") String keyword);
}}
"""

    files[f"src/main/java/{pkg_dir}/service/UserService.java"] = f"""package {package}.service;

import {package}.dto.LoginRequest;
import {package}.dto.LoginResponse;
import {package}.dto.RegisterRequest;
import {package}.entity.User;

/**
 * 用户业务接口。
 */
public interface UserService {{

    User register(RegisterRequest request);

    LoginResponse login(LoginRequest request);

    User getById(Long id);
}}
"""

    files[f"src/main/java/{pkg_dir}/service/impl/UserServiceImpl.java"] = f"""package {package}.service.impl;

import {package}.dto.LoginRequest;
import {package}.dto.LoginResponse;
import {package}.dto.RegisterRequest;
import {package}.entity.User;
import {package}.mapper.UserMapper;
import {package}.service.UserService;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.UUID;

/**
 * 用户业务实现。
 */
@Service
public class UserServiceImpl implements UserService {{

    private final UserMapper userMapper;

    public UserServiceImpl(UserMapper userMapper) {{
        this.userMapper = userMapper;
    }}

    @Override
    public User register(RegisterRequest request) {{
        if (userMapper.findByUsername(request.getUsername()) != null) {{
            throw new IllegalArgumentException("用户名已存在");
        }}
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(hashPassword(request.getPassword()));
        user.setEmail(request.getEmail());
        user.setCreatedAt(LocalDateTime.now());
        userMapper.insert(user);
        return user;
    }}

    @Override
    public LoginResponse login(LoginRequest request) {{
        User user = userMapper.findByUsername(request.getUsername());
        if (user == null || !user.getPassword().equals(hashPassword(request.getPassword()))) {{
            throw new IllegalArgumentException("用户名或密码错误");
        }}
        String token = UUID.randomUUID().toString().replace("-", "");
        return new LoginResponse(token, user.getUsername(), "登录成功");
    }}

    @Override
    public User getById(Long id) {{
        return userMapper.findByUsername("id:" + id);
    }}

    private String hashPassword(String raw) {{
        // TODO: 生产环境请替换为 BCrypt 加盐哈希
        try {{
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        }} catch (Exception e) {{
            throw new IllegalStateException("密码加密失败", e);
        }}
    }}
}}
"""

    files[f"src/main/java/{pkg_dir}/controller/UserController.java"] = f"""package {package}.controller;

import {package}.common.ApiResponse;
import {package}.dto.LoginRequest;
import {package}.dto.LoginResponse;
import {package}.dto.RegisterRequest;
import {package}.entity.User;
import {package}.service.UserService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

/**
 * 用户认证接口。
 */
@RestController
@RequestMapping("/api/auth")
public class UserController {{

    private final UserService userService;

    public UserController(UserService userService) {{
        this.userService = userService;
    }}

    @PostMapping("/register")
    public ApiResponse<User> register(@Valid @RequestBody RegisterRequest request) {{
        if (request.getUsername() == null || request.getUsername().trim().isEmpty()) {{
            return ApiResponse.error(400, "用户名不能为空");
        }}
        if (request.getPassword() == null || request.getPassword().trim().isEmpty()) {{
            return ApiResponse.error(400, "密码不能为空");
        }}
        return ApiResponse.ok(userService.register(request));
    }}

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {{
        return ApiResponse.ok(userService.login(request));
    }}

    @GetMapping("/users/{{id}}")
    public ApiResponse<User> getUser(@PathVariable Long id) {{
        return ApiResponse.ok(userService.getById(id));
    }}
}}
"""

    files[f"src/main/resources/schema.sql"] = f"""-- 用户登录模块数据库脚本（AI Coding Agent Demo 生成）
CREATE DATABASE IF NOT EXISTS {artifact.replace('-', '_')}
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE {artifact.replace('-', '_')};

DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    username   VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名',
    password   VARCHAR(128) NOT NULL COMMENT '密码（SHA-256 哈希）',
    email      VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
"""

    files[f"src/test/java/{pkg_dir}/UserControllerTest.java"] = f"""package {package};

import com.fasterxml.jackson.databind.ObjectMapper;
import {package}.dto.LoginRequest;
import {package}.dto.RegisterRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 用户认证接口测试。
 */
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {{

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void registerShouldReturnUser() throws Exception {{
        RegisterRequest request = new RegisterRequest();
        request.setUsername("alice");
        request.setPassword("secret123");
        request.setEmail("alice@example.com");

        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.username").value("alice"));
    }}

    @Test
    void loginShouldReturnToken() throws Exception {{
        LoginRequest request = new LoginRequest();
        request.setUsername("alice");
        request.setPassword("secret123");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.token").isNotEmpty());
    }}
}}
"""

    return files


def apply_captcha_to_springboot(files: dict[str, str]) -> dict[str, str]:
    """模拟「增加验证码校验」的代码修改：给实体 / DTO / SQL / 服务层打补丁。"""
    out = dict(files)

    # 1. User 实体增加 captcha 字段
    key = next((k for k in out if k.endswith("entity/User.java")), None)
    if key:
        content = out[key]
        content = content.replace(
            "    private String email;",
            "    private String email;\n    private String captcha;",
        )
        content = content.replace(
            "    public String getEmail() {{",
            "    public String getCaptcha() {{\n        return captcha;\n    }}\n\n"
            "    public void setCaptcha(String captcha) {{\n        this.captcha = captcha;\n    }}\n\n"
            "    public String getEmail() {{",
        )
        out[key] = content

    # 2. LoginRequest 增加验证码字段
    key = next((k for k in out if k.endswith("dto/LoginRequest.java")), None)
    if key:
        content = out[key]
        content = content.replace(
            "    private String password;",
            "    private String password;\n\n    @NotBlank(message = \"验证码不能为空\")\n    private String captcha;",
        )
        content = content.replace(
            "    public String getPassword() {{",
            "    public String getCaptcha() {{\n        return captcha;\n    }}\n\n"
            "    public void setCaptcha(String captcha) {{\n        this.captcha = captcha;\n    }}\n\n"
            "    public String getPassword() {{",
        )
        out[key] = content

    # 3. schema.sql 增加 captcha 列
    key = next((k for k in out if k.endswith("schema.sql")), None)
    if key:
        out[key] = out[key].replace(
            "    email      VARCHAR(100) DEFAULT NULL COMMENT '邮箱',",
            "    email      VARCHAR(100) DEFAULT NULL COMMENT '邮箱',\n"
            "    captcha    VARCHAR(10)  DEFAULT NULL COMMENT '登录验证码',",
        )

    # 4. UserServiceImpl.login 增加验证码校验
    key = next((k for k in out if k.endswith("service/impl/UserServiceImpl.java")), None)
    if key:
        content = out[key]
        content = content.replace(
            "        User user = userMapper.findByUsername(request.getUsername());",
            "        // 验证码校验（Demo：模拟校验，生产环境请接入 Redis 存储）\n"
            "        if (request.getCaptcha() == null || request.getCaptcha().length() != 4) {{\n"
            "            throw new IllegalArgumentException(\"验证码错误\");\n"
            "        }}\n"
            "        User user = userMapper.findByUsername(request.getUsername());",
        )
        out[key] = content

    # 5. 测试类补充验证码
    key = next((k for k in out if k.endswith("UserControllerTest.java")), None)
    if key:
        content = out[key]
        content = content.replace(
            "        request.setPassword(\"secret123\");\n\n"
            "        mockMvc.perform(post(\"/api/auth/login\")",
            "        request.setPassword(\"secret123\");\n"
            "        request.setCaptcha(\"8888\");\n\n"
            "        mockMvc.perform(post(\"/api/auth/login\")",
        )
        out[key] = content

    return out


def apply_token_to_springboot(files: dict[str, str]) -> dict[str, str]:
    """模拟「登录返回 JWT Token」的代码修改。"""
    out = dict(files)
    key = next((k for k in out if k.endswith("dto/LoginResponse.java")), None)
    if key:
        out[key] = out[key].replace(
            "    private String token;",
            "    // JWT Token（Demo 使用 UUID 模拟，生产环境请使用 jjwt 生成标准 JWT）\n    private String token;",
        )
    key = next((k for k in out if k.endswith("service/impl/UserServiceImpl.java")), None)
    if key:
        out[key] = out[key].replace(
            "        String token = UUID.randomUUID().toString().replace(\"-\", \"\");",
            "        // 模拟 JWT：header.payload.signature\n"
            "        String token = \"eyJhbGciOiJIUzI1NiJ9.\" + UUID.randomUUID().toString().replace(\"-\", \"\") + \".demo-signature\";",
        )
    return out

