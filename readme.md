后端启动

- 切到项目根目录 cd d:\code\trae_code\jinxiaocun
- 创建并激活虚拟环境（Windows） python -m venv venv
- 安装后端依赖 .\\venv\\Scripts\\pip install -r backend\\requirements.txt
- 启动 FastAPI 服务（在后端目录） cd backend ..\\venv\\Scripts\\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
访问前端

- 打开浏览器访问前端页面 http://127.0.0.1:8000/ui/
- 默认登录账号 admin / admin
接口测试（可选）

- 登录获取令牌（PowerShell） $body = @{ username = 'admin'; password = 'admin' ; grant_type='password' } ; Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8000/auth/login -Body $body -ContentType 'application/x-www-form-urlencoded' | Select-Object -ExpandProperty Content
- 携带令牌请求商品列表（PowerShell） $token = '<上一步返回的access_token>' ; Invoke-WebRequest -Method Get -Uri http://127.0.0.1:8000/products/ -Headers @{ Authorization = "Bearer $token" } | Select-Object -ExpandProperty Content
停止服务

- 在运行服务的终端按 Ctrl + C



1. 运行 uvicorn 模块
- 选择配置类型： Python
- Interpreter：选你常用的虚拟环境（需安装 fastapi 、 uvicorn 、 sqlalchemy 、 pydantic ）
- Run 方式： Module name
- Module： uvicorn
- Parameters： app.main:app --port 8000 --reload
- Working directory： d:\code\trae_code\jinxiaocun\backend
- 勾选： Add content roots to PYTHONPATH 和 Add source roots to PYTHONPATH
- 说明：你截图里把工作目录设成了 backend\app ，这样 app.main 无法被找到；请改成 backend 。