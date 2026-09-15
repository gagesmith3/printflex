"""Start PrintFlex.  Windows: .venv\\Scripts\\python.exe run.py   Linux: .venv/bin/python run.py"""

import logging

from printflex import create_app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    port = app.config["PORT"]
    base = app.extensions["printflex"].base_url
    local = "http://localhost" if port == 80 else f"http://localhost:{port}"
    print(
        f"\n  {app.config['SOFTWARE_NAME']} is running\n"
        f"  Display : {local}/server/display\n"
        f"  Phone   : {base}/user\n"
        f"  Crew    : {base}/server/operator\n"
    )
    app.run(host=app.config["HOST"], port=port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
