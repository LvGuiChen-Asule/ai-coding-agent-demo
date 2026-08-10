package com.example.userlogin.service.impl;

import com.example.userlogin.dto.LoginRequest;
import com.example.userlogin.dto.LoginResponse;
import com.example.userlogin.dto.RegisterRequest;
import com.example.userlogin.entity.User;
import com.example.userlogin.mapper.UserMapper;
import com.example.userlogin.service.UserService;
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
public class UserServiceImpl implements UserService {

    private final UserMapper userMapper;

    public UserServiceImpl(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    @Override
    public User register(RegisterRequest request) {
        if (userMapper.findByUsername(request.getUsername()) != null) {
            throw new IllegalArgumentException("用户名已存在");
        }
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(hashPassword(request.getPassword()));
        user.setEmail(request.getEmail());
        user.setCreatedAt(LocalDateTime.now());
        userMapper.insert(user);
        return user;
    }

    @Override
    public LoginResponse login(LoginRequest request) {
        User user = userMapper.findByUsername(request.getUsername());
        if (user == null || !user.getPassword().equals(hashPassword(request.getPassword()))) {
            throw new IllegalArgumentException("用户名或密码错误");
        }
        String token = UUID.randomUUID().toString().replace("-", "");
        return new LoginResponse(token, user.getUsername(), "登录成功");
    }

    @Override
    public User getById(Long id) {
        return userMapper.findByUsername("id:" + id);
    }

    private String hashPassword(String raw) {
        // TODO: 生产环境请替换为 BCrypt 加盐哈希
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (Exception e) {
            throw new IllegalStateException("密码加密失败", e);
        }
    }
}
