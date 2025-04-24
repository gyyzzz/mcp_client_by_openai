# MCP_client_by_openai

此项目用于个人学习实践MCP(Modle Context Protocol)，本项目实现了一个使用openai api的mcp-client

## 快速开始

首先安装uv，官方文档：https://docs.astral.sh/uv/，

执行以下内容：

```
uv init MCP_client_by_openai
cd MCP_client_by_openai
uv venv
source .venv/bin/activate

uv add mcp openai
```

复制main.py到项目文件夹

### 模型配置

创建.env文件加载OPENAI_API_KEY、BASE_URL、MODEL等环境变量，例如：

```
❯ cat .env
OPENAI_API_KEY=<your_openai_api_key>
BASE_URL="https://api.deepseek.com"
MODEL="deepseek-chat"
```

**注意：**请将.evn加入.gitignore

### mcp_server运行配置

通过config.json执行运行的mcp服务端启动命令参数及环境变量

```
❯ cat config.json.example
{
  "mcpServers": {
    "mcp-clickhouse": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp-clickhouse",
        "--python",
        "3.13",
        "mcp-clickhouse"
      ],
      "env": {
        "CLICKHOUSE_HOST": "<clickhouse-host>",
        "CLICKHOUSE_PORT": "<clickhouse-port>",
        "CLICKHOUSE_USER": "<clickhouse-user>",
        "CLICKHOUSE_PASSWORD": "<clickhouse-password>",
        "CLICKHOUSE_SECURE": "true",
        "CLICKHOUSE_VERIFY": "true",
        "CLICKHOUSE_CONNECT_TIMEOUT": "30",
        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "30"
      }
    }
  }
}
```

**注意**：请将config.json加入.gitignore

配置好以上信息后执行

```
uv run main.py
```

