from __future__ import annotations

import uvicorn

from zhaocai_gateway.app import create_default_app
from zhaocai_gateway.config import load_server_config


app = create_default_app()


def main() -> None:
    server_config = load_server_config()
    uvicorn.run(
        "zhaocai_gateway.main:app",
        host=server_config.host,
        port=server_config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
