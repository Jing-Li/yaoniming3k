# ADR-0001: 增量数据抓取

## Status
Accepted

## Context

caisen-data 负责从外部 API 获取行情数据，历史行情数据一旦获取且验证正确后，不会再变化。

如果每次抓取都重新下载全部数据：
1. 浪费时间（重复请求 API）
2. 增加 API 限流风险
3. 不必要的网络开销

需要实现增量抓取机制，只下载缺失的数据。

## Decision

### 1. 文件存在性检查

按文件粒度检查：
- 文件路径：`{output_dir}/{symbol}/{freq}/{start}_{end}.parquet`
- 文件存在则跳过整个请求（假设历史数据不变）

### 2. 强制更新选项

提供 `--force` CLI 参数：
- 默认：文件存在则跳过
- `--force`：覆盖现有文件

### 3. 部分范围匹配

当请求范围与已有文件存在重叠时：
1. 识别已有文件覆盖的日期区间
2. 计算缺失的日期区间
3. 只下载缺失部分

### 4. 数据合并策略

多文件合并为单个文件：
- 下载新数据后，与已有文件合并
- 合并结果写入新文件（覆盖原有请求的文件名）
- 删除被合并的旧文件

**示例流程**:
```
已有: 20240101_20240630.parquet
请求: 20240101_20241231

步骤:
1. 发现范围重叠
2. 计算缺失区间: 20240701_20241231
3. 下载缺失数据
4. 合并为: 20240101_20241231.parquet
5. 删除 20240101_20240630.parquet
```

### 5. CLI 参数

```bash
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31 --force  # 强制更新
```

## Implementation Notes

### 文件扫描

扫描 `{output_dir}/{symbol}/{freq}/` 目录，匹配 `*.parquet` 文件，解析文件名中的日期范围。

### 日期范围计算

```python
def parse_date_range(filename: str) -> tuple[date, date]:
    """从文件名解析日期范围，如 20240101_20240630 -> (2024-01-01, 2024-06-30)"""
    parts = filename.stem.split('_')
    start = datetime.strptime(parts[0], '%Y%m%d').date()
    end = datetime.strptime(parts[1], '%Y%m%d').date()
    return start, end

def merge_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """合并重叠的日期范围"""
    # 按起始日期排序
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    merged = [sorted_ranges[0]]

    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:  # 有重叠
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged
```

### 合并逻辑

```python
def merge_parquet_files(files: list[Path], output: Path) -> None:
    """合并多个 Parquet 文件为一个"""
    dfs = [pd.read_parquet(f) for f in files]
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values('timestamp')
    combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
    combined.to_parquet(output, index=False)

    # 删除旧文件
    for f in files:
        f.unlink()
```

## Consequences

### Positive
- 避免重复下载，节省时间和 API 配额
- 用户体验更好（无需手动判断哪些已下载）
- 保持数据目录整洁（只有完整连续的数据文件）

### Negative
- 合并操作可能耗时（但历史数据只合并一次）
- 文件删除不可逆（需要确保合并成功后再删除）

### Limitations
- 不支持跨频率的合并（如 1d 和 1h 分别处理）
- 不处理数据源 API 返回错误的情况（需要上层处理）

## References
- CLI 实现: `src/caisen_data/cli.py`
- 数据源: `src/caisen_data/sources/akshare.py`