import random
from fastmcp import FastMCP

mcp = FastMCP(name='demo_server')

@mcp.tool
def roll_dice(n: int) -> list[int]:
    """Roll n dice and return the results."""
    return [random.randint(1, 6) for _ in range(n)]

@mcp.tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)