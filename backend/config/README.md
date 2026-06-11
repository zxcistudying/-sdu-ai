# Config 模块使用说明

## 初始化

```python
from config import setup_logging, config

# 初始化日志（在应用启动时调用一次）
setup_logging()

# 验证配置
is_valid, errors = config.validate()
if not is_valid:
    print(f"配置错误: {errors}")