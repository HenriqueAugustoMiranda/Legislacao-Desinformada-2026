#!/bin/bash

echo "Starting post collection..."
python 01_collect_posts.py

echo "Waiting 120 seconds..."
sleep 120

echo "Starting comments collection..."
python 02_collect_comments.py

echo "Finished!"