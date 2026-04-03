# Apify's official Playwright + Chromium image (Node 20)
# Includes Playwright, Chromium, and all system dependencies pre-installed.
FROM apify/actor-node-playwright-chrome:20

# Copy package files and install dependencies
COPY package*.json ./
RUN npm --quiet set progress=false \
    && npm install --only=prod --no-optional \
    && echo "Dependencies installed"

# Copy actor source
COPY . ./

CMD npm start --silent
