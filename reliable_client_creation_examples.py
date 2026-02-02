"""
Reliable Client Creation Examples

This script demonstrates reliable client creation and basic Kafka operations
including topic creation, message production, and consumption.
"""

# Install dependencies
# Run: pip install -e '.[kafka-python]'

# Import the reliable topic creation functions
from diaspora_event_sdk.sdk.kafka_client import (
    reliable_client_creation,
    KafkaProducer,
    KafkaConsumer,
)
from diaspora_event_sdk import Client as GlobusClient
from kafka.errors import KafkaTimeoutError
import uuid
import time
import argparse
import traceback
import os
from datetime import datetime

# Configure logging to show INFO level messages from kafka_client
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )


def reliable_produce(namespace, topic, num_messages=3, max_retries=3):
    """Produce messages to a topic with retry logic for timeout errors.

    Args:
        namespace: The namespace for the topic
        topic: The topic name (without namespace prefix)
        num_messages: Number of messages to produce (default: 3)
        max_retries: Maximum number of retries on timeout (default: 3)

    Returns:
        bool: True if successful, False otherwise
    """
    kafka_topic = f"{namespace}.{topic}"

    for attempt in range(max_retries):
        producer = None
        try:
            if attempt > 0:
                print(f"    Retry {attempt + 1}/{max_retries}")
            producer = KafkaProducer(kafka_topic)
            for i in range(num_messages):
                message = {
                    "message_id": i + 1,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "content": f"Message {i + 1} from reliable_produce",
                }
                future = producer.send(kafka_topic, message)
                print(f"    Sending message {i + 1}/{num_messages}...")
                future.get(timeout=30)
            return True
        except KafkaTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                print(f"✗ Produce failed after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"✗ Produce error: {e}")
            return False
        finally:
            if producer is not None:
                try:
                    producer.close(timeout=1)
                except Exception:
                    # Ignore errors during cleanup to avoid "Exception ignored" warnings
                    pass

    return False


def reliable_consume(namespace, topic, max_retries=3):
    """Consume messages from a topic with retry logic for timeout errors.

    Args:
        namespace: The namespace for the topic
        topic: The topic name (without namespace prefix)
        max_retries: Maximum number of retries on timeout (default: 3)

    Returns:
        tuple: (success: bool, consumed_count: int)
    """
    kafka_topic = f"{namespace}.{topic}"

    for attempt in range(max_retries):
        consumer = None
        try:
            if attempt > 0:
                print(f"    Retry {attempt + 1}/{max_retries}")
            print("    Polling for messages...")
            consumer = KafkaConsumer(kafka_topic, auto_offset_reset="earliest")
            messages = consumer.poll(timeout_ms=10000)
            consumed_count = 0
            for tp, msgs in messages.items():
                for message in msgs:
                    consumed_count += 1
            return True, consumed_count
        except KafkaTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                print(f"✗ Consume failed after {max_retries} attempts")
                return False, 0
        except Exception as e:
            print(f"✗ Consume error: {e}")
            return False, 0
        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    # Ignore errors during cleanup to avoid "Exception ignored" warnings
                    pass

    return False, 0


def run_produce_consume_cycle(produce_consumer_per_iteration=1):
    """Run the reliable client creation examples with produce/consume cycles.

    Args:
        produce_consumer_per_iteration: Number of times to run the topic produce/consume cycle

    Returns:
        tuple: (success: bool, log_file: str or None)
    """
    try:
        # Initialize client
        # os.environ["DIASPORA_SDK_ENVIRONMENT"] = "local"
        c = GlobusClient()

        # Run reliable_client_creation to set up client and test basic flow
        print("  → reliable_client_creation()")
        reliable_client_creation()

        # Run produce/consume cycles
        for i in range(produce_consumer_per_iteration):
            print(f"Iteration {i + 1}/{produce_consumer_per_iteration}")

            # Create topic
            topic_name = f"topic-{str(uuid.uuid4())[:5]}"
            print("  → create_topic()")
            topic_result = c.create_topic(topic_name)

            if topic_result.get("status") != "success":
                print("✗ Failed to create topic")
                continue

            time.sleep(3)  # Wait for topic to be ready

            # Produce messages with retry logic
            print("  → reliable_produce()")
            produce_success = reliable_produce(c.namespace, topic_name)

            time.sleep(2)  # Wait before consuming

            # Consume messages with retry logic
            print("  → reliable_consume()")
            consume_success, consumed_count = reliable_consume(c.namespace, topic_name)

            # Delete topic
            print("  → delete_topic()")
            c.delete_topic(topic_name)

            if produce_success and consume_success:
                print(f"✓ Iteration {i + 1} completed")
            else:
                print(f"✗ Iteration {i + 1} failed")

            if (
                i < produce_consumer_per_iteration - 1
            ):  # Don't sleep after last iteration
                time.sleep(2)

        # Cleanup: Delete user at the end
        print("  → delete_user()")
        delete_user_result = c.delete_user()
        if delete_user_result.get("status") != "success":
            print("✗ Failed to delete user")

        return True, None
    except Exception as e:
        # Get the script directory for log file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_filename = os.path.join(
            script_dir, f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Get full traceback
        full_traceback = traceback.format_exc()

        # Write to log file
        with open(log_filename, "w") as log_file:
            log_file.write(
                f"Exception occurred at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            log_file.write(f"{'=' * 80}\n")
            log_file.write(f"Exception type: {type(e).__name__}\n")
            log_file.write(f"Exception message: {str(e)}\n")
            log_file.write(f"{'=' * 80}\n")
            log_file.write("Full traceback:\n")
            log_file.write(full_traceback)

        print(f"✗ Exception: {type(e).__name__}: {str(e)}")
        print(f"Log: {log_filename}")

        return False, log_filename


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Reliable client creation examples with configurable iterations"
    )
    parser.add_argument(
        "--produce-consumer-per-iteration",
        type=int,
        default=1,
        help="Number of topic produce/consume cycles to run per main() call (default: 1)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of times to call main() (default: 3)",
    )
    args = parser.parse_args()

    # Track statistics
    successful_runs = 0
    failed_runs = 0
    log_files = []

    try:
        for i in range(args.iterations):
            print(f"\nRun {i + 1}/{args.iterations}")
            success, log_file = run_produce_consume_cycle(
                produce_consumer_per_iteration=args.produce_consumer_per_iteration
            )
            if success:
                successful_runs += 1
            else:
                failed_runs += 1
                if log_file:
                    log_files.append(log_file)
            if i < args.iterations - 1:  # Don't sleep after last iteration
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\nInterrupted by user after {successful_runs + failed_runs} runs")

    # Print final statistics
    print("\nFINAL STATISTICS")
    print(f"Successfully completed runs: {successful_runs}")
    print(f"Failed runs: {failed_runs}")
    print(f"Total runs: {successful_runs + failed_runs}")

    if log_files:
        print(f"\nError log files ({len(log_files)}):")
        for log_file in log_files:
            print(f"  {log_file}")


if __name__ == "__main__":
    main()
