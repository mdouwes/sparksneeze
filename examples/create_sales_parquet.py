#!/usr/bin/env python3
"""
Script to create sales.parquet file with Trailer Park Boys themed data using PySpark.

Generates 500 realistic sales transactions over the past year with TPB characters,
products, and business scenarios. Run from repo root with:
uv run python examples/create_sales_parquet.py
"""

from sparksneeze.spark_utils import create_spark_session_with_delta
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, BooleanType, DateType
from datetime import datetime, timedelta
import random

spark = create_spark_session_with_delta(app_name="CreateTPBSalesData")

schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("transaction_date", DateType(), True),
    StructField("product_id", StringType(), True),
    StructField("product_name", StringType(), True),
    StructField("customer_name", StringType(), True),
    StructField("salesperson", StringType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("unit_price", DoubleType(), True),
    StructField("total_amount", DoubleType(), True),
    StructField("payment_method", StringType(), True),
    StructField("is_successful", BooleanType(), True),
    StructField("location", StringType(), True),
    StructField("notes", StringType(), True)
])

products = [
    ("TPB001", "Hash", 40.0),
    ("TPB002", "Pepperoni Sticks", 8.99),
    ("TPB003", "Shopping Cart", 25.0),
    ("TPB004", "Liquor", 25.99),
    ("TPB005", "Kitty Food", 12.50),
    ("TPB006", "Stolen Barbecue", 150.0)
]

customers = [
    "Jacob Collins", "Trinity", "Donny", "Private Dancer", "Philadelphia Collins",
    "Sam Losco", "Barb Lahey", "Candy", "Detroit Velvet Smooth", "Sebastian Bach"
]

salespeople = ["Ricky", "Julian", "Bubbles", "Corey", "Trevor"]

notes_options = [
    "Decent transaction boys",
    "Customer paid in pepperoni sticks", 
    "Had to negotiate with shopping cart",
    "Lahey tried to interfere",
    "Smooth as a baby's bottom",
    "Customer was drunk as fuck",
    "Bubbles supervised the deal",
    "Corey and Trevor fucked it up",
    "Julian had everything under control",
    "Ricky forgot to count the money"
]

sales_data = []
start_date = datetime.now() - timedelta(days=365)

for i in range(500):
    transaction_date = start_date + timedelta(days=random.randint(0, 365))
    product_id, product_name, base_price = random.choice(products)
    customer = random.choice(customers)
    salesperson = random.choice(salespeople)
    
    price_multiplier = random.uniform(0.8, 1.5)
    unit_price = round(base_price * price_multiplier, 2)
    
    quantity = random.randint(10, 50) if random.random() < 0.1 else random.randint(1, 5)
    total_amount = round(unit_price * quantity, 2)
    
    payment_method = random.choices(
        ["Cash", "Credit Card", "Barter", "IOU"], 
        weights=[70, 15, 10, 5]
    )[0]
    
    success_rates = {"Ricky": 0.6, "Julian": 0.9, "Bubbles": 0.8, "Corey": 0.4, "Trevor": 0.3}
    is_successful = random.random() < success_rates[salesperson]
    
    sales_data.append((
        f"TXN{i+1:04d}",
        transaction_date.date(),
        product_id,
        product_name,
        customer,
        salesperson,
        quantity,
        unit_price,
        total_amount,
        payment_method,
        is_successful,
        "Sunnyvale Trailer Park",
        random.choice(notes_options)
    ))

df = spark.createDataFrame(sales_data, schema)
df.coalesce(1).write.mode("overwrite").parquet("examples/data/sales.parquet")

print(f"✅ Created sales.parquet with {df.count()} transactions")
print(f"💰 Total sales amount: ${df.agg({'total_amount': 'sum'}).collect()[0][0]:,.2f}")
successful_rate = df.filter(df.is_successful).count() / df.count()
print(f"📈 Success rate: {successful_rate:.1%}")

spark.stop()