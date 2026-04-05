# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

FROM python:3.10-slim

# Update and install dependencies
RUN apt update && apt upgrade -y && \
    apt install git -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U -r requirements.txt

# Create working directory
RUN mkdir /VJ-File-Store
WORKDIR /VJ-File-Store

# Copy application code
COPY . /VJ-File-Store

# Run the bot
CMD ["python", "bot.py"]
