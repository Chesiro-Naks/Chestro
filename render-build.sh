#!/usr/bin/env bash
# Exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

# Download and set up Chrome if it's not already cached
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  cd $HOME/project/src # Return to the original directory
else
  echo "...Using Chrome from cache"
fi

# Add Chrome to the PATH
export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome"

# Install Python dependencies from requirements.txt
pip install -r requirements.txt

# Run Streamlit app on the correct port
# Render automatically assigns the $PORT environment variable
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
