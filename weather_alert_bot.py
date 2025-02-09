import os
import requests
import json
from kafka import KafkaConsumer
import psycopg2
from psycopg2 import pool
from telegram import Bot
from telegram.ext import Application
import time
import asyncio

# Load environment variables
TELEGRAM_BOT_TOKEN = '7560823758:AAF84YiVI0qEdWuI_TBQgRH4XEz2H4mpGwc'
CHAT_ID = '1246065946'

# Initialize Telegram bot using Application class
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Kafka Consumer setup
consumer = KafkaConsumer('weather-data',
                         bootstrap_servers='localhost:9092',
                         auto_offset_reset='earliest',
                         enable_auto_commit=True,
                         group_id='weather-group',
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

# PostgreSQL connection pool setup
db_pool = psycopg2.pool.SimpleConnectionPool(10, 50,
    dbname="weather_data1", user="postgres", password="harsh", host="localhost", port="5432"
)


# Function to handle database inserts and alerts
async def process_weather_data(weather_data):
    try:
        conn = db_pool.getconn()  # Get a connection from the pool
        with conn.cursor() as cursor:  # Use context manager for the cursor
            cursor.execute("INSERT INTO weather_info (city, timestamp, temperature, weather) VALUES (%s, %s, %s, %s)",
                           (weather_data['city'], weather_data['timestamp'], weather_data['temperature'], weather_data['weather']))
            conn.commit()

            # Check for extreme weather conditions
            if weather_data['temperature'] > 35:  # Example threshold for heatwave
                alert_message = f"Alert! Extreme heat detected in {weather_data['city']}: {weather_data['temperature']}°C."
                await application.bot.send_message(chat_id=CHAT_ID, text=alert_message)
            elif weather_data['temperature'] < -10:  # Example threshold for extreme cold
                alert_message = f"Alert! Extreme cold detected in {weather_data['city']}: {weather_data['temperature']}°C."
                await application.bot.send_message(chat_id=CHAT_ID, text=alert_message)

            # Check for clear sky condition
            if weather_data['weather'] == 'clear sky':  # Check if the sky is clear
                alert_message = f"Clear sky detected in {weather_data['city']}. Enjoy the beautiful day!"
                await application.bot.send_message(chat_id=CHAT_ID, text=alert_message)

            # Check for storm condition
            if 'storm' in weather_data['weather'].lower() or 'thunderstorm' in weather_data['weather'].lower():  # Check for stormy weather
                alert_message = f"Storm detected in {weather_data['city']}! Please stay safe."
                await application.bot.send_message(chat_id=CHAT_ID, text=alert_message)

            # Additional conditions can be added here (e.g., heavy rain or other weather conditions)

    except Exception as e:
        print(f"Error processing weather data: {e}")
        time.sleep(5)  # Optionally, wait for some time before retrying
    finally:
        db_pool.putconn(conn)  # Return the connection to the pool

# Main loop to consume messages from Kafka
async def main():
    try:
        for message in consumer:
            weather_data = message.value
            await process_weather_data(weather_data)

    except KeyboardInterrupt:
        print("Consumer interrupted, shutting down...")

    finally:
        consumer.close()
        print("Kafka consumer closed.")

# Run the asyncio loop
if __name__ == "__main__":
    asyncio.run(main())
