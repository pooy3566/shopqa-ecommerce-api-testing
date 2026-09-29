# ShopQA 电商 API 质量保障项目

基于 FastAPI 电商后端的测试工程改造项目，覆盖认证、商品、订单、权限和库存一致性场景。

## 项目定位

应用底座来自 [SeyiDan/enterprise-ecommerce-api](https://github.com/SeyiDan/enterprise-ecommerce-api)，遵循 MIT License。原应用代码和基础测试结构作为被测系统保留；本人的改造集中在测试设计、业务边界回归、库存一致性验证和中文测试文档。

## 个人新增内容

- `docs/test-plan.md`：测试范围、风险识别、等价类、边界值和权限矩阵；
- `docs/test-cases.md`：订单、认证和权限的核心手工用例；
- `tests/test_business_boundaries.py`：数量为 0 的参数校验、成功下单后的库存扣减；
- `QUICKSTART-中文.md`：本地环境创建和回归测试说明；
- `.github/workflows/ci.yml`：沿用并验证 pytest + coverage 的 CI 流程。

## 技术栈

Python、FastAPI、SQLAlchemy、pytest、pytest-cov、SQLite 测试隔离、GitHub Actions。

## 本地验证

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

当前本地结果：`44 passed`。

只运行个人新增的边界用例：

```powershell
pytest -m integration tests/test_business_boundaries.py
```

## API 快速入口

启动服务后可访问：

- Swagger UI：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`
- 订单接口：`POST /api/v1/orders/`

## 隐私与安全

- `.env`、本地数据库、测试报告、虚拟环境和缓存目录均不会提交；
- `.env.example` 只提供字段示例，不包含真实密码、令牌或连接凭据；
- 文档和测试中的邮箱为虚构占位内容，不对应真实个人；
- 详见 [docs/隐私检查说明.md](docs/隐私检查说明.md) 和 [SECURITY.md](SECURITY.md)。

## 许可证与来源

本项目保留上游 MIT License，并在 [docs/README-个人改造说明.md](docs/README-个人改造说明.md) 中记录参考仓库和个人改造边界。
