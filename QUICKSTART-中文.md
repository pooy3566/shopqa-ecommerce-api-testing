# ShopQA 本地运行说明

## 1. 创建环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. 执行回归测试

```powershell
pytest
```

只运行个人补充的业务边界用例：

```powershell
pytest -m integration tests/test_business_boundaries.py
```

## 3. 说明

项目底座来自 `SeyiDan/enterprise-ecommerce-api`，保留 MIT License。新增测试计划、手工用例、业务边界和库存一致性回归测试属于个人改造内容。
