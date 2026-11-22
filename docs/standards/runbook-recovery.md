# EPE MVP 故障恢复手册

## 写入冲突

退出码 5 或 `EPE-WRITE-CONFLICT` 表示已有 EPE 写锁或目标文件。先确认没有仍在运行的 EPE 进程，再检查 `.engineering/.write.lock` 的持有者信息；不要在活动进程存在时删除锁。确认失效后删除锁并重试原命令。

## 图快照过期或损坏

运行：

```bash
epe --format json graph build
epe --format json architecture validate
```

构建会生成新的完整 generation 并原子切换 current 指针；旧 generation 保留用于历史影响分析。不要手工修改 `.engineering/` 派生文件。

## Evidence stale、invalid 或 unknown

- `stale`：重新运行 `epe verify TASK-ID`，再运行 `epe check --task TASK-ID`。
- `invalid`：检查 Evidence 引用的产物是否被修改或删除；不要手工改摘要。
- `unknown`：确认环境、审计登记、策略指纹和测试协议完整，再重新验证。
- 运行目录缺失或 Evidence JSON 损坏会产生读取/审计故障，不能回退到较早的通过记录。

## 审计链故障

```bash
epe --format json audit verify
```

审计链无效时，保留原文件用于取证；不要截断或重写历史链。审批和生命周期操作需要完整审计事件，修复可信存储后重新执行相应操作。

## 初始化失败

`epe init` 的文件创建采用写锁和独占创建。中途存储故障会回滚本次创建且未被外部修改的文件；检查已有内容后重新运行即可。符号链接路径会被阻断，需改为仓库内普通目录或文件。

## 宿主不可用

`host capabilities` 返回 `unsupported-unintegrated` 或 `handshake-failed` 时，继续使用本地只读检查。不要把请求中的 `approved`、`role` 或 `identity-source` 参数当作认证，也不要把本地 CLI 的 `accepted` 当作写入授权。
