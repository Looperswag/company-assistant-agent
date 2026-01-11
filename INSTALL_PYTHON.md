# Python安装指南

## 问题诊断

如果遇到 `pip : 无法将"pip"项识别为 cmdlet` 错误，通常是因为：

1. **Python未安装**
2. **Python已安装但未添加到PATH环境变量**

## 解决方案

### 方案1: 安装Python（如果未安装）

1. **下载Python**
   - 访问 [Python官网](https://www.python.org/downloads/)
   - 下载Python 3.10或更高版本（推荐3.11或3.12）

2. **安装Python**
   - 运行安装程序
   - **重要**: 勾选 "Add Python to PATH" 选项
   - 选择 "Install Now" 或自定义安装路径

3. **验证安装**
   ```powershell
   python --version
   pip --version
   ```

### 方案2: 将Python添加到PATH（如果已安装但未在PATH中）

1. **查找Python安装路径**
   - 常见位置：
     - `C:\Python3x\`
     - `C:\Users\<用户名>\AppData\Local\Programs\Python\`
     - `C:\Program Files\Python3x\`

2. **添加到PATH环境变量**
   - 按 `Win + R`，输入 `sysdm.cpl`，回车
   - 点击"高级"选项卡
   - 点击"环境变量"
   - 在"系统变量"中找到 `Path`，点击"编辑"
   - 点击"新建"，添加Python安装目录和 `Scripts` 目录：
     ```
     C:\Python3x\
     C:\Python3x\Scripts\
     ```
   - 点击"确定"保存

3. **重启PowerShell或命令提示符**

4. **验证**
   ```powershell
   python --version
   pip --version
   ```

### 方案3: 使用完整路径（临时解决方案）

如果Python已安装但未在PATH中，可以使用完整路径：

```powershell
# 替换为您的Python实际路径
C:\Python3x\python.exe -m pip install -r requirements.txt
```

## 安装项目依赖

Python安装完成后，在项目目录中运行：

```powershell
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略错误，运行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 安装依赖
pip install -r requirements.txt
```

## 验证安装

安装完成后，验证关键包：

```powershell
python -c "import fastapi; print('FastAPI OK')"
python -c "import zhipuai; print('ZhipuAI OK')"
python -c "import chromadb; print('ChromaDB OK')"
```

## 常见问题

### Q: PowerShell执行策略错误

**错误**: `无法加载文件，因为在此系统上禁止运行脚本`

**解决**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: pip安装速度慢

**解决**: 使用国内镜像源

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 某些包安装失败

**解决**: 
1. 确保使用最新版本的pip: `python -m pip install --upgrade pip`
2. 检查Python版本是否符合要求（3.10+）
3. 查看具体错误信息，可能需要安装Visual C++ Build Tools（某些包需要编译）

## 下一步

Python和依赖安装完成后，继续：

1. **初始化知识库**
   ```powershell
   python -m src.main init
   ```

2. **启动Web界面**
   ```powershell
   python -m src.main web
   ```

3. **或使用CLI界面**
   ```powershell
   python -m src.main chat
   ```
