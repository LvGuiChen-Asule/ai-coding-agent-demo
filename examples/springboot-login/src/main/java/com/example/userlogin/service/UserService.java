package com.example.userlogin.service;

import com.example.userlogin.dto.LoginRequest;
import com.example.userlogin.dto.LoginResponse;
import com.example.userlogin.dto.RegisterRequest;
import com.example.userlogin.entity.User;

/**
 * 用户业务接口。
 */
public interface UserService {

    User register(RegisterRequest request);

    LoginResponse login(LoginRequest request);

    User getById(Long id);
}
