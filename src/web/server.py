"""Web server entry point."""

import uvicorn

from src.utils.config import config
from src.utils.logger import logger


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the web server.

    Args:
        host: Server host address
        port: Server port
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting web server on http://{host}:{port}")
    uvicorn.run(
        "src.web.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    run_server(reload=True)
