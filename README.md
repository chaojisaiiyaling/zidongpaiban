# 科室自动排班网页工具 MVP

这是一个基于 Python + Streamlit 的本地网页排班工具。第一版不使用数据库，所有请假和排班数据保存在 JSON 文件中。

## 功能

- 固定 5 名排班人员
- 选择年份和月份
- 添加、查看、删除请假记录
- 一键生成当月排班
- 周一到周四使用固定模板
- 周五自动轮换中班和晚班
- 周六、周日各安排 1 人半天班，显示为“班/休”
- 请假当天自动显示“休息”，且不会被安排中班、晚班或周末班
- 固定模板人员请假时，自动找同类班次次数较少的人替班
- 网页表格手动修改排班
- 保存后再次打开还能看到上次排班
- 统计每个人中班、晚班、周末班、休息次数
- 导出 Excel 排班表

## 目录结构

```text
schedule_app/
  app.py
  scheduler.py
  excel_exporter.py
  data/
    leaves.json
    schedules.json
  README.md
  requirements.txt
```

## 安装依赖

进入项目目录：

```bash
cd schedule_app
pip install -r requirements.txt
```

## 启动

```bash
streamlit run app.py
```

启动后浏览器会打开本地网页。如果没有自动打开，可以访问终端里显示的本地地址，通常是：

```text
http://localhost:8501
```

## 让科室同事也能打开

项目已经带了 Streamlit 共享配置：

```text
.streamlit/config.toml
```

启动后，同一个局域网里的同事可以用浏览器访问：

```text
http://你的电脑IP:8501
```

查看你电脑 IP 的方式：

```bash
ipconfig getifaddr en0
```

如果你连接的是有线网络，可以试：

```bash
ipconfig getifaddr en1
```

例如查到 IP 是 `192.168.1.23`，同事访问：

```text
http://192.168.1.23:8501
```

注意：

- 你的电脑需要保持开机，Streamlit 命令窗口不能关闭。
- 同事需要和你在同一个 Wi-Fi 或医院内网。
- 如果浏览器打不开，通常是 macOS 防火墙或医院网络策略拦截了 8501 端口。
- 当前 MVP 用 JSON 文件保存数据，多人同时编辑时最后保存的人会覆盖前一次保存；第一版建议由一个人负责编辑，其他人主要查看。

## 如果要发到微信

如果希望把链接发到微信群里，让大家不在同一个 Wi-Fi 也能打开，需要部署成公网网页。

最简单的第一版方式是部署到 Streamlit Community Cloud，部署后会得到一个类似下面的链接：

```text
https://你的应用名.streamlit.app
```

然后把这个链接直接发到微信即可。

详细步骤见：

```text
DEPLOY_WECHAT.md
```

注意：当前 MVP 用 JSON 文件保存数据，适合演示和轻量使用；如果多人长期同时编辑，建议下一版加数据库和登录权限。

## 数据保存位置

- 请假记录：`data/leaves.json`
- 已保存排班：`data/schedules.json`

删除这两个文件后重新启动，系统会自动创建空数据文件。
