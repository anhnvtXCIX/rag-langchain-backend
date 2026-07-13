import logging

logger = logging.getLogger(__name__)


def sum_2_numbers(a: int, b: int) -> int:
    """
    Returns the sum of two numbers.

    Args:
        a (int): The first number.
        b (int): The second number.

    Returns:
        int: The sum of the two numbers.
    """
    logger.info("Calculating the sum of %d and %d", a, b)
    return a + b
