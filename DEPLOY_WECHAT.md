# 分享到微信的部署方式

如果要把排班工具发到微信群里，让大家直接点链接打开，需要部署成公网网页。

本地运行得到的 `http://localhost:8501` 只能你自己的电脑打开；局域网地址也只能同一 Wi-Fi 或同一内网打开。微信分享需要类似下面这样的公网地址：

```text
https://你的应用名.streamlit.app
```

## 推荐方式：Streamlit Community Cloud

适合第一版 MVP 演示、查看和少量编辑。

### 1. 准备 GitHub 仓库

把 `schedule_app` 目录上传到 GitHub 仓库。

仓库里至少需要有：

```text
app.py
scheduler.py
excel_exporter.py
requirements.txt
data/leaves.json
data/schedules.json
.streamlit/config.toml
```

### 2. 创建 Streamlit Cloud 应用

打开 Streamlit Community Cloud，选择从 GitHub 部署应用。

配置：

```text
Repository: 你的 GitHub 仓库
Branch: main
Main file path: app.py
```

如果你的仓库根目录不是 `schedule_app`，而是上一级目录，则 Main file path 填：

```text
schedule_app/app.py
```

部署完成后，会得到一个公网地址，例如：

```text
https://your-schedule-app.streamlit.app
```

把这个链接发到微信群即可。

## 重要提醒

当前 MVP 使用 JSON 文件保存数据，适合第一版快速使用，但不适合多人同时编辑：

- 多人同时保存时，后保存的人可能覆盖前一个人的修改。
- 免费云平台重启或重新部署后，JSON 文件可能回到仓库里的初始状态。
- 第一版建议：一个人负责编辑排班，其他人主要查看。

如果后面要正式给科室长期使用，建议第二版升级为：

- 云服务器部署
- SQLite / PostgreSQL 数据库
- 登录权限
- 编辑记录
- 数据自动备份

## 备选方式：云服务器

如果医院网络环境严格，或者希望数据更稳定，可以把项目部署到云服务器。

大致流程：

```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

然后用域名和 HTTPS 反向代理把它变成公网链接。

这种方式更稳定，但需要服务器和一些运维配置。
