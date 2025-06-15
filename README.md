# RealMaster Property Scraper

这是一个用于抓取 RealMaster 网站房源数据的 Python 爬虫程序。

## 功能特点

- 支持按省份和城市抓取房源数据
- 自动处理分页
- 提取详细的房源信息
- 将数据保存为 CSV 格式
- 支持自定义抓取区域
- 支持 Docker 部署

## 系统要求

### 方式一：直接运行
- Python 3.6+
- Microsoft Edge 浏览器
- Windows 操作系统

### 方式二：Docker 运行
- Docker
- Docker Compose

## 安装步骤

### 方式一：直接运行

1. **克隆仓库**
   ```bash
   git clone [你的仓库URL]
   cd [仓库目录]
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置 EdgeDriver**
   - 访问 [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
   - 下载与你的 Edge 浏览器版本匹配的 WebDriver
   - 将下载的 `msedgedriver.exe` 放在项目根目录下

4. **配置 Cookies**
   - 使用 Microsoft Edge 浏览器登录 [RealMaster](https://www.realmaster.com)
   - 按 F12 打开开发者工具
   - 切换到 "Application" 或 "应用程序" 标签
   - 在左侧找到 "Cookies" 并选择网站域名
   - 右键点击 cookies，选择 "Copy all as JSON"
   - 创建 `browser_cookies.json` 文件并粘贴内容

### 方式二：Docker 运行

1. **克隆仓库**
   ```bash
   git clone [你的仓库URL]
   cd [仓库目录]
   ```

2. **配置 Cookies**
   - 按照上述方式一中的步骤 4 配置 cookies
   - 确保 `browser_cookies.json` 文件在项目根目录下

3. **构建并运行 Docker 容器**
   ```bash
   docker-compose up --build
   ```

## 使用方法

### 方式一：直接运行

1. 运行程序：
   ```bash
   python scraper.py
   ```

2. 按提示输入：
   - 省份名称（例如：Ontario）
   - 城市名称（例如：Toronto）

### 方式二：Docker 运行

1. 运行容器：
   ```bash
   docker-compose up
   ```

2. 在容器中按提示输入：
   - 省份名称（例如：Ontario）
   - 城市名称（例如：Toronto）

3. 数据文件将保存在 `./data` 目录下

## 输出文件

程序会生成一个 CSV 文件，文件名格式为：`[城市名]_[省份名]_listings.csv`

CSV 文件包含以下字段：
- URL
- ID
- 价格
- 地址
- 卧室数量
- 浴室数量
- 车库数量
- 房屋面积
- 地块大小
- 土地面积
- 土地面积（英亩）
- 城市
- 省份

## 注意事项

- 确保你的网络连接稳定
- 程序运行过程中请勿关闭浏览器
- 如果遇到验证码，可能需要更新 cookies
- 建议不要过于频繁地运行程序，以免被网站限制
- 使用 Docker 运行时，确保 Docker 服务已启动
- Docker 容器中的数据会保存在宿主机的 `./data` 目录下

## 常见问题

1. **EdgeDriver 版本不匹配**
   - 直接运行时：确保下载的 EdgeDriver 版本与你的 Edge 浏览器版本一致
   - Docker 运行时：容器会自动安装匹配的 EdgeDriver 版本

2. **Cookies 失效**
   - 如果程序无法访问网站，可能需要重新导出 cookies
   - 确保 cookies 文件格式正确（JSON 格式）

3. **程序运行缓慢**
   - 这是正常的，程序包含延时以避免请求过快
   - 可以根据需要调整代码中的延时参数

4. **Docker 相关问题**
   - 如果遇到权限问题，可能需要使用 `sudo` 运行 Docker 命令
   - 确保 Docker 和 Docker Compose 已正确安装
   - 如果容器无法启动，检查 Docker 日志：`docker-compose logs`

## 许可证

[添加你的许可证信息]

## 贡献

欢迎提交 Issue 和 Pull Request！ 