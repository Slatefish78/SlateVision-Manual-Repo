def hex_2_rgb(hex_val):
    """Return 3-tuple of ints converting 7char hex color string (#xxxxxx) to rgb"""
    if len(hex_val) != 7 or not hex_val.startswith('#'):
        raise TypeError("Invalid Hex Color Format")
    
    r = int(hex_val[1:3],16)
    g = int(hex_val[3:5],16)
    b = int(hex_val[5:7],16)

    return (r,g,b)

def rgb_2_hex(r,g,b):
    """Return string converting 3 rgb ints to hex color"""
    return f"#{r:02x}{g:02x}{b:02x}"