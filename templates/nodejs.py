"""Node.js 用户模块模板（测试使用 node:test，Node 18+ 可运行）。"""

from __future__ import annotations

from typing import Any


def render_nodejs(project: dict[str, Any]) -> dict[str, str]:
    name = project.get("module", "user-api")
    files: dict[str, str] = {}

    files[f"package.json"] = f"""{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "AI Coding Agent Demo 生成",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "test": "node --test test/"
  }},
  "dependencies": {{
    "express": "^4.19.0"
  }}
}}
"""

    files[f"models/User.js"] = """// 用户数据模型（内存存储，Demo 用）
const users = new Map();
let nextId = 1;

function hashPassword(raw) {
  // TODO: 生产环境请使用 bcrypt
  const { createHash } = require("node:crypto");
  return createHash("sha256").update(raw).digest("hex");
}

function findByUsername(username) {
  return users.get(username) || null;
}

function create({ username, password, email = "" }) {
  if (findByUsername(username)) {
    const err = new Error("用户名已存在");
    err.status = 400;
    throw err;
  }
  const user = {
    id: nextId++,
    username,
    passwordHash: hashPassword(password),
    email,
    createdAt: new Date().toISOString(),
  };
  users.set(username, user);
  return user;
}

module.exports = { create, findByUsername, hashPassword };
"""

    files[f"services/userService.js"] = """const { create, findByUsername, hashPassword } = require("../models/User");
const { randomBytes } = require("node:crypto");

function register(body) {
  if (!body.username || body.username.length < 3) {
    const err = new Error("用户名长度至少 3 位");
    err.status = 400;
    throw err;
  }
  if (!body.password || body.password.length < 6) {
    const err = new Error("密码长度至少 6 位");
    err.status = 400;
    throw err;
  }
  return create(body);
}

function login(body) {
  const user = findByUsername(body.username);
  if (!user || user.passwordHash !== hashPassword(body.password)) {
    const err = new Error("用户名或密码错误");
    err.status = 401;
    throw err;
  }
  return { token: randomBytes(16).toString("hex"), username: user.username };
}

module.exports = { register, login };
"""

    files[f"routes/user.js"] = """const express = require("express");
const { register, login } = require("../services/userService");

const router = express.Router();

router.post("/register", (req, res) => {
  try {
    const user = register(req.body || {});
    res.json({ code: 200, message: "success", data: user });
  } catch (err) {
    res.status(err.status || 500).json({ code: err.status || 500, message: err.message });
  }
});

router.post("/login", (req, res) => {
  try {
    res.json({ code: 200, message: "success", data: login(req.body || {}) });
  } catch (err) {
    res.status(err.status || 500).json({ code: err.status || 500, message: err.message });
  }
});

module.exports = router;
"""

    files[f"server.js"] = """const express = require("express");
const userRouter = require("./routes/user");

const app = express();
app.use(express.json());
app.use("/api/auth", userRouter);

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Server running at http://localhost:${port}`));
"""

    files[f"test/user-service.test.js"] = """const test = require("node:test");
const assert = require("node:assert/strict");
const { register, login } = require("../services/userService");

test("注册成功返回用户且密码已哈希", () => {
  const user = register({ username: "alice", password: "secret123", email: "alice@example.com" });
  assert.equal(user.username, "alice");
  assert.notEqual(user.passwordHash, "secret123");
});

test("重复用户名注册报错", () => {
  register({ username: "bob", password: "secret123" });
  assert.throws(() => register({ username: "bob", password: "secret456" }), /用户名已存在/);
});

test("登录成功返回 token", () => {
  register({ username: "alice", password: "secret123" });
  const resp = login({ username: "alice", password: "secret123" });
  assert.ok(resp.token);
});

test("密码错误登录失败", () => {
  register({ username: "alice", password: "secret123" });
  assert.throws(() => login({ username: "alice", password: "wrong" }), /用户名或密码错误/);
});
"""

    return files

