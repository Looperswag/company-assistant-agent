"""CLI interface for the assistant."""

import logging
import sys
import warnings
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from src.core.assistant import Assistant
from src.utils.config import config
from src.utils.logger import logger

# Suppress INFO logs and warnings in CLI output
logging.getLogger("assistant").setLevel(logging.WARNING)
logging.getLogger("jieba").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)

app = typer.Typer(help="小美 - ZURU Melon 智能客服助手")
console = Console()


@app.command()
def chat() -> None:
    """Start interactive chat session."""
    try:
        assistant = Assistant()
        console.print(
            Panel.fit(
                "[bold green]小美 - ZURU Melon 智能客服[/bold green]\n"
                "输入您的问题，输入 'exit' 或 'quit' 退出，输入 'clear' 清空历史",
                title="欢迎",
            )
        )

        while True:
            try:
                query = Prompt.ask("\n[bold cyan]您[/bold cyan]")
                query = query.strip()

                if not query:
                    continue

                if query.lower() in ["exit", "quit", "退出"]:
                    console.print("\n[bold yellow]再见！[/bold yellow]")
                    break

                if query.lower() in ["clear", "清空"]:
                    assistant.clear_history()
                    console.print("[dim]对话历史已清空[/dim]")
                    continue

                # Process query silently (no spinner, logs hidden)
                response = assistant.process_query(query)

                # Display response
                console.print("\n[bold cyan]助手[/bold cyan]")
                console.print(Markdown(response))
                console.print()  # Empty line

            except KeyboardInterrupt:
                console.print("\n\n[bold yellow]再见！[/bold yellow]")
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {e}")
                console.print(f"[bold red]错误:[/bold red] {e}")

    except Exception as e:
        logger.error(f"Error starting assistant: {e}")
        console.print(f"[bold red]启动失败:[/bold red] {e}")
        sys.exit(1)


@app.command()
def init() -> None:
    """Initialize the knowledge base vector store."""
    from src.knowledge.parser import MarkdownParser
    from src.knowledge.vector_store import VectorStore

    console.print("[bold green]正在初始化知识库...[/bold green]")

    try:
        # Parse knowledge base files
        parser = MarkdownParser(
            chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
        )
        chunks = parser.parse_directory(config.knowledge_base_path)

        if not chunks:
            console.print("[bold red]错误:[/bold red] 未找到知识库文件")
            sys.exit(1)

        # Create vector store and add documents
        vector_store = VectorStore()
        vector_store.clear()  # Clear existing data
        vector_store.add_documents(chunks)

        console.print(f"[bold green]✓[/bold green] 成功初始化知识库，共 {len(chunks)} 个文档块")
        console.print(f"[bold green]✓[/bold green] 向量数据库位置: {config.vector_db_path}")

    except Exception as e:
        logger.error(f"Error initializing knowledge base: {e}")
        console.print(f"[bold red]错误:[/bold red] {e}")
        sys.exit(1)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask"),
    no_history: bool = typer.Option(False, "--no-history", help="Don't use conversation history"),
) -> None:
    """Ask a single question."""
    try:
        assistant = Assistant()
        response = assistant.process_query(question, use_history=not no_history)
        console.print(Markdown(response))
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        console.print(f"[bold red]错误:[/bold red] {e}")
        sys.exit(1)


@app.command()
def status() -> None:
    """Show system status and configuration."""
    from src.knowledge.vector_store import VectorStore

    console.print(Panel.fit("[bold]系统状态[/bold]", title="Company Assistant Agent"))

    # Configuration
    console.print("\n[bold]配置信息:[/bold]")
    console.print(f"  模型: {config.zhipuai_model}")
    console.print(f"  知识库路径: {config.knowledge_base_path}")
    console.print(f"  向量数据库路径: {config.vector_db_path}")
    console.print(f"  搜索功能: {'启用' if config.search_enabled else '禁用'}")
    console.print(f"  安全过滤: {'启用' if config.safety_filter_enabled else '禁用'}")

    # Vector store status
    try:
        vector_store = VectorStore()
        count = vector_store.get_collection_size()
        console.print(f"\n[bold]知识库状态:[/bold]")
        console.print(f"  文档块数量: {count}")
        if count == 0:
            console.print("  [yellow]提示: 运行 'python -m src.main init' 初始化知识库[/yellow]")
    except Exception as e:
        console.print(f"  [red]错误: 无法读取向量数据库: {e}[/red]")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the web server."""
    from src.web.server import run_server

    console.print(f"[bold green]启动Web服务器...[/bold green]")
    console.print(f"访问地址: [bold cyan]http://{host}:{port}[/bold cyan]")
    run_server(host=host, port=port, reload=reload)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
