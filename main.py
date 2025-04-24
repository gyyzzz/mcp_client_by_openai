import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self, config_path: str = "config.json"):
        """初始化 MCP 客户端"""
        self.exit_stack = AsyncExitStack()
        self.config_path = config_path
        self.config = self.load_config()
        # 从环境变量读取配置
        self.openai_api_key = os.getenv("OPENAI_API_KEY")  # 读取 OpenAI API Key
        self.base_url = os.getenv("BASE_URL")  # 读取 BASE URL
        self.model = os.getenv("MODEL")  # 读取模型名称

        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置 OPENAI_API_KEY")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        self.session: Optional[ClientSession] = None
    def load_config(self):
        """加载 JSON 配置文件"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ 配置文件 {self.config_path} 未找到")
        except json.JSONDecodeError:
            raise ValueError(f"❌ 配置文件 {self.config_path} 格式错误")
        
    def get_server_name_and_config(self):
        """自动获取服务器名称和配置"""
        try:
            mcp_servers = self.config.get("mcpServers", {})
            if not mcp_servers:
                raise ValueError("❌ 配置文件中未找到 MCP 服务器配置")
            server_name, server_config = next(iter(self.config["mcpServers"].items()))
            return server_name, server_config
        except Exception as e:
            raise ValueError(f"❌ 获取服务器名称和配置失败: {str(e)}")

    async def connect_to_server(self, server_name: str = "mcp-clickhouse"):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (ignored in this case)
        """

        server_name, server_config = self.get_server_name_and_config()
        print(f"Connecting to server: {server_name}")

        
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", {})
        print("Server Command:", command)
        print("Server Args:", args)
        print("Server Env:", env)
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])


    async def process_query(self, query: str) -> str:
        """
        使用大模型处理查询并调用可用的 MCP 工具 (Function Calling)
        """
        messages = [{"role": "user", "content": query}]
        
        # 获取可用工具列表
        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
        } for tool in response.tools]

        # 调用 OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools
        )

        # 处理返回的内容
        content = response.choices[0]
        if content.finish_reason == "tool_calls":
            # 如果需要使用工具，解析工具调用
            tool_call = content.message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # 执行工具
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")

            # 将结果存入消息历史
            messages.append(content.message.model_dump())
            messages.append({
                "role": "tool",
                "content": result.content[0].text,
                "tool_call_id": tool_call.id,
            })

            # 将结果返回给大模型生成最终响应
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content

        return content.message.content
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
