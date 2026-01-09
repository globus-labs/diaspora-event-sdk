#!/usr/bin/env python3
"""
Reliable client creation examples - Python script version with timing.

For each iteration, this script:
1. Initializes a client
2. Calls reliable_client_creation()
3. Runs 3 cycles of: create topic → produce 3 msgs → consume → delete topic
4. Deletes the user
If any iteration exceeds 1 minute, it's marked as failure.

Usage:
    python reliable_client_creation_examples.py [NUMBER_OF_ITERATIONS]
    
    If no argument is provided, defaults to 20 iterations.
    
Example:
    python reliable_client_creation_examples.py 20
    python reliable_client_creation_examples.py 10
"""

import sys
import time
import uuid
from time import perf_counter

# Import the client and kafka functions
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.kafka_client import (
    reliable_client_creation,
    KafkaProducer,
    KafkaConsumer,
)


def format_time(seconds):
    """Format time in a human-readable way."""
    if seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.2f}s"


def random_topic_produce_consume(client):
    """Create a random topic, produce 3 messages, and consume them."""
    topic_name = f"topic-{str(uuid.uuid4())[:5]}"
    kafka_topic = f"{client.namespace}.{topic_name}"

    if client.create_topic(topic_name).get("status") != "success":
        return False
    time.sleep(3)

    producer = KafkaProducer(kafka_topic)
    for i in range(3):
        producer.send(kafka_topic, {"message_id": i + 1, "content": f"Message {i + 1}"}).get(timeout=30)
    producer.close()
    time.sleep(2)

    consumer = KafkaConsumer(kafka_topic, auto_offset_reset="earliest")
    consumer.poll(timeout_ms=10000)
    consumer.close()

    return client.delete_topic(topic_name).get("status") == "success"


def main():
    """Main execution function - Run reliable_client_creation, then 3 cycles of produce/consume, N times."""
    try:
        num_iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        if num_iterations < 1:
            raise ValueError("Number of iterations must be at least 1")
    except ValueError as e:
        print(f"Error: {e}")
        print("Usage: python reliable_client_creation_examples.py [NUMBER_OF_ITERATIONS]")
        sys.exit(1)
    
    print("=" * 60)
    print(f"Running {num_iterations} iterations: reliable_client_creation() + 3 cycles + delete user")
    print("=" * 60)

    execution_times = []
    successful = failed = 0
    timeout = 60

    for i in range(num_iterations):
        start = perf_counter()
        client = None
        try:
            client = Client()
            reliable_client_creation()
            
            for _ in range(3):
                if not random_topic_produce_consume(client):
                    raise RuntimeError("random_topic_produce_consume failed")
            
            elapsed = perf_counter() - start
            if elapsed > timeout:
                raise RuntimeError(f"Exceeded {timeout}s timeout")
            
            execution_times.append(elapsed)
            successful += 1
            print(f"[{i + 1}/{num_iterations}] ✓ Success - {format_time(elapsed)}")
            client.delete_user()
                
        except Exception as e:
            elapsed = perf_counter() - start
            execution_times.append(elapsed)
            failed += 1
            timeout_msg = " (timeout)" if elapsed > timeout else ""
            print(f"[{i + 1}/{num_iterations}] ✗ Failed - {format_time(elapsed)}{timeout_msg} - {e}")
            if client:
                try:
                    client.delete_user()
                except Exception:
                    pass
        
        if i < num_iterations - 1:
            time.sleep(2)

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    print(f"Total: {num_iterations}, Successful: {successful}, Failed: {failed}")
    
    if execution_times:
        avg = sum(execution_times) / len(execution_times)
        print(f"\nTiming: avg={format_time(avg):>10s}, "
              f"min={format_time(min(execution_times)):>10s}, "
              f"max={format_time(max(execution_times)):>10s}")
        print(f"Total time: {format_time(sum(execution_times))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
