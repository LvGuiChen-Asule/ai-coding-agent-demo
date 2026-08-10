# Code Review Report

**综合评分：41/100**

共发现 5 个问题（critical 1 / high 1 / medium 2 / low 1），综合评分 41/100。

## 问题清单

| 严重级别 | 文件 | 问题 | 建议 |
| --- | --- | --- | --- |
| critical | `src/main/resources/mapper/UserMapper.xml` | SQL 注入风险 | 改为 #{keyword} 参数化查询，或对关键字做白名单 / 转义处理。 |
| medium | `src/main/java/com/example/userlogin/service/impl/UserServiceImpl.java` | 密码哈希强度不足 | 改用 BCrypt / Argon2 加盐哈希（如 spring-security-crypto 的 BCryptPasswordEncoder）。 |
| high | `src/main/java/com/example/userlogin/service/impl/UserServiceImpl.java` | 查询逻辑错误 | 新增 findById 方法并使用 #{id} 参数化查询。 |
| low | `src/main/java/com/example/userlogin/service/impl/UserServiceImpl.java` | 遗留 TODO 标记 | 按标记内容完善实现后移除。 |
| medium | `(全局)` | 存在重复代码 | 提取公共方法 / 基类 / 工具类消除重复。 |

## 亮点

- 分层清晰：Controller / Service / Mapper 职责分离
- 接口层使用了 Bean Validation 参数校验
- 包含 MockMvc 接口测试，覆盖注册与登录主流程
- 数据写入使用参数化 SQL，整体上避免了拼接注入

## 优化建议

- 优先修复 critical / high 级别问题（SQL 注入、明文口令、查询逻辑）。
- 密码存储升级为 BCrypt，并移除硬编码配置。
- 补充更多边界用例（重复注册、空参数、非法字符）。