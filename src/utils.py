import os
import logging
import textwrap

print_width = 70
logger = logging.getLogger(__name__)

def configure_logger(log_path: str, level: int = logging.INFO):
    """
    Configures the logger to write to a specified file.
    Args:
        log_path (str): The path to the log file.
        level (int): The logging level (default: logging.INFO).
    """
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    open(log_path, "a").close()

    logging.basicConfig(
        filename=log_path,
        filemode='w',
        level=level,
        format="%(asctime)s | %(levelname)8s | %(filename)16s:%(lineno)4d | %(message)s"
    )

def validate_inputs(user_input: str, order_info: dict) -> bool:
    """
    Validates the user input and order information.
    Args:
        user_input (str): The user's input message.
        order_info (dict): Information about the order, including order_id, order_date, and user_id.
    Returns:
        bool: True if inputs are valid, False otherwise.
    """
    if not user_input or not isinstance(user_input, str):
        logger.error("Invalid user input. Must be a non-empty string.")
        return False
    if not order_info or not isinstance(order_info, dict):
        logger.error("Invalid order info. Must be a non-empty JSON object.")
        return False
    else:
        required_keys = ["order_id", "order_date", "user_id"]
        for key in required_keys:
            if key not in order_info:
                logger.error(f"Missing required key in order info: {key}")
                return False
    return True

def pretty_section(title: str, body: str, wrap: bool = False):
    """
    Pretty prints a section with a title and body.
    Args:
        title (str): The title of the section.
        body (str): The body content of the section.
        wrap (bool): Whether to wrap the text to fit within the print width.
    """
    sep = "=" * print_width
    if wrap:
        body = textwrap.fill(body, width=print_width)
    print(f"\n{sep}\n{title}\n{sep}\n{body}")