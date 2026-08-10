"""Planner Agent：自然语言需求 -> 结构化任务规划（Chain of Thought）。"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from .llm import BaseLLMProvider
from .prompts import PLANNER_SYSTEM
from .types import TaskPlan, TaskStep


def detect_stack(requirement: str) -> str:
    """根据需求关键词识别目标技术栈。"""
    text = requirement.lower()
    if any(k in text for k in ("spring", "springboot", "spring boot", "java", "maven", "mybatis")):
        return "springboot"
    if any(k in text for k in ("node", "express", "javascript", "js", "npm")):
        return "node"
    if any(k in text for k in ("python", "fastapi", "flask", "django")):
        return "python"
    return "springboot"  # 默认演示 SpringBoot 工作流


def detect_project_name(requirement: str, stack: str) -> str:
    """从需求中抽取项目名；未命中则按技术栈给默认名。"""
    defaults = {"springboot": "user-login", "python": "user-api", "node": "user-api"}
    text = requirement
    # 去掉祈使前缀（帮我 / 创建 / 生成 / 开发 / 实现 / 做一个 ...）
    for prefix in (
        "帮我创建一个", "帮我生成一个", "帮我开发一个", "帮我实现一个", "帮我做一个", "帮我创建", "帮我",
        "创建一个", "生成一个", "开发一个", "实现一个", "做一个", "创建", "生成", "开发", "实现", "做",
    ):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.strip()
    # 去掉结尾的业务后缀
    match = re.search(r"^([\w\u4e00-\u9fa5-]+?)(?:模块|系统|项目|接口|后端|应用)?$", text)
    name = match.group(1) if match else text
    # 去掉技术栈词（SpringBoot / Java / FastAPI ...）
    for word in ("springboot", "spring boot", "spring", "java", "python",
                 "fastapi", "flask", "node", "nodejs", "express", "javascript"):
        name = re.sub(re.escape(word), "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", "-", name).strip("-_ ")

    # 中文需求映射为英文项目名（Maven artifact / Python 包名更规范）
    zh_map = {
        "用户登录": "user-login",
        "登录认证": "auth-service",
        "用户管理": "user-service",
        "用户": "user-api",
        "订单": "order-service",
        "博客": "blog",
        "待办": "todo",
    }
    for zh, en in zh_map.items():
        if zh in name:
            return en

    if name and not any("\u4e00" <= ch <= "\u9fff" for ch in name):
        return name.lower()
    return defaults.get(stack, "demo-app")


def _project_meta(project_name: str, stack: str) -> dict[str, Any]:
    """生成各技术栈的项目元信息。"""
    if stack == "springboot":
        return {
            "artifact": project_name,
            "group": "com.example",
            "package": f"com.example.{project_name.replace('-', '')}",
        }
    if stack == "python":
        pkg = project_name.replace("-", "_")
        return {"module": project_name, "pkg": pkg}
    return {"module": project_name}


def _step(step_id: int, title: str, description: str, step_type: str, files: list[str], note: str = "") -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "description": description,
        "type": step_type,
        "detail": {"files": files, "note": note},
    }


def mock_plan(requirement: str, stack: str = "") -> dict[str, Any]:
    """离线规划：按技术栈生成确定性的任务步骤。"""
    stack = stack or detect_stack(requirement)
    project_name = detect_project_name(requirement, stack)
    meta = _project_meta(project_name, stack)

    # 修改类需求 -> 单一 modify 步骤
    if any(k in requirement for k in ("修改", "优化", "重构", "增加", "添加")):
        intent = "add_captcha" if any(k in requirement for k in ("验证码", "captcha")) else (
            "add_token" if any(k in requirement for k in ("token", "jwt", "登录态")) else "generic"
        )
        target = "Controller/Service/Entity/DTO/SQL"
        steps = [
            _step(
                1,
                f"修改登录逻辑（{intent}）",
                f"定位 {target} 中与登录相关的代码，读取后原地修改并保存",
                "modify",
                [],
                intent,
            )
        ]
        return {"task": requirement, "stack": stack, "project": meta, "intent": intent, "steps": steps}

    if stack == "springboot":
        pkg = meta["package"]
        pkg_dir = pkg.replace(".", "/")
        steps = [
            _step(1, "创建 Maven 工程骨架", "生成 pom.xml、application.yml 与启动类", "codegen",
                  ["pom.xml", "src/main/resources/application.yml", f"src/main/java/{pkg_dir}/{_class_name(project_name)}Application.java"]),
            _step(2, "创建 User 实体类", "定义用户实体字段与 getter/setter", "codegen",
                  [f"src/main/java/{pkg_dir}/entity/User.java"]),
            _step(3, "创建 DTO 与统一响应", "LoginRequest / RegisterRequest / LoginResponse / ApiResponse", "codegen",
                  [f"src/main/java/{pkg_dir}/dto/LoginRequest.java",
                   f"src/main/java/{pkg_dir}/dto/RegisterRequest.java",
                   f"src/main/java/{pkg_dir}/dto/LoginResponse.java",
                   f"src/main/java/{pkg_dir}/common/ApiResponse.java"]),
            _step(4, "创建 Mapper 数据访问层", "UserMapper 接口与 XML 映射", "codegen",
                  [f"src/main/java/{pkg_dir}/mapper/UserMapper.java",
                   "src/main/resources/mapper/UserMapper.xml"]),
            _step(5, "创建 Service 业务逻辑", "注册 / 登录 / 查询用户", "codegen",
                  [f"src/main/java/{pkg_dir}/service/UserService.java",
                   f"src/main/java/{pkg_dir}/service/impl/UserServiceImpl.java"]),
            _step(6, "创建 Controller 接口", "注册、登录、查询 REST 接口", "codegen",
                  [f"src/main/java/{pkg_dir}/controller/UserController.java"]),
            _step(7, "编写 MySQL 建表 SQL", "生成 schema.sql", "codegen",
                  ["src/main/resources/schema.sql"]),
            _step(8, "编写测试代码", "MockMvc 注册 / 登录接口测试", "codegen",
                  [f"src/test/java/{pkg_dir}/UserControllerTest.java"]),
            _step(9, "运行测试并静态验证", "执行 mvn test；环境缺失时做静态结构校验", "test", []),
        ]
    elif stack == "python":
        pkg = meta["pkg"]
        steps = [
            _step(1, "创建 Python 工程骨架", "requirements.txt 与包结构", "codegen",
                  ["requirements.txt", f"{pkg}/__init__.py"]),
            _step(2, "创建数据模型", "User dataclass 与内存存储", "codegen",
                  [f"{pkg}/models.py"]),
            _step(3, "创建请求 / 响应结构", "RegisterRequest / LoginRequest / LoginResponse", "codegen",
                  [f"{pkg}/schemas.py"]),
            _step(4, "创建业务逻辑", "注册 / 登录 / 查询", "codegen",
                  [f"{pkg}/user_service.py"]),
            _step(5, "创建 FastAPI 接口", "REST API 入口", "codegen",
                  [f"{pkg}/main.py"]),
            _step(6, "编写单元测试", "unittest 业务层测试", "codegen",
                  [f"{pkg}/test_user_service.py"]),
            _step(7, "运行测试", "python -m unittest 验证业务逻辑", "test", []),
        ]
    else:
        steps = [
            _step(1, "创建 Node.js 工程骨架", "package.json", "codegen",
                  ["package.json"]),
            _step(2, "创建用户数据模型", "内存 Map 存储与密码哈希", "codegen",
                  ["models/User.js"]),
            _step(3, "创建业务逻辑", "注册 / 登录服务", "codegen",
                  ["services/userService.js"]),
            _step(4, "创建 Express 接口", "REST API 路由与服务入口", "codegen",
                  ["routes/user.js", "server.js"]),
            _step(5, "编写单元测试", "node:test 业务层测试", "codegen",
                  ["test/user-service.test.js"]),
            _step(6, "运行测试", "npm test 验证业务逻辑", "test", []),
        ]

    return {"task": requirement, "stack": stack, "project": meta, "intent": "create", "steps": steps}


def _class_name(project_name: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[-_\s]+", project_name) if w)


class PlannerAgent:
    """Planner Agent：调用 LLM 做 Chain of Thought 规划，失败时回退离线规划。"""

    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    def plan(self, requirement: str, stack: Optional[str] = None) -> TaskPlan:
        stack = stack or detect_stack(requirement)
        project_name = detect_project_name(requirement, stack)
        meta = _project_meta(project_name, stack)
        user = json.dumps(
            {
                "requirement": requirement,
                "stack": stack,
                "project": meta,
                "workspace_files": [],
            },
            ensure_ascii=False,
        )
        try:
            raw = self.provider.complete_json(PLANNER_SYSTEM, user, temperature=0.2)
            steps = [
                TaskStep(
                    id=int(s.get("id", i + 1)),
                    title=str(s.get("title", f"步骤 {i + 1}")),
                    description=str(s.get("description", "")),
                    step_type=str(s.get("type", "codegen")),
                    detail=s.get("detail", {}),
                )
                for i, s in enumerate(raw.get("steps", []))
            ]
            if not steps:
                raise ValueError("LLM 规划结果为空")
            plan_stack = str(raw.get("stack", stack))
            task = str(raw.get("task", requirement))
            return TaskPlan(
                task=task,
                steps=steps,
                meta={"stack": plan_stack, "project": raw.get("project", meta), "source": "llm"},
            )
        except Exception:
            # 解析失败 / 无 Key：回退到离线确定性规划，保证工作流不中断
            raw = mock_plan(requirement, stack)
            return TaskPlan(
                task=raw["task"],
                steps=[TaskStep(**s) for s in raw["steps"]],
                meta={"stack": raw["stack"], "project": raw["project"], "source": "mock"},
            )
