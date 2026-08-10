package com.example.userlogin.mapper;

import com.example.userlogin.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 用户数据访问层。
 */
@Mapper
public interface UserMapper {

    User findByUsername(@Param("username") String username);

    int insert(User user);

    List<User> searchByKeyword(@Param("keyword") String keyword);
}
