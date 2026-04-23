from fastmcp import FastMCP

mcp = FastMCP("test-tools")


# Math tools
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the result."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b and return the result."""
    if b == 0:
        return float("inf")
    return a / b


# Text tools
@mcp.tool()
def reverse_string(text: str) -> str:
    """Reverse a string and return the result."""
    return text[::-1]


@mcp.tool()
def uppercase(text: str) -> str:
    """Convert text to uppercase and return the result."""
    return text.upper()


@mcp.tool()
def lowercase(text: str) -> str:
    """Convert text to lowercase and return the result."""
    return text.lower()


@mcp.tool()
def int_to_string(number: float) -> str:
    """Convert a number to its string representation."""
    if number == int(number):
        return str(int(number))
    return str(number)


def run():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3000)


if __name__ == "__main__":
    run()
