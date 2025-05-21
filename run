#!/bin/bash
# This script is used to run the Streamlit app with the specified configuration.

#If argument is "dev" run the app in development mode
if [ "$1" == "dev" ]; then
    echo "Running in development mode..."
    streamlit run app.py --server.runOnSave true
    exit 0
fi

# If argument is "prod" run the app in production mode
if [ "$1" == "prod" ]; then
    echo "Running in production mode..."
    streamlit run app.py
    exit 0
fi