#!/bin/bash

# Start both of MedDR's backend and web UI server.
# If the user presses Ctrl+C, kill them both.

if [ "$1" == "dev" ]; then
    echo -e "Starting MedDR in [DEVELOPMENT] mode...\n"
    export MEDDR_DEV_MODE=true
    python server.py --reload & SERVER_PID=$$!
    cd web && pnpm dev & WEB_PID=$$!
    trap "kill $$SERVER_PID $$WEB_PID" SIGINT SIGTERM
    wait
else
    echo -e "Starting MedDR in [PRODUCTION] mode...\n"
    python server.py & SERVER_PID=$$!
    cd web && pnpm start & WEB_PID=$$!
    trap "kill $$SERVER_PID $$WEB_PID" SIGINT SIGTERM
    wait
fi
