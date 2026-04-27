#!/bin/bash
cd data
streamlit run app_main.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
