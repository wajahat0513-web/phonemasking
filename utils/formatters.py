
def format_display_name(name: str) -> str:
    """
    Formats a full name into 'First Name' + 'Last Initial.'
    Example: 'John Smith' -> 'John S.'
    Example: 'John' -> 'John'
    """
    if not name or name.strip() == "Unknown":
        return "Unknown"
    
    parts = name.strip().split()
    
    if len(parts) < 2:
        return parts[0]
    
    first_name = parts[0]
    last_initial = parts[-1][0].upper()
    
    return f"{first_name} {last_initial}."
