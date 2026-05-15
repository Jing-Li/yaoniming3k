# caisen-data

数据抓取模块，为 caisen 回测系统提供数据源。

## 安装

```bash
pip install caisen-data
```

## 使用

```bash
# 下载数据
caisen-data fetch --symbol 000001.SZ --start 2020-01-01 --end 2024-12-31

# 列出可用数据源
caisen-data list-sources
```

## 数据源

- **akshare**: 免费数据源，支持 A 股数据